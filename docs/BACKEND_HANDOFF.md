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
  Railway with Postgres and Redis. Identity/tenancy (Clerk), campaign CRUD,
  global rate-limiter and the OpenRouter LLM provider are done (99 tests).
- **The outreach loop is REAL and end-to-end**: connect account → define ICP →
  import people → agent suggests who to contact and what to say → a human
  approves/edits/rejects → paced send under a global per-account cap. This is
  the product's spine; see §4a. Nothing reaches LinkedIn without an approval.
- **The mobile transport now calls real Voyager endpoints** (whoami, invite,
  message, like, comment, post, profile, inbox) over a TLS-fingerprinted
  session with a stable per-account device identity, with Playwright as the
  fallback. It is validated against a recording transport in tests but has not
  yet been proven against a live LinkedIn account — see §4 for exactly what
  that means.
- Multi-account is modeled *and used* (Org → User → ConnectedAccount), and the
  admin dashboard aggregates across accounts today (`GET /outreach/dashboard`).
  Per-account worker containerization remains PLANNED — design in §8.

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
- **Deployed today:** the **web service**, with Postgres and Redis attached.
  The outreach loop runs entirely inside it — generation, approval and sending
  are all synchronous API calls, so it works without the agent runtime. The
  agent runtime (which will drive *scheduled* sending via `execute.run_due`)
  is not yet deployed, so today a due send is triggered by
  `POST /outreach/accounts/{id}/run` rather than a background tick.
- `GET /healthz` reports component readiness (redis, database, encryption key,
  LLM, and whether sending is enabled) — check it first when something is off.

Key modules:
| Area | Path | Status |
|---|---|---|
| FastAPI app + SPA serving | `src/api/main.py` | REAL |
| Campaign CRUD | `src/campaigns/*`, `src/api/routes/campaigns.py` | REAL |
| Identity/tenancy (Clerk) | `src/api/middleware/clerk.py`, `src/tenancy/*` | REAL |
| Connected accounts | `src/accounts/*`, `src/api/routes/accounts.py` | REAL |
| Credential encryption (Fernet) | `src/accounts/crypto.py` | REAL |
| Caps & pacing policy | `src/accounts/caps.py`, `src/outreach/pacing.py` | REAL |
| ICP + relevance scoring | `src/targeting/*` | REAL |
| Suggestion engine | `src/outreach/suggest.py` | REAL |
| Copy quality gate (anti-spam) | `src/outreach/quality.py` | REAL |
| Humanistic copywriting | `src/outreach/copy.py` | REAL (LLM + template fallback) |
| Approve / paced send executor | `src/outreach/execute.py` | REAL |
| Global rate limiter | `src/infrastructure/rate_policy.py` | REAL |
| OpenRouter LLM (2 slots) | `src/infrastructure/llm/*` | REAL |
| Campaign→agent bridge | `src/infrastructure/task_bridge.py` | REAL |
| Transport interface + router | `src/infrastructure/api_client.py`, `transports/*` | REAL interface |
| Mobile transport endpoints | `src/infrastructure/transports/mobile.py` | REAL, unvalidated live |
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

**Question: is it working with the mobile system?** The endpoints are now real
code rather than scaffolding, but they have not yet been exercised against a
live LinkedIn account. Precisely:

What's REAL and tested:
- `LinkedInTransport` protocol and the `CompositeTransport` router
  (`api_client.py`): tries mobile first, falls back to Playwright on
  `TransportUnavailable`/`TransportChallenge`.
- Per-account **device fingerprint** generation (stable UA / device-id / OS /
  app-version + curl_cffi TLS-impersonation profile): `transports/fingerprints.py`.
- Mobile **session builder**: a curl_cffi session with fingerprint headers, TLS
  impersonation, proxy, cookies, and the `csrf-token` header Voyager requires
  (its value must equal the `JSESSIONID` cookie — a common thing to get wrong).
- **All action methods are implemented** against Voyager: `whoami`,
  `fetch_profile`, `connect`, `send_message`, `like`, `comment`, `create_post`,
  `fetch_activity`, `fetch_inbox`. Each tries the current-generation ("dash")
  endpoint and then the legacy one before giving up and falling back.
