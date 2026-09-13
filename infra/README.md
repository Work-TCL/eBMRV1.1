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

## Temporal — not yet provisioned

SG-183's other half. Not built in the WP-11 Stage 1 pass that added NATS; a future stage will add it
here following the same tight-resource-limit discipline.
