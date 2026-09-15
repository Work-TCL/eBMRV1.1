"""Edge Gateway CLI -- Document 43 section 2's "Installer / Site Admin" actor drives `enroll`
interactively (it is a human-signed action, see EnrollGatewayCommand's `challenge_id`/`reauth_password`
server-side requirement); `run` and `status` are the unattended/support-facing operations.
"""

from __future__ import annotations

import argparse
import asyncio
import getpass
import json
import logging
import socket
import sys
from pathlib import Path

import httpx

from contracts.client import EdgeApiClient, GatewayCredential
from runtime.config.activation import activate_runtime_config
from runtime.config.loader import ConfigRejectedError, load_runtime_config
from runtime.forwarding.forwarder import UpstreamUnavailableError, forward_pending_batch
from runtime.health.reporter import collect_health_snapshot
from runtime.ingestion.pipeline import MappingRegistry, normalize_observation
from runtime.observability.logging_setup import configure_logging
from runtime.security.clock import evaluate_clock_health
from runtime.security.identity import generate_gateway_fingerprint
from runtime.security.secrets import SecretStore
from runtime.security.software_update import UpdateRejectedError, install_signed_update
from runtime.supervisor.supervisor import ConnectorSupervisor
from storage.db import connect, migrate

logger = logging.getLogger("edge.cli")


async def cmd_enroll(args: argparse.Namespace) -> int:
    client = EdgeApiClient(args.server_url)
    try:
        username = input("GxP username (Site Admin): ")
        password = getpass.getpass("Password: ")
        jwt = await client.login(username, password)

        host_identity = args.host_identity or socket.gethostname()
        fingerprint = generate_gateway_fingerprint(host_identity)

        challenge = await client.request_enrollment_signature_challenge(jwt, args.bootstrap_token, fingerprint)
        reauth_password = getpass.getpass("Re-enter password to sign enrollment (Part 11 step-up): ")
        result = await client.enroll(
            jwt, bootstrap_token=args.bootstrap_token, site_id=args.site_id, gateway_fingerprint=fingerprint,
            challenge_id=challenge["challenge_id"], reauth_password=reauth_password,
            reason=args.reason or "Initial gateway enrollment",
        )

        secrets = SecretStore(Path(args.state_dir) / "secrets")
        if result.get("bearer_token"):
            secrets.put("service_identity_bearer_token", result["bearer_token"])
        secrets.put("gateway_fingerprint", fingerprint)

        conn = connect(Path(args.state_dir) / "edge.db")
        migrate(conn)
        conn.execute(
            """
            INSERT INTO edge_gateway_state (id, gateway_id, tenant_id, site_id, host_identity, gateway_fingerprint,
                                             runtime_state, config_endpoint, enrolled_at)
            VALUES (1, ?, ?, ?, ?, ?, 'ENROLLED', ?, datetime('now'))
            ON CONFLICT(id) DO UPDATE SET gateway_id=excluded.gateway_id, runtime_state='ENROLLED'
            """,
            (result["gateway_id"], args.tenant_id, args.site_id, host_identity, fingerprint, result["config_endpoint"]),
        )
        print(f"Enrolled gateway {result['gateway_id']} (state dir: {args.state_dir})")
        return 0
    finally:
        await client.aclose()


async def cmd_run(args: argparse.Namespace) -> int:
    """Section 13's steady-state loop: refresh/activate config, supervise connectors, forward the outbox
    and report health on a timer. `expected_version` tracks the server's `edge_gateways.version`
    optimistic-concurrency column (MUT-FR-009) via each mutation's own `resulting_version` receipt field,
    starting from `GET /edge/v1/gateways/{id}`'s current value."""
    state_dir = Path(args.state_dir)
    conn = connect(state_dir / "edge.db")
    migrate(conn)

    gateway_row = conn.execute("SELECT * FROM edge_gateway_state WHERE id = 1").fetchone()
    if gateway_row is None:
        print("Gateway is not enrolled -- run `edge-gateway enroll` first", file=sys.stderr)
        return 1
    gateway_id = gateway_row["gateway_id"]

    secrets = SecretStore(state_dir / "secrets")
    bearer_token = secrets.get("service_identity_bearer_token")
    if bearer_token is None:
        print("No service-identity credential in secret store", file=sys.stderr)
        return 1

    api = EdgeApiClient(args.server_url)
    http_client = api.bind_service_identity(GatewayCredential(identity_id=gateway_id, bearer_token=bearer_token))

    gateway_response = await http_client.get(f"/edge/v1/gateways/{gateway_id}")
    gateway_response.raise_for_status()
    expected_version = gateway_response.json()["version"]

    mapping_registry = MappingRegistry()
    sequence_counter = {"n": 0}

    async def observation_sink(connector_id: str, raw) -> None:
        from runtime.forwarding.outbox import append_delivery_envelope, next_gateway_sequence

        sequence_counter["n"] = max(sequence_counter["n"], next_gateway_sequence(conn))
        envelope = normalize_observation(
            raw, gateway_id=gateway_id, tenant_id=gateway_row["tenant_id"], site_id=gateway_row["site_id"],
            gateway_sequence=sequence_counter["n"], clock_quality=evaluate_clock_health(), mapping_registry=mapping_registry,
        )
        append_delivery_envelope(conn, envelope)

    supervisor = ConnectorSupervisor(conn, observation_sink)

    try:
        validated = await load_runtime_config(http_client, gateway_id)
        await activate_runtime_config(conn, supervisor, mapping_registry, validated)
    except ConfigRejectedError as exc:
        logger.error("initial config load rejected: %s -- gateway will retry on next cycle", exc)

    iterations = 0
    max_iterations = args.max_iterations  # None in production; set by tests for determinism
    while max_iterations is None or iterations < max_iterations:
        try:
            result = await forward_pending_batch(
                conn, http_client, gateway_id=gateway_id, expected_version=expected_version,
                idempotency_key=f"forward-{gateway_id}-{iterations}",
            )
            if result.sent_event_ids:
                logger.info("forwarded batch: sent=%d acked=%d", len(result.sent_event_ids), len(result.server_ack_event_ids))
        except UpstreamUnavailableError as exc:
            logger.warning("upstream unavailable, buffering continues: %s", exc)

        clock_quality = evaluate_clock_health()
        snapshot = collect_health_snapshot(conn, state_dir / "edge.db", supervisor, clock_quality, cert_expiry_days=None)
        try:
            health_response = await http_client.post(
                f"/edge/v1/gateways/{gateway_id}/health",
                json={
                    "idempotency_key": f"health-{gateway_id}-{iterations}", "expected_version": expected_version,
                    "operational_state": "RUNNING", "metrics": snapshot.to_dict(), "clock_quality": clock_quality.model_dump(mode="json"),
                },
            )
            if health_response.status_code < 300:
                expected_version = health_response.json().get("resulting_version", expected_version)
        except httpx.HTTPError as exc:
            logger.warning("health report failed: %s", exc)

        iterations += 1
        if max_iterations is None:
            await asyncio.sleep(args.poll_interval_seconds)

    await api.aclose()
    return 0


