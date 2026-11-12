# Railway services

One repo, one Dockerfile, three Railway services plus the Redis and Postgres plugins.

| Service | Config file | Start command | Replicas |
|---|---|---|---|
| web | `railway.json` | `uvicorn src.api.main:app` | 1+ |
| worker | `railway.worker.json` | `python -m src.jobs.worker` | 1, scalable (consumer group) |
| scheduler | `railway.scheduler.json` | `python -m src.jobs.scheduler` | exactly 1 (also guarded by a Redis lock) |

Worker and scheduler have no port and no HTTP healthcheck. Liveness is a Redis heartbeat surfaced on web `/healthz` (`components.queue`, `components.scheduler`). Set each service's config-as-code path in Settings, or set the Custom Start Command.

## Redis contract

`campaign:tasks` (stream), `campaign-workers` (group), `campaign:dead`, `campaign:delayed` (ZSET), `worker:hb:{HOSTNAME}` (60s), `scheduler:hb` (120s), `scheduler:lock` (600s). Code: `backend/src/jobs/streams.py`. Redis must be 6.2+ (XAUTOCLAIM) with persistence on, or a Redis restart drops the stream.

## Variables (names only; values live in Railway)

| Var | web | worker | scheduler |
|---|---|---|---|
| `REDIS_URL` (reference `${{Redis.REDIS_URL}}`) | yes | yes | yes |
| `DATABASE_URL` | yes | yes | yes |
| `ENCRYPTION_KEY` (same value on all three) | yes | yes | yes |
| `REQUIRE_REDIS=true` | yes | | |
| `AUTO_CREATE_TABLES=false` | (true) | false | false |
| `ALLOW_UNCAPPED_SENDING=false` | yes | yes | yes |
| `SENDING_PAUSED` (kill switch) | | optional | |
| `WORKER_BATCH` / `WORKER_MAX_ATTEMPTS` / `WORKER_CLAIM_IDLE_MS` (5 / 3 / 300000) | | optional | |
| `SCHEDULER_TICK_SECONDS` (300) | | | optional |

## Cutover

1. Deploy web first. Check `/healthz`: `redis: ok`, `queue` present.
2. Create the worker service. Logs show `worker ... ready`; `/healthz` shows `queue.workers_alive: 1`.
3. Create the scheduler service. `/healthz` shows `scheduler: ok`.
4. Scale the worker only after a clean day.

Campaigns started before the worker existed were published to pub/sub and never delivered. Re-start them (a campaign in RUNNING with pending rows needs pausing and starting again, which re-enqueues the pending rows).

## Rollback

1. Stop sending: set `SENDING_PAUSED=true` on the worker, or scale it to 0. Entries stay in the stream.
2. Scheduler problem: scale it to 0. API-triggered runs still work.
3. Bad web release: redeploy the previous deployment.
4. Full back-out: remove worker and scheduler. `DEL campaign:tasks campaign:dead campaign:delayed` only for a clean slate. No DB change to undo.

## Alert thresholds

`workers_alive == 0` for 2 min, `oldest_pending_ms > 900000`, `dead > 0`.

## Not deployed here

The legacy multi-agent runtime (`main.py`, `src/agents/**`) stays in `docker-compose.yml` only.
