# infra/

Local infrastructure this deployment runs directly with Docker (not via `docker-compose` — each
service was provisioned individually with explicit resource limits given this shared host's disk/memory
headroom).

## NATS JetStream (WP-11, ADR-0011 / SG-183)

Real transport for the transactional-outbox publisher (Document 73). Config: `nats-server.conf`.
Container: `ebmr-new-nats`.

- Bound to `127.0.0.1:4222` (client) / `127.0.0.1:8222` (monitoring) only — never exposed beyond this
  host.
- `--memory=160m --memory-swap=160m`, JetStream `max_file_store: 512MB` / `max_memory_store: 64MB`,
  `--restart unless-stopped` (survives host reboots without needing PM2).
- Data persisted at `nats-data/` (gitignored) — safe to delete when the container is stopped; it only
  holds the JetStream stream, which is rebuildable from the authoritative PostgreSQL outbox table
  (AG-09: NATS is transport, never authoritative).

Recreate if the container is ever removed:

```bash
docker run -d --name ebmr-new-nats \
  --memory=160m --memory-swap=160m \
  --log-opt max-size=5m --log-opt max-file=2 \
  --restart unless-stopped \
  -p 127.0.0.1:4222:4222 -p 127.0.0.1:8222:8222 \
  -v /home/hepin/mydata/eBMR-new/infra/nats-data:/data \
  -v /home/hepin/mydata/eBMR-new/infra/nats-server.conf:/etc/nats/nats-server.conf:ro \
  nats:2.10-alpine -c /etc/nats/nats-server.conf -m 8222
```

Check health: `curl http://127.0.0.1:8222/varz`. Check resource use: `docker stats ebmr-new-nats --no-stream`.

`GXP_NATS_URL` (default `nats://127.0.0.1:4222`) points `app/modules/eventbus/jetstream.py` at this
broker. The app starts even if it is unreachable (transport dependency, not authoritative — MUT-FR-022
still requires the *authoritative* DB to be up, not the transport).

## Temporal (WP-11 Stage 2, ADR-0011 / SG-183)

Real Temporal dev-server (embedded SQLite persistence — no separate Postgres/Elasticsearch container,
matching the tight-resource-limit discipline the NATS provisioning above already established). Not a
Docker container this time: the `temporal` CLI is a single self-contained binary
(`/usr/local/bin/temporal`, MIT license, installed from the official `temporalio/cli` GitHub release),
managed the same way `ebmr-new-api`/`ebmr-new-frontend` already are — PM2, process name
`ebmr-new-temporal`, so it survives session boundaries and host reboots (`pm2 save` was run after
adding it; PM2 itself is already `systemd`-enabled).

- Bound to `127.0.0.1:7233` (gRPC) / `127.0.0.1:7243` (HTTP) only — never exposed beyond this host.
  `--headless` (no Web UI) to keep the footprint minimal — measured at ~130MB RAM.
- Persistence: `temporal-data/temporal.db` (gitignored) — safe to delete when the process is stopped;
  it only holds workflow *execution history* (Temporal's own bookkeeping), never regulated GxP state
  (AG-10: Temporal orchestrates, it is never regulatory truth — the outcome any workflow here cares
  about is re-read from the owning GxP service, not from this file).

Recreate if the PM2 process is ever removed:

```bash
pm2 start /usr/local/bin/temporal --name ebmr-new-temporal -- \
  server start-dev --headless --ip 127.0.0.1 --port 7233 --http-port 7243 \
  --db-filename /home/hepin/mydata/eBMR-new/infra/temporal-data/temporal.db
pm2 save
```

(Run as the `frappe` user, matching every other PM2-managed process on this host:
`su -s /bin/bash frappe -c "..."`.)

Check health: `temporal operator namespace list --address 127.0.0.1:7233`. Check resource use:
`pm2 list` (or `pm2 monit`).

`GXP_TEMPORAL_TARGET` (default `127.0.0.1:7233`) points `app/modules/workflowops/client.py` at this
server. The app starts even if it is unreachable (orchestration dependency, not authoritative — same
fail-open posture as NATS, and for the same reason: AG-10 makes Temporal never regulatory truth).

**Scope built so far**: one real workflow, `StepStuckDetectionWorkflow` (`app/modules/workflowops/
workflows.py`) — see `PHASE_4_WP11_STAGE2.md` for exactly what it does and does not cover. The rest of
Document 11's Temporal-dependent scope (SG-048) remains on the pre-existing `workflowops` stand-in
functions, untouched by this pass.
