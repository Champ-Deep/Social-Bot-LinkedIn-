# Frontend Handoff — Social Bot (SalesRobot-class outbound engine)

This document is the contract between the backend and the frontend. It lists
everything the API exposes today, the auth model, the realtime contract, and the
**proposed** endpoints for the product vision (connect multiple LinkedIn
accounts, per-account direction, and one admin dashboard to watch all of them).

> Status legend: **LIVE** = deployed and working · **STUB** = route/shape exists
> but returns placeholder/limited data · **PLANNED** = agreed contract, not built
> yet (build the UI against it; backend will implement in lockstep).

Deployed base URL: `https://social-bot-web-production.up.railway.app`
API prefix: `/api/v1` · The SPA is served from the same origin, so the frontend
calls the API at a relative `/api/v1` (no CORS in production).

---

## 1. Product framing (what we're building)

A multi-channel outbound engine comparable to SalesRobot, but better:
- A person connects their LinkedIn account and gives it a **direction**
  (outreach vs account-based engagement) and an **ICP**.
- The system acts *as them* — humanistic comments, connection requests,
  follow-up DMs, occasional posts — within real LinkedIn daily limits.
- An **admin** connects/oversees **many accounts** and watches all their
  activity from **one dashboard** (acceptance %, reply rate, throughput, live
  status per account).

The frontend's north star is that admin dashboard plus the per-account control
surfaces (connect account, set direction/ICP, smart inbox, content calendar).

---

## 2. Auth model (Clerk)

- Auth is **Clerk**. The frontend obtains a Clerk session JWT and sends it as
  `Authorization: Bearer <token>` on every API call.
- The client already does this: `frontend/src/lib/clerk.tsx` bridges the Clerk
  token into the axios client (`frontend/src/lib/api.ts`).
- **Demo mode:** if `VITE_CLERK_PUBLISHABLE_KEY` is unset at build time, the SPA
  runs without login and calls the API unauthenticated. This is how the current
  deployment runs so it's clickable without keys.
- Enabling auth requires setting `VITE_CLERK_PUBLISHABLE_KEY` (frontend, build
  time — needs a redeploy) and `CLERK_JWKS_URL` / `CLERK_ISSUER` (backend).

Tenancy: a Clerk user resolves to a local **User** inside an **Organization**
(auto-provisioned on first authenticated call). Users sharing a Clerk org share
one Organization — this is the "admin sees the whole team" boundary.

---

## 3. Conventions

- **Idempotency:** `POST /campaigns` and `POST /campaigns/{id}/start` require an
  `X-Idempotency-Key` header (any unique string; the client sends a UUID).
- **Pagination:** list endpoints take `page` (>=1) and `page_size` (1–100).
  The client normalizes list responses to `{ items, total, page, page_size,
  total_pages }`.
- **IDs:** UUID strings.
- **Errors:** FastAPI shape — `{ "detail": ... }`, 422 for validation, 401 for
  auth, 404/400 for state errors.

---

## 4. Endpoints available today

### System
| Method | Path | Status | Notes |
|---|---|---|---|
| GET | `/healthz` | LIVE | `{ "status": "ok" }` |

### Identity — `/api/v1/me`
| Method | Path | Auth | Status |
|---|---|---|---|
| GET | `/api/v1/me` | required | LIVE |

Response:
```json
{ "user_id": "uuid", "org_id": "uuid", "clerk_user_id": "user_...",
  "clerk_org_id": "org_... | null", "email": "a@b.com", "role": "owner" }
```
Returns 401 without a valid token. Use it to resolve the signed-in user's org.

### Agents monitor — `/api/v1/agents`
| Method | Path | Auth | Status |
|---|---|---|---|
| GET | `/api/v1/agents` | open today | STUB (real when the agent runtime + Redis are attached) |

Response: `Agent[]`
```ts
interface Agent {
  id: string; name: string;
  type: 'account_manager'|'content_analysis'|'interaction'|'conversation'|'safety';
  status: 'idle'|'processing'|'waiting'|'error';
  tasks_completed: number; tasks_failed: number; last_activity: string; // ISO
}
```
Today returns the five configured agents as `idle` (no live runtime attached to
the deployed web service). Powers the Agent Monitor board.

