# Backend Handoff — Social Bot (SalesRobot-class outbound engine)

Audience: backend engineers continuing this system. It covers the real
architecture, an honest status of every subsystem (especially the **mobile
transport** and whether LinkedIn actions actually execute today), the
**multi-account** model, the **containerization** path from one person to many,
and how the **admin dashboard** aggregates activity across all accounts.

> Status legend: **REAL** = implemented & tested · **SCAFFOLD** = interfaces/
> structure real, behavior not implemented · **BROKEN** = present but non-
> functional (known) · **PLANNED** = designed, not written.

---

## 0. TL;DR for the impatient

- The **web service** (FastAPI API + React SPA) is **REAL and deployed** on
  Railway with Postgres. Identity/tenancy (Clerk), campaign CRUD, global
  rate-limiter, OpenRouter LLM provider, and the transport *interfaces* are done
  and unit-tested (46 tests).
- **No LinkedIn action executes end-to-end yet.** The mobile transport is a
  SCAFFOLD (falls back to Playwright), the Playwright executor is not bound, and
  the agent runtime's session bridge is BROKEN. Making it work for **one person**
  is the immediate next milestone — see §4 and §11.
- Multi-account is modeled (Org → User → ConnectedAccount) and ready to build on.
  The admin-dashboard aggregation and per-account worker containerization are
  PLANNED with a concrete design in §7–§8.

---

## 1. Architecture

Two processes, one Redis, one Postgres:

```
                    ┌──────────────── Postgres (tenancy, accounts, campaigns) ─────────┐
                    │                                                                    │
  Browser ── SPA ──▶ FastAPI web service (src/api/main.py)  ──Redis pub/sub──▶ Agent runtime (main.py)
                    │   /api/v1/* + serves SPA                 events:* / commands       │  orchestrator + agents
                    └──────────────── Redis (state, rate limits, task map, events) ──────┘
```

- **API ↔ agents coupling is Redis-only.** The API never touches the agents'
  in-memory objects. It publishes commands and consumes `events:*`. This is the
  seam that makes multi-account/multi-worker scaling clean.