- Auth failures (401/403) and throttling (429/999) raise `TransportChallenge`,
  which pauses the account rather than retrying into a restriction.

What is NOT yet proven:
- **No live-account validation.** Voyager is undocumented and its request
  shapes drift; the endpoint bodies here are written against the shapes the
  first-party clients use, but until they run against a real session we cannot
  claim they work. Expect to iterate on the exact payloads.
- The **Playwright fallback executor is still not bound**
  (`get_transport(..., playwright_executor=None)`), so if a mobile shape is
  wrong today the fallback cannot rescue it — the action fails cleanly and the
  suggestion is marked `failed` with the error recorded.
- The agent runtime's session bridge (`InteractionAgent._wait_for_response`)
  remains BROKEN, so the *agent-runtime* path still can't act. The outreach
  loop does not depend on it — it calls transports directly from the API.

**How to validate against a real account** (this is the next concrete step):
1. Connect a real account via `POST /api/v1/accounts` with a live `li_at` +
   `JSESSIONID`. The response `status` tells you immediately whether `whoami`
   worked — that alone validates session construction, headers and CSRF.
2. Import one target, generate a suggestion, approve it, and `POST .../send`.
   Watch `suggestion.result.detail.shape` to see which endpoint generation
   answered, or `suggestion.error` for the failure from every shape tried.
3. Fix payloads as needed. Because each action tries multiple shapes and the
   composite falls back, a wrong guess degrades to a clean failure rather than
   a corrupted send.
4. Then bind the Playwright executor as the safety net for shapes that break.

Ban-risk posture (why mobile-first): mobile-API traffic with stable per-account
fingerprints + the global daily caps (§5) is far lower risk than headless
Chromium. Playwright stays as the fallback only.

---

## 4a. The outreach loop — the product's spine

The path from "we have a list of people" to "a message was sent" runs entirely
through these modules, and every one of them is a place where the system can
decide *not* to act:

```
  targeting/scoring.py     is this the right person?        -> score + reasons
        │  (below the ICP floor, or excluded -> stop)
        ▼
  outreach/copy.py         what would we say to them?       -> draft
        │  (LLM via OpenRouter content slot; templates if no key)
        ▼
  outreach/quality.py      is this copy fit to send?        -> blockers/warnings
        │  (blockers -> stored as `blocked`, never shown as ready)
        ▼
  outreach/suggest.py      should we ask the user at all?   -> OutreachSuggestion
        │  (dedupe, remaining caps, daily approval budget)
        ▼
  ── HUMAN APPROVES / EDITS / REJECTS ──   (an edit is re-checked by the gate)
        │
        ▼
  outreach/pacing.py       when may it fire?                -> scheduled_for
        │  (active hours, cooldown, jitter)
        ▼
  outreach/execute.py      send it                          -> transport call
           re-checks: approved? due? in hours? copy still clean? under caps?
```

Design notes worth preserving:

- **Scoring is deterministic, not a model call.** Every suggestion can explain
  itself ("Title matches 'head of growth'"), the same person always scores the
  same, and inference cost is spent only on the few who survive. An ICP with no
  criteria matches *nobody* — it fails closed.
- **The quality gate is rules-based on purpose.** A model asked "is this spammy?"
  approves its own output. Leaked `{{placeholders}}`, booking links, pitches in
  connection notes and over-length copy are blockers; tired phrasing, generic
  openers and sender-focused copy are scored penalties surfaced to the reviewer.
- **A human edit is not an exemption.** `approve(edited_text=...)` runs the same
  gate; a person pasting a Calendly link is refused exactly like a model doing it.
- **The daily approval budget** (default 20/account) exists because a 200-item
  queue gets rubber-stamped, which is identical to having no review at all.