### Campaigns — `/api/v1/campaigns`
| Method | Path | Auth | Status | Notes |
|---|---|---|---|---|
| POST | `/campaigns` | open today* | LIVE | needs `X-Idempotency-Key`; validates LinkedIn URLs |
| GET | `/campaigns?page=&page_size=&status=` | open today* | LIVE | returns `{ campaigns, total, page, page_size }` |
| GET | `/campaigns/{id}` | open today* | LIVE | |
| PATCH | `/campaigns/{id}` | open today* | LIVE | draft-only |
| DELETE | `/campaigns/{id}` | open today* | LIVE | soft delete; not while running |
| POST | `/campaigns/{id}/start` | open today* | LIVE | needs `X-Idempotency-Key`; enqueues work (no-op until agent runtime attached) |
| POST | `/campaigns/{id}/pause` | open today* | LIVE | |
| GET | `/campaigns/{id}/status` | open today* | LIVE | progress counters |
| GET | `/campaigns/{id}/tasks?status=` | open today* | LIVE | one task per URL |

\* Campaigns are **not org-scoped yet** — a known gap. They will require auth and
be filtered by `org_id` (see §7). Build the UI assuming they will be authed.

Campaign shapes (as the client normalizes them):
```ts
interface Campaign {
  id: string; name: string; description: string;
  status: 'draft'|'scheduled'|'running'|'paused'|'completed'|'failed'|'cancelled';
  target_urls: string[]; account_ids: string[];
  actions: { like: boolean; comment: boolean; share: boolean; follow: boolean };
  priority: number; // 1=normal 2=high 3=urgent
  progress: { total_tasks: number; completed_tasks: number; failed_tasks: number };
  created_at: string; updated_at: string; scheduled_start?: string;
}
```

---

## 5. Realtime (WebSocket) — PLANNED

The client is already written against these (`frontend/src/hooks/useWebSocket.ts`)
but the **backend WS server is not implemented yet** (next Phase 0 item). Until
then the UI falls back to polling (campaigns every 5s, agents every 3s).

- `GET /ws/updates` — org-wide stream
- `GET /ws/campaigns/{id}` — per-campaign stream

Message envelope:
```ts
interface WSMessage {
  type: 'CAMPAIGN_UPDATE'|'TASK_COMPLETED'|'TASK_FAILED'|'AGENT_STATUS'|'PROGRESS_UPDATE';
  campaign_id?: string; task_id?: string; agent_id?: string;
  data: any; timestamp: string;
}
```
For the admin dashboard we'll extend this with `ACCOUNT_STATUS` and
`ACCOUNT_ACTIVITY` (see §8).

---

## 6. What is real vs not (be honest with the UI)

- **Real & persisted:** identity/tenancy, campaign CRUD (against Postgres),
  idempotency, agent-monitor shape.
- **Not executing yet:** starting a campaign enqueues work, but no LinkedIn
  action actually runs — the agent runtime isn't attached to the deployment and
  the interaction transport is still a scaffold (see the Backend Handoff). Treat
  campaign execution as "queued" in the UI; don't promise completed actions.
- **Not built yet:** everything in §7–§8 (accounts, settings, ICP, inbox,
  content calendar, admin aggregation) and the WebSocket server.

---

## 7. Proposed endpoints — connect accounts, direction, settings

These are the contracts to design the UI around. They map 1:1 to models that
already exist in the backend (`ConnectedAccount`, `Organization`, planned
`ICPProfile` / `OrgModelSettings`).

### Connected accounts (the heart of multi-account)
```
POST   /api/v1/accounts            connect a LinkedIn account
GET    /api/v1/accounts            list this org's connected accounts
GET    /api/v1/accounts/{id}       one account (status, mode, icp, caps, last_post_at)
PATCH  /api/v1/accounts/{id}       set mode / active ICP / daily caps / proxy
DELETE /api/v1/accounts/{id}       disconnect
POST   /api/v1/accounts/{id}/reauth  refresh credentials when status=auth_required
```
`ConnectedAccount` shape:
```ts
interface ConnectedAccount {
  id: string; org_id: string; user_id: string;
  status: 'active'|'inactive'|'suspended'|'rate_limited'|'auth_required'|'error';
  display_name?: string; headline?: string; profile_url?: string;
  linkedin_member_urn?: string;
  mode?: 'outreach'|'account_based_engagement';
  active_icp_id?: string;
  daily_caps?: Record<string, {per_hour:number; per_day:number}>; // per action
  last_post_at?: string; last_active_at?: string;
  created_at: string;
}
```
**Connect flow (to finalize with backend):** the account's session is captured
(LinkedIn cookie / `li_at`, or credentials) and stored **encrypted**; a device
fingerprint is generated per account for the mobile transport. The UI needs a
"Connect account" form (cookie paste or credential capture) + a status chip that
reflects `status` (e.g. `auth_required` → prompt re-auth).