def cmd_install_update(args: argparse.Namespace) -> int:
    """Document 43 EDGE-FR-019's one real (human/deployment-script-invoked, never automatic) caller.
    `--health-check-command` is an optional real shell command a real deployment supplies to say what
    "healthy after this update" means for its own environment (exit code 0 = healthy) -- this codebase
    does not invent that definition; if omitted, the health check is simply "the local SQLite store the
    supervisor/outbox depend on is reachable", the one health fact this function can honestly assert on
    its own without a running gateway process to probe.
    """
    import subprocess

    conn = connect(Path(args.state_dir) / "edge.db")
    migrate(conn)

    def health_check() -> bool:
        if args.health_check_command:
            return subprocess.run(args.health_check_command, shell=True, check=False).returncode == 0
        conn.execute("SELECT 1").fetchone()
        return True

    try:
        result = install_signed_update(
            conn, Path(args.staged_dir), expected_version=args.expected_version,
            change_id=args.change_id, health_check=health_check,
        )
    except UpdateRejectedError as exc:
        print(f"{exc.code}: {exc.detail}", file=sys.stderr)
        return 1

    print(json.dumps({
        "old_version": result.old_version, "new_version": result.new_version,
        "status": result.status, "detail": result.detail,
    }))
    return 0 if result.status == "activated" else 2


def cmd_status(args: argparse.Namespace) -> int:
    db_path = Path(args.state_dir) / "edge.db"
    if not db_path.exists():
        # A never-enrolled gateway (state dir not even created yet) is a normal, expected condition --
        # not an error -- and must be reported as such rather than failing to open a missing database.
        print(json.dumps({"enrolled": False}))
        return 1
    conn = connect(db_path)
    row = conn.execute("SELECT * FROM edge_gateway_state WHERE id = 1").fetchone()
    if row is None:
        print(json.dumps({"enrolled": False}))
        return 1
    print(json.dumps({k: row[k] for k in row.keys()}, default=str))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="edge-gateway")
    parser.add_argument("--state-dir", default="/var/lib/edge-gateway")
    sub = parser.add_subparsers(dest="command", required=True)

    enroll = sub.add_parser("enroll")
    enroll.add_argument("--server-url", required=True)
    enroll.add_argument("--bootstrap-token", required=True)
    enroll.add_argument("--site-id", required=True)
    enroll.add_argument("--tenant-id", required=True)
    enroll.add_argument("--host-identity")
    enroll.add_argument("--reason")
    enroll.set_defaults(func=lambda a: asyncio.run(cmd_enroll(a)))

    status = sub.add_parser("status")
    status.set_defaults(func=cmd_status)

    install_update = sub.add_parser("install-update")
    install_update.add_argument("--staged-dir", required=True)
    install_update.add_argument("--expected-version", required=True)
    install_update.add_argument("--change-id", required=True)
    install_update.add_argument("--health-check-command")
    install_update.set_defaults(func=cmd_install_update)

    run = sub.add_parser("run")
    run.add_argument("--server-url", required=True)
    run.add_argument("--poll-interval-seconds", type=float, default=10.0)
    run.add_argument("--max-iterations", type=int, default=None)
    run.set_defaults(func=lambda a: asyncio.run(cmd_run(a)))

    return parser


def main(argv: list[str] | None = None) -> int:
    configure_logging()
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())