- **Caps are checked twice**: once when building the queue (so we don't suggest
  what can't be sent) and again at send time against the live Redis counters,
  which is the authoritative check. A refusal never consumes allowance.
- **Suppression is permanent.** Rejecting with `suppress_target` puts a person
  out of reach of every future suggestion, for every action, regardless of ICP
  changes.

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

`/healthz` (with component readiness); `/api/v1/me`; `/api/v1/agents` (stub
data); `/api/v1/campaigns` CRUD + `/start` `/pause` `/status` `/tasks`.

**Accounts** — `POST /accounts` (connect + verify), `GET /accounts`,
`GET|PATCH|DELETE /accounts/{id}`, `POST /accounts/{id}/credentials` (rotate
cookies), `POST /accounts/{id}/verify`.

**Targeting** — `POST|GET /targeting/icps`, `PATCH|DELETE /targeting/icps/{id}`,
`POST /targeting/preview` (score a hypothetical person against a draft ICP,
saves nothing, unauthenticated), `POST|GET /targeting/targets`,
`POST /targeting/targets/{id}/suppress`.

**Outreach** — `POST /outreach/suggestions` (generate), `GET
/outreach/suggestions`, `GET /outreach/suggestions/{id}`,
`POST /outreach/suggestions/{id}/approve|reject|send`,
`POST /outreach/accounts/{id}/run` (execute everything due),
`GET /outreach/activity`, `GET /outreach/dashboard` (multi-account roll-up).

All of the above are org-scoped and require auth. Full request/response shapes
in the Frontend Handoff. OpenAPI at `/docs`.

Known gaps to close: **campaigns** are still not org-scoped/authed (add
`Depends(get_request_context)` + filter by `org_id`); the WS server is not
implemented, so the UI polls.

---

## 10. Deployment & config

- **Image:** 3-stage `Dockerfile` (node build → pip → slim runtime) serving
  SPA + API on `$PORT`. `railway.json` sets the start command (shell-wrapped so
  `$PORT` expands) and `/healthz` healthcheck.
- **Live:** Railway project "Social Bot" / production / service `social-bot-web`
  + Postgres + Redis. URL: `https://social-bot-web-production.up.railway.app`.
- **Env vars** (see `.env.example`): `DATABASE_URL` (Railway Postgres) or
  `USE_SQLITE=true`; `AUTO_CREATE_TABLES=true`; optional `REDIS_URL`;
  `CLERK_JWKS_URL`/`CLERK_ISSUER` + `VITE_CLERK_PUBLISHABLE_KEY`;
  `OPENROUTER_API_KEY` (+ model slots); `MOBILE_TRANSPORT_ENABLED`.
- **`ENCRYPTION_KEY` is required to connect accounts** (Fernet key; credentials
  are encrypted at rest with it). Rotating it makes existing stored cookies
  undecryptable — accounts then need `POST /accounts/{id}/credentials`.
- **Sending is refused without Redis**, because the per-account caps cannot be
  enforced globally without it. `ALLOW_UNCAPPED_SENDING=true` overrides this;
  don't, outside local testing.
- **Agent runtime** is a separate process (`python main.py --agents ...`) not yet
  deployed; deploy it as a second Railway service with Redis attached to activate
  execution.
- **Tests:** `pytest` (99 passing). CI-friendly, no external services —
  in-memory SQLite, fakeredis, injected Clerk JWKS, and a recording transport
  (`tests/conftest.py`) that captures what *would* have been sent.

---

## 11. Recommended next steps (ordered)

1. **Validate the mobile endpoints against one real account** (§4). This is the
   single highest-value next step: everything else is built and tested, and this
   is the only thing standing between the loop and real sends.
2. **Bind the Playwright executor** as the fallback, so a drifted Voyager shape
   degrades to a slower send rather than a failure.
3. **Deploy the agent runtime** and have `scheduler_agent` call
   `execute.run_due` on a tick, so approved outreach fires on its paced schedule
   instead of needing `POST /outreach/accounts/{id}/run`.
4. **Detect invitation acceptance** (poll connections via `fetch_activity`/
   inbox) to flip targets to `connected`, which is what unlocks the
   connect → wait → follow-up-message sequence the engine already supports.
5. WebSocket server (`/ws/updates`) so the approval queue updates live instead
   of polling.
6. Org-scope + auth the legacy campaign routes.
7. Per-account worker containerization (§8); WhatsApp ingestion; smart inbox;
   content calendar/coaching. (Full phasing in the plan file.)