- **Deployed today:** only the **web service**. The agent runtime is not yet
  deployed (and Redis isn't attached), which is why campaign *execution* is a
  no-op in production even though CRUD works.

Key modules:
| Area | Path | Status |
|---|---|---|
| FastAPI app + SPA serving | `src/api/main.py` | REAL |
| Campaign CRUD | `src/campaigns/*`, `src/api/routes/campaigns.py` | REAL |
| Identity/tenancy (Clerk) | `src/api/middleware/clerk.py`, `src/tenancy/*` | REAL |
| Connected accounts model | `src/accounts/models.py` | REAL (model), routes PLANNED |
| Global rate limiter | `src/infrastructure/rate_policy.py` | REAL |
| OpenRouter LLM (2 slots) | `src/infrastructure/llm/*` | REAL |
| Campaign→agent bridge | `src/infrastructure/task_bridge.py` | REAL |
| Transport interface + router | `src/infrastructure/api_client.py`, `transports/*` | REAL interface |
| Mobile transport endpoints | `src/infrastructure/transports/mobile.py` | SCAFFOLD |
| Playwright transport | `src/infrastructure/transports/playwright.py` | REAL adapter, not bound |
| Agent runtime | `src/agents/*`, `src/infrastructure/orchestrator.py` | mixed (see §4) |
| Skeleton agents | `safety/scheduler/whatsapp_monitor/analytics_agent.py` | SCAFFOLD |

---

## 2. Data model (Postgres, SQLAlchemy 2.0 async)

Single `Base` (`src/database/models.py`), cross-dialect types (works on Postgres
and SQLite). `AUTO_CREATE_TABLES=true` bootstraps schema on boot (Alembic is the
production path — PLANNED).

REAL tables:
- **Organization** (`clerk_org_id`, `whatsapp_admin_number`, `settings`)
- **User** (`clerk_user_id`, `org_id`, `role`)
- **ConnectedAccount** (`org_id`, `user_id`, `status`, encrypted `auth_blob`,
  `device_fingerprint`, `daily_caps`, `mode`, `active_icp_id`, `last_post_at`)
- **Campaign**, **CampaignTask**, **IdempotencyKey**

PLANNED tables (designed in the plan file): ICPProfile, EngagementDirective,
SharedLinkEvent, LinkEvaluation, Post, ContentCalendarEntry, Cadence /
SequenceStep / SequenceEnrollment, InboxThread / InboxMessage, OrgModelSettings.

---

## 3. Multi-account & tenancy — how "multiple logins" work

The model already supports many accounts under one admin:

```
Organization (the admin's workspace / Clerk org)
├── User (admin)         ── owns/oversees
├── User (team member)
└── ConnectedAccount ×N   ── each = one LinkedIn identity the system acts AS
      ├─ auth_blob (encrypted cookies/li_at)      ← how it logs in as that person
      ├─ device_fingerprint (per-account)         ← mobile identity, stable
      ├─ mode + active_icp                         ← its "thought process"
      └─ daily_caps                                ← per-account limits
```

- Every account belongs to an org, so the admin dashboard is just "all
  ConnectedAccounts where org_id = my org."
- Credentials are encrypted at rest (Fernet; reuse the `AccountManagerAgent`
  key handling). **Do not** log `auth_blob`.
- **To build for one person first:** implement the `/api/v1/accounts` CRUD
  (§7 of the Frontend Handoff), the connect flow (capture `li_at`/cookies →
  encrypt → store), and generate the device fingerprint (already implemented:
  `transports/fingerprints.generate_fingerprint`).

---

## 4. The mobile system — honest status (READ THIS)

**Question: is it working with the mobile system?** Not yet — here's exactly
where it stands so there are no surprises.

What's REAL:
- `LinkedInTransport` protocol and the `CompositeTransport` router
  (`api_client.py`): tries mobile first, falls back to Playwright on
  `TransportUnavailable`/`TransportChallenge`. Unit-tested.
- Per-account **device fingerprint** generation (stable UA / device-id / OS /
  app-version + curl_cffi TLS-impersonation profile): `transports/fingerprints.py`.
- Mobile **session builder** (`MobileAPITransport.build_session`): a real
  curl_cffi session with fingerprint headers, TLS impersonation, proxy, and the
  account's auth cookie.

What's SCAFFOLD / not done:
- The mobile **action endpoints** (`like`, `comment`, `connect`, `send_message`,
  `create_post`, `fetch_activity`, `fetch_inbox`, `whoami`) currently raise
  `TransportUnavailable` — i.e. they are not implemented against LinkedIn's real
  mobile API. They exist as clearly-marked slots.
- The **Playwright fallback executor is not bound** (`get_transport(...,
  playwright_executor=None)`), so the fallback also can't act yet.
- The agent runtime's **session bridge is BROKEN**:
  `InteractionAgent._wait_for_response` is a stub ("simplified version"), so the
  agent can't obtain a browser session either.

**Net:** calling `get_transport(account).like(...)` today returns
`success=False`. No like/comment/connect/DM/post actually happens on LinkedIn
through any path yet. The plumbing and safety rails are in place; the "last mile"
(real endpoint calls, or bound Playwright + fixed session bridge) is the work.

**Fastest route to "works for one person"** (recommended order):
1. Bind a **PlaywrightTransport executor** to a live logged-in session for a
   single ConnectedAccount, and implement `like`/`comment`/`connect`/
   `send_message` via the existing `_execute_*_playwright` methods in
   `interaction_agent.py`. This gives a working vertical slice fast.
2. In parallel, implement the **mobile** `like`/`comment` against LinkedIn's
   Voyager/mobile endpoints and validate against that one real account; keep
   Playwright as the automatic fallback.
3. Fix `_wait_for_response` (BaseAgent correlation futures) so the agent-runtime
   path also works, then wire campaigns → bridge → interaction agent end-to-end.

Ban-risk posture (why mobile-first): mobile-API traffic with stable per-account
fingerprints + the global daily caps (§5) is far lower risk than headless
Chromium. Playwright stays as the fallback only.

---

## 5. Rate limiting — real, global, per-account

`src/infrastructure/rate_policy.py: AccountRateLimiter` (REAL, tested). Redis
sliding-window keyed per `connected_account_id` + action. Enforces hourly cap,
daily cap, and cooldown together; consumes a slot only on success. This replaces
the legacy in-memory per-instance limiter (which multiplied caps across the pool).
Caps come from `ConnectedAccount.daily_caps` (fallback to `LinkedInConfig`
defaults). This is the guardrail that keeps N accounts within real LinkedIn
limits — critical for the multi-account safety story.

---

## 6. LLM — OpenRouter, two configurable slots

`src/infrastructure/llm/` (REAL, tested). `LLMProvider.complete(slot, ...)` with
two slots: **content** (humanistic copywriting) and **classification** (fast
intent/relevance). Model per slot resolves: per-org override (`OrgModelSettings`,
PLANNED) → backend config default. Any OpenRouter model id. Configure via
`OPENROUTER_API_KEY`, `OPENROUTER_CONTENT_MODEL`, `OPENROUTER_CLASSIFICATION_MODEL`,
and later the admin settings UI.

---

## 7. Admin dashboard aggregation — one view over many accounts

Everything needed is derivable from Postgres (accounts, campaigns, tasks) +
Redis (live status, rate-limit usage, `events:*`). Proposed backend work:

- **Activity source of truth:** have the interaction path emit `events:*`
  (`interaction_completed`, `reply_received`, `connection_accepted`, ...). The
  `AnalyticsAgent` (SCAFFOLD) rolls these into per-account/per-org counters in
  Redis + periodic snapshots in Postgres.
- **Endpoints** (PLANNED, contracts in Frontend Handoff §8):
  - `GET /api/v1/dashboard/overview` — org totals + per-account summary (today's
    throughput vs caps, acceptance %, reply rate, status).
  - `GET /api/v1/accounts/{id}/activity` — per-account feed.
  - `GET /api/v1/dashboard/metrics?range=` — time series.
- **Live:** extend the (PLANNED) WS server with `ACCOUNT_STATUS` /
  `ACCOUNT_ACTIVITY` events so the dashboard updates without polling.
- Rate-limit usage per account is already queryable: `AccountRateLimiter.usage(
  account_id, action)`.

---

## 8. One person → many: containerization plan

Goal: isolate each LinkedIn account's automation so one account's challenge/ban
never affects others, while a single admin dashboard aggregates them.

Recommended shape (control plane + per-account workers):
- **Control plane** = the web service (API + dashboard) + Redis + Postgres.
  Shared, stateless-ish, already deployed.
- **Per-account worker** = a container running the agent runtime scoped to one
  (or a few) ConnectedAccount(s). Each worker:
  - loads only its account(s)' credentials + fingerprint,
  - owns its own browser context / mobile session,
  - reads work from Redis (`agent_type:interaction` + per-account queues),
  - honors the **global** `AccountRateLimiter` (shared Redis) so caps are
    correct regardless of worker count,
  - emits `events:*` the analytics/dashboard consume.
- **Isolation options** (pick per scale/cost):
  1. One worker container **per account** — maximum isolation (best for ban
     containment), higher cost. Natural for high-value accounts.
  2. One worker per **N accounts** (pool) — cheaper, coarser isolation.
  - Proxy per account (`ConnectedAccount.proxy`) for network isolation.
- **Orchestration:** the existing `AgentOrchestrator` already scales agent pools;
  extend it to shard by `connected_account_id`. On Railway this can be a second
  service (the agent runtime) scaled horizontally; for strict per-account
  isolation, provision a worker service per account or move to K8s (the repo has
  `deployment/` manifests to build on).

Start simple: one shared agent-runtime service handling one account, prove the
vertical slice (§4), then shard to per-account workers.

---

## 9. Current API surface (implemented)

`/healthz`; `/api/v1/me` (auth); `/api/v1/agents` (stub data);
`/api/v1/campaigns` CRUD + `/start` `/pause` `/status` `/tasks`. Full request/
response shapes in the Frontend Handoff. OpenAPI at `/docs`.

Known gaps to close: campaigns are **not org-scoped/authed yet** (add
`Depends(get_request_context)` + filter by `org_id`); the WS server is not
implemented; `/api/v1/accounts` and the vision endpoints are PLANNED.

---

## 10. Deployment & config

- **Image:** 3-stage `Dockerfile` (node build → pip → slim runtime) serving
  SPA + API on `$PORT`. `railway.json` sets the start command (shell-wrapped so
  `$PORT` expands) and `/healthz` healthcheck.
- **Live:** Railway project "Social Bot" / production / service `social-bot-web`
  + Postgres. URL: `https://social-bot-web-production.up.railway.app`.
- **Env vars** (see `.env.example`): `DATABASE_URL` (Railway Postgres) or
  `USE_SQLITE=true`; `AUTO_CREATE_TABLES=true`; optional `REDIS_URL`;
  `CLERK_JWKS_URL`/`CLERK_ISSUER` + `VITE_CLERK_PUBLISHABLE_KEY`;
  `OPENROUTER_API_KEY` (+ model slots); `MOBILE_TRANSPORT_ENABLED`.
- **Agent runtime** is a separate process (`python main.py --agents ...`) not yet
  deployed; deploy it as a second Railway service with Redis attached to activate
  execution.
- **Tests:** `USE_SQLITE=true pytest` (46 passing). CI-friendly, no external
  services (fakeredis + injected Clerk JWKS + mocked transport).

---

## 11. Recommended next steps (ordered)

1. **Vertical slice for one account** (§4 step 1): accounts CRUD + connect flow,
   bind Playwright executor, execute like/comment/connect/DM for one real
   account under the global caps. Proves the whole loop.
2. Fix `_wait_for_response` (BaseAgent correlation futures); wire campaigns →
   bridge → interaction agent; deploy the agent runtime + Redis.
3. WebSocket server (`/ws/updates`, `/ws/campaigns/{id}`) + `ACCOUNT_*` events.
4. Org-scope + auth the campaign routes; add `/api/v1/accounts`, `/icps`,
   `/settings/models`.
5. Admin dashboard aggregation endpoints + AnalyticsAgent rollups (§7).
6. Mobile endpoint implementation (§4 step 2), account by account.
7. Per-account worker containerization (§8); WhatsApp ingestion; smart inbox;
   content calendar/coaching. (Full phasing in the plan file.)