### ICP / direction
```
GET/POST /api/v1/icps            list/create ICP profiles (industries, titles, keywords, geo)
PATCH/DELETE /api/v1/icps/{id}
```

### Settings (admin)
```
GET/PUT /api/v1/settings/models   OpenRouter content + classification model per org
GET/PUT /api/v1/settings/whatsapp admin WhatsApp number (org-wide link feed)
```

### Inbox (smart inbox / take-over) — PLANNED
```
GET  /api/v1/inbox                 threads across all the org's accounts
GET  /api/v1/inbox/{thread_id}     messages in a thread
POST /api/v1/inbox/{thread_id}/reply   send (AI-drafted or manual)
POST /api/v1/inbox/{thread_id}/takeover pause automation for this lead
```

### Content calendar / coaching — PLANNED
```
GET  /api/v1/accounts/{id}/calendar        suggested + scheduled entries
POST /api/v1/accounts/{id}/calendar        add/approve an entry
POST /api/v1/accounts/{id}/posts           draft/schedule a post
GET  /api/v1/accounts/{id}/topics          AI topic suggestions from engagement history
```

---

## 8. The admin dashboard — one view over many accounts

This is the flagship screen. Proposed aggregation endpoints:

```
GET /api/v1/dashboard/overview
  → org-wide roll-up: totals + per-account summary
GET /api/v1/accounts/{id}/activity?since=&type=
  → per-account activity feed (actions taken, replies, acceptances)
GET /api/v1/dashboard/metrics?range=7d
  → time series: acceptance %, reply rate, actions/day, per account
```
`dashboard/overview` shape (proposed):
```ts
interface DashboardOverview {
  totals: { accounts: number; active: number; rate_limited: number;
            actions_today: number; replies_today: number; meetings_requested: number };
  accounts: Array<{
    id: string; display_name: string; status: string;
    mode: string; icp_name?: string;
    today: { connections: number; comments: number; messages: number; posts: number };
    caps: { connections: {used:number; limit:number}; /* ...per action */ };
    acceptance_rate: number; reply_rate: number;
    last_active_at: string;
  }>;
}
```
Realtime additions to the WS stream for this screen: `ACCOUNT_STATUS`
(status/health per account) and `ACCOUNT_ACTIVITY` (a new action/reply event).

Suggested screens:
1. **Overview** — cards per account (status light, today's throughput vs caps,
   acceptance/reply rate), org totals header, live indicator.
2. **Account detail** — activity feed, cap usage gauges, current
   direction/ICP, inbox shortcut, "take over" toggle.
3. **Connect account** — add a LinkedIn login, pick direction + ICP.
4. **Settings** — OpenRouter models, WhatsApp admin number, default caps.
5. **Smart inbox** — cross-account threads with AI-drafted replies + take-over.

---

## 9. Design system (from the original brief)

Deep navy foundation `#0B0F19`, dark slate cards `#1E293B`, vibrant purple or
gold accents for active states/CTAs. High-contrast modern SaaS. (The current
merged UI is a lighter LinkedIn-blue theme; align new screens to the navy/slate
system — this is a good moment to introduce the tokens in `tailwind.config.js`.)

---

## 10. Local dev

- Frontend: `cd frontend && npm install && npm run dev` (Vite on :3000, proxies
  `/api` + `/ws` to `http://localhost:8000`).
- Backend: `uvicorn src.api.main:app --reload` (set `USE_SQLITE=true` for a
  zero-setup DB). OpenAPI docs at `/docs`.
- Set `VITE_API_BASE` to point the SPA at a remote API if not same-origin.
