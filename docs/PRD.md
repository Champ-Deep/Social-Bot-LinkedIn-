# PRD / Change Record — Social Bot hardening

**Living document.** Every change made to this repo in this workstream is
recorded here with the reasoning behind it, how it was verified, and anything
that still needs a human decision. Append to it; don't rewrite history.

- **Owner:** backend
- **Started:** 2026-08-10
- **Last updated:** 2026-08-12
- **Baseline:** commit `10f9fcd` (merge of product-roadmap branches)
- **State:** changes 1–4d **done, verified and committed** on
  `hardening/campaign-auth-and-migrations`. Change 5 is deferred until a
  throwaway account exists. **Change 7 (the scheduler) is the active work** — it
  needs no live account, so it is what keeps this moving meanwhile.

> ### ✅ Committed as of 2026-08-12
> The three-commit split described in §3.2 was made on branch
> `hardening/campaign-auth-and-migrations`. §3.2's "commit first" instruction is
> kept below as the record of what was done, not as an outstanding action.

---

## 0. Why this workstream exists

The product is roughly 85% built: the outreach loop, warm-up programme, rate
limiting, targeting and LLM integration are all real and tested. What stood
between it and a working system was a small number of load-bearing gaps, not
missing features.

This workstream closes the ones that do not require a live LinkedIn account, so
that the one that *does* (validating the mobile transport) can be attempted
against a codebase that is safe to deploy and a test suite that can be trusted.

**Ordering principle:** anything that makes a later mistake unrecoverable comes
first. Migrations before schema changes; a trustworthy test suite before
delicate live work.

---

## 1. Status summary

| # | Change | Status | Verified by |
|---|---|---|---|
| 1 | Campaign routes authenticated + org-scoped | **Done** | 13 new tests, incl. cross-tenant |
| 2 | Alembic migrations + safe adoption of the live DB | **Done** | 4 tests + 3 paths run manually |
| 3 | Flaky warm-up runner tests fixed | **Done** | 10/10 file runs, 8/8 full-suite runs |
| 4 | `status` parameter shadowing bug (found in passing) | **Done** | covered by the 404 assertions |
| 4b | Transport fallback no longer hides the primary error | **Done** | 1 new test + live probe |
| 4c | One-command account validator (`scripts/validate_account.py`) | **Done** | 19 tests + 5 end-to-end checks |
| 4d | `0002` aborts instead of deleting orphan campaigns | **Done** | 2 tests, incl. the recovery path |
| 5 | Validate mobile transport on a real account | **Deferred** | account to be obtained later |
| 7 | Scheduler to drive warm-up / sync / send | **In progress** | — |
| 6 | Bind the Playwright fallback executor | **Not started** | blocked behind 5 by design |

Test suite: **193 passing.**
Baseline before this work: 161 passing + 11 unreliable (~50% failure rate).
Stability was measured at the time of change 3 — the previously flaky file passed
10/10 runs and the whole suite 8/8. Nothing since has reintroduced clock or seed
dependence.

### Decisions — all resolved

**The destructive branch in migration `0002`: resolved 2026-08-12 — it aborts.**
The user chose abort over delete. `0002` no longer deletes anything under any
circumstances; with orphans and no organization to own them it fails the deploy
and hands the operator the row count plus two ways forward. See §2.7.

---

## 2. Changes

### 2.1 Campaign routes: authentication and tenant isolation

**Severity:** security. **Status:** done.

**The defect.** Every other route in the system resolved a tenancy context and
filtered by `org_id`. The campaign routes did neither — they had no auth
dependency at all, and the `campaigns` table had no owner column, so there was
nothing to scope them by even in principle. Any unauthenticated caller could
list, read, modify, start, pause and delete every organization's campaigns.

**What changed.**

| File | Change |
|---|---|
| `src/campaigns/models.py` | `Campaign.org_id` (required, FK, indexed) and `created_by_user_id` (nullable, `SET NULL`) |
| `src/campaigns/repository.py` | `CampaignRepository` / `IdempotencyRepository` take a required `org_id`; all reads go through one scoped base query |
| `src/campaigns/service.py` | `CampaignService` requires `org_id`; `update_task_status` extracted to module-level `apply_task_result` |
| `src/api/routes/campaigns.py` | `get_campaign_service` depends on `get_request_context`; every route inherits auth |
| `src/campaigns/__init__.py`, `src/infrastructure/task_bridge.py` | export + docstring follow-through |

**Decisions worth keeping.**

- **No unscoped mode, no `org_id=None` sentinel.** A repository that can be
  constructed without a tenant is the defect itself; an optional parameter would
  leave the same hole one forgotten argument away.
- **404, not 403, across tenants.** A 403 confirms the id exists, which is a
  disclosure to a caller with no right to know. Cross-org rows read as absent.
- **Idempotency keys namespaced per org** (`{org_id}:{key}`). Keys are chosen by
  the client, so collisions between tenants are expected, not exotic. In a
  shared namespace, replaying another org's key returns *their* campaign as the
  cached response — the same leak by a quieter route. Namespacing the stored key
  avoided a composite-primary-key migration.
- **The orchestrator callback has no request context**, so it does not use the
  service. `apply_task_result` derives the tenant from the task's own campaign,
  which keeps `org_id` mandatory everywhere else.

**Tests.** `tests/test_campaigns_api.py` was rewritten. The previous version
mocked the service layer out entirely, which meant it exercised none of the
wiring the defect lived in — it would have passed identically with or without
the bug. It now runs against the real app, real Clerk-shaped auth and a real
in-memory database, and covers: anonymous refusal on every route; garbage
tokens; cross-org invisibility on all six routes; list scoping; teammates in one
org sharing visibility; and idempotency keys not crossing orgs.

Shared fixtures (`clerk_keypair`, `issue_token`, `api_client`) were added to
`tests/conftest.py` so any future authenticated-route test can reuse them.

### 2.2 Database migrations (Alembic)

**Severity:** operational risk. **Status:** done.

**The problem.** Schema was created by `AUTO_CREATE_TABLES` (`create_all`) on
boot. That is fine until the first change to a table holding real data — at
which point there is no safe path forward. Change 2.1 was exactly that change.

**What changed.** `alembic.ini`, `alembic/env.py`, `alembic/script.py.mako`,
two revisions, `scripts/migrate.py`, plus `Dockerfile` / `railway.json` /
`.env.example` wiring.

**The two-revision split, and why it must not be squashed.**

- `0001_baseline` — the schema exactly as `create_all` was producing it,
  deliberately *without* the new campaign columns.
- `0002_campaign_org_scope` — adds them, with a backfill.

The deployed database has every table but no `alembic_version` row. A plain
`alembic upgrade head` would try to re-create existing tables and fail on every
boot until somebody ran a manual `stamp`. `scripts/migrate.py` detects the three
possible states and handles them:

| State | Action |
|---|---|
| `alembic_version` exists | upgrade |
| No `alembic_version`, but `campaigns` exists | stamp `0001`, then upgrade |
| Empty database | upgrade from scratch |

Squashing the revisions removes the stamp target and breaks adoption.

**Other decisions.**

- `env.py` takes the URL from `src.database.session`, not `alembic.ini` —
  duplicating URL resolution is how you migrate a database the app never opens.
- Models load via `import_all_models()`, the same registry `create_all` uses; a
  module nobody imports is invisible to autogenerate and gets silently omitted.
- `AUTO_CREATE_TABLES` is now `false` in the image and documented as local-only.
  Running both would let `create_all` invent tables no migration describes.
- The start command is `migrate && uvicorn`. The `&&` is load-bearing: a schema
  that cannot reach head must fail the healthcheck, not serve traffic.

**Backfill.** `0002` must give every existing campaign an owner, and that
information was never recorded. It assigns orphans to the **oldest organization**
(in this deployment, the only one, so it is exact rather than a guess). If **no**
organization exists at all it aborts — see §2.7, which supersedes the destructive
branch this section originally described.

**Verification.** `tests/test_migrations.py` (4 tests): migrations produce a
schema identical to the models (drift guard — a model change without a migration
now fails CI); `head → base → head` round-trips; and both backfill branches.
All three adoption paths were also run by hand, including simulating the live
database with a campaign in it — the campaign survived and was adopted.

### 2.3 Flaky warm-up runner tests

**Severity:** blocks trustworthy CI. **Status:** done.

**The problem.** `tests/test_warmup_runner.py` failed roughly half the time —
confirmed on unmodified code with all other changes stashed, so it was
pre-existing, not introduced here.

**Root cause — two independent sources, both correct behaviour:**

1. The daily plan is seeded by `(account_id, day)`. Each test creates a fresh
   random account UUID and used the real date. The `observe` stage plans likes
   with `probability=0.8`, so **one day in five is a deliberately quiet day**
   with zero likes. A test asserting "it liked something" was asserting a coin
   flip.
2. The active window is 08:00–19:00, but tests asked at `now=18:00`. Anything
   the planner scattered into the final hour was not yet due.

Neither is a product bug — quiet days and pacing are the design.

**Fix.** Pinning a lucky seed would work until the next volume-band change
silently un-pinned it. Instead `day_that_plans()` searches forward from a fixed
date for a day on which *this* account really is scheduled to perform the action
under test, using the same planner the runner uses; `end_of_day()` puts the
clock past every scheduled time. Deterministic, and self-correcting if the bands
are retuned. A failed search raises a message naming the account, action and
stage rather than an opaque assertion.

**Two tests were also strengthened while in there** — they had been passing
vacuously. `test_the_same_post_is_never_engaged_with_twice` now asserts that
something *was* liked before checking for repeats (an empty day trivially has no
duplicates), and `test_only_actions_that_are_due_are_performed` now runs on a
day with actions planned, so it proves pacing rather than passing because there
was nothing to do.

**Verification.** 10/10 runs of the file; 8/8 full-suite runs. Other tests using
the real clock (`test_sequences`, `test_warmup`, `test_outreach_flow`) were
inspected and derive their values relatively, so they are time-independent.

### 2.4 `status` parameter shadowing (found in passing)

**Severity:** latent 500. **Status:** done.

In `src/api/routes/campaigns.py`, the `status` query parameter shadowed the
imported `fastapi.status` module inside `list_campaigns` and
`get_campaign_tasks`. Any `status.HTTP_404_NOT_FOUND` reference in those
handlers raised `AttributeError`, so "campaign not found" returned a 500 instead
of a 404. It had always been broken and nothing exercised it; the new
cross-tenant 404 assertions surfaced it immediately.

Both parameters are renamed `status_filter` and exposed unchanged as `?status=`
via `alias`, so the API contract is identical.

### 2.5 Transport fallback hid the error that matters

**Severity:** blocks change 5 (live validation). **Status:** done.
**Found by:** running preflight locally against a deliberately invalid session
while preparing the task-5 runbook.

**The defect.** In `CompositeTransport._dispatch`, when the primary (mobile)
*and* the fallback (Playwright) both failed, the returned error was
`str(exc2)` — the fallback's — and the primary's was discarded.

The Playwright executor is not bound yet, so its error is always the same
sentence: `no playwright executor bound for <action>`. That means **every**
Voyager failure was being reported as a Playwright wiring problem, with the
actual LinkedIn response thrown away.

This made the documented procedure for change 5 impossible: BACKEND_HANDOFF §4
says to "watch `suggestion.error` for the failure from every shape tried", but
no Voyager error could reach that field.

**Fix.** Both errors are now reported — joined in `error`, and separated in
`detail` as `primary_error` / `primary_via` / `fallback_error` / `fallback_via`.

**Before:**
```
no playwright executor bound for whoami
```
**After (same invalid session):**
```
mobile: voyager request failed: Failed to perform, curl: (47) Maximum (30)
redirects followed || playwright: no playwright executor bound for whoami
```

The second one is a diagnosis: LinkedIn is bouncing the request to the login
page, i.e. the cookie is invalid or expired.

**Noted, not fixed:** the mobile session follows redirects, so an invalid cookie
surfaces as a redirect loop rather than a clean 401. Disabling redirect-following
would give a cleaner signal, but it changes live transport behaviour that has
never been exercised against a real account — the wrong thing to alter on the eve
of validating it. Revisit once change 5 has a known-good baseline.

### 2.6 One-command account validator

**Severity:** enabler for change 5. **Status:** done.

**Context.** The runbook for validating a live account was a sequence of curl
calls, a hand-minted dev JWT and JSON piping — fine once, bad as an inner loop,
and payload iteration *is* an inner loop.

The user asked whether Claude in Chrome could drive it. It cannot, and the
reasons are worth keeping:

1. Its MCP tools are not connected in this environment.
2. `li_at` is **HttpOnly** — page JavaScript cannot read it by design, which is
   why the docs point at the DevTools Application panel.
3. Decisively: **driving a browser would validate nothing.** Change 5 exists to
   prove `src/infrastructure/transports/mobile.py` works. A browser exercises
   none of that code, so success there would be a false positive about the exact
   thing under test.

Cookie capture therefore stays manual (agreed with the user). A Playwright
capture helper was considered and rejected as unnecessary: it would add a ~150MB
browser download, and logging in through an automated browser can itself trigger
a LinkedIn checkpoint.

**`scripts/validate_account.py`** — connect + preflight in one command.

| Invocation | Purpose |
|---|---|
| `validate_account.py` | connect a new account, then preflight |
| `--account-id <id>` | preflight again — **the iteration loop**, creates no duplicate account |
| `--account-id <id> --rotate` | replace expired cookies, then preflight |

Design decisions:

- **Drives the HTTP API, not the Python internals.** It exercises the same path
  the product does — auth, Fernet round-trip, transport selection — so it cannot
  pass while the real flow is broken, and `--api-base` retargets it at Railway.
- **Normalises `JSESSIONID`.** DevTools shows it quoted; the transport re-quotes
  it at `src/infrastructure/transports/mobile.py:153`, so a pasted quoted value
  becomes double-quoted, the CSRF header stops matching, and `whoami` *still
  passes* while every write fails. Silent, expensive, and now impossible.
- **Fails early and specifically** via `/healthz` — missing `ENCRYPTION_KEY`,
  unreachable API, database not ready — instead of surfacing as a confusing 500
  during connect. Warns loudly if the insecure dev encryption key is in use,
  because a real session cookie would then sit under a publicly known key.
- **Credentials never appear anywhere.** Read from env or a no-echo prompt, never
  argv (shell history), masked to a 4-char prefix in all output including errors.
  No password handling: the legacy `account_manager_agent._authenticate_with_playwright`
  password path is explicitly not reused — it contradicts
  `src/accounts/schemas.py:14-20`.
- Exit code 0/1 so it can drive a loop.

**Verification.** 19 unit tests on the pure helpers. End-to-end against a running
server with a deliberately invalid cookie: the real Voyager error surfaces
(`mobile: voyager request failed ... redirects followed`, not the Playwright
placeholder — see 2.5), the quoted `JSESSIONID` is stored stripped (17 chars in,
15 stored), `--account-id` and `--rotate` leave the account count at 1, the
server-down path gives a start command rather than a traceback, and a grep of
stdout/stderr confirms no cookie value or unmasked prefix ever appears.

Suite: **192 passing**.

### 2.7 Migration `0002` aborts instead of deleting

**Severity:** data safety. **Status:** done. **Decided by:** the user, 2026-08-12.

The open decision from §2.2 is closed: **abort, never delete.** The reasoning
behind the delete was sound (no organizations ⇒ no users ⇒ nobody can own or
reach those rows) but it rested on an assumption about production that only the
owner can confirm, and the asymmetry is decisive — an aborted deploy is a
five-minute conversation, a wrong delete is unrecoverable.

`0002` now raises with the orphan count and two documented ways forward: create
the organization that should own them and re-deploy (the oldest org adopts them
automatically), or delete the rows deliberately by hand and re-deploy. It also
prints the `SELECT` to inspect them first.

**A bug in this change, found by its own test.** The abort was first placed where
the delete had been — *after* the two `add_column` calls. On SQLite there is no
transactional DDL (Alembic logs `Will assume non-transactional DDL`), so those
columns survived the rollback and the re-run died on `duplicate column name:
org_id`. The abort message tells the operator to fix the data and re-deploy, and
that instruction would have failed on the second step.

Postgres would have rolled it back cleanly, so production was never at risk — but
local development runs on SQLite (`USE_SQLITE=true`, and the change-5 runbook uses
it), so this would have been found the hard way by whoever tried the recovery
path first.

**Fix:** the orphan check moved *above* all DDL, so an abort touches nothing on
any backend. At revision `0001` the `org_id` column does not exist yet, which
makes `SELECT COUNT(*) FROM campaigns` exactly the orphan count — the pre-check
is simpler than the post-check it replaced, not more complex.

**Tests.** The delete assertion became `test_backfill_aborts_when_no_org_can_own_
the_orphans`, which now asserts the row survives, `alembic_version` still reads
`0001`, **and** that neither column was added — the last of these is what caught
the bug. A new `test_upgrade_succeeds_once_an_org_exists_to_adopt_them` walks the
documented recovery path end to end (abort → create org → re-run → adopted),
because an instruction given to an operator in a failure message is worth proving.

Suite: **193 passing**.

---

## 3. Picking this back up

### 3.1 Environment

No project dependencies were installed on this machine when the work started, so
nothing could be verified. A virtual environment now exists at `.venv`
(Python 3.12, gitignored). It should still be there; recreate it if not:

```bash
py -3.12 -m venv .venv
./.venv/Scripts/python.exe -m pip install -r requirements.txt
```

Confirm the starting point before changing anything — expect **192 passed**:

```bash
./.venv/Scripts/python.exe -m pytest -q
```

Run the app locally (this is also the setup change 5 needs):

```bash
# One-off: generate a key. Do not use the insecure dev fallback with real cookies.
./.venv/Scripts/python.exe -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

export USE_SQLITE=true CLERK_DEV_UNSAFE=true ENCRYPTION_KEY="<the key>"
./.venv/Scripts/python.exe scripts/migrate.py
./.venv/Scripts/python.exe -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000
```

`GET /healthz` should report `database: ok` and `credentials_encryption: ok`.
`redis: not configured` and `sending: disabled` are expected and fine — preflight
does not send, so change 5 does not need Redis. Sending (change 5, step 2) does.

`CLERK_DEV_UNSAFE=true` skips JWT signature verification. **Local only.**

### 3.2 First action on resuming

Commit. `HEAD` is still the baseline and every change below is working-tree only.
Suggested split, so the security fix is reviewable on its own:

1. `alembic/`, `alembic.ini`, `scripts/migrate.py`, `tests/test_migrations.py`,
   `Dockerfile`, `railway.json`, `.env.example`, `src/api/main.py` — migrations
2. campaign auth/org-scoping + its tests
3. flaky-test fix, transport fallback fix, `scripts/validate_account.py`, docs

Branch first — the repo's default branch is `main` and these are not trivial.

### 3.3 File manifest

**New (10):**
```
alembic.ini
alembic/env.py
alembic/script.py.mako
alembic/versions/0001_baseline.py
alembic/versions/0002_campaign_org_scope.py
scripts/migrate.py
scripts/validate_account.py
tests/test_migrations.py
tests/test_validate_account.py
docs/PRD.md                      (this file)
```

**Modified (17):** `src/campaigns/{models,repository,service,__init__}.py`,
`src/api/routes/campaigns.py`, `src/api/main.py`,
`src/infrastructure/{api_client,task_bridge}.py`,
`tests/{conftest,test_campaigns_api,test_transports,test_warmup_runner}.py`,
`Dockerfile`, `railway.json`, `.env.example`,
`docs/{BACKEND_HANDOFF,CONNECTING_AN_ACCOUNT}.md`.

**Not mine:** `HOW_IT_WORKS.md` was already untracked when this workstream began.

**Gitignored, safe to delete:** `.venv/`, `test_campaigns.db` (local scratch DB;
delete it to start from a clean schema).

---

## 4. Next up

### 4.1 Change 5 — validate the mobile transport on a real account

The highest-value remaining step, and the only one that cannot be done from a
keyboard alone. Everything needed to attempt it is now in place.

**You need:** a **throwaway** LinkedIn account (not yours, not the company's),
ideally aged a day or two with a photo and a plausible headline. The request
shapes are unproven, and finding that out is exactly what gets an account
restricted.

**Do:**
1. Bring up the local server (§3.1).
2. Get `li_at` and `JSESSIONID` from DevTools → Application → Cookies →
   `https://www.linkedin.com`. **Both from the same browser session** — mixing
   them yields a session that passes `whoami` and fails every write.
3. `CLERK_DEV_UNSAFE=true python scripts/validate_account.py`
4. Iterate: edit `src/infrastructure/transports/mobile.py`, re-run
   `--account-id <id>`. Use `--rotate` when the cookie expires mid-session.

**Reading the result.** If `whoami` passes, the hard part is proven — Voyager
rejects the request outright unless headers, cookies, TLS fingerprint and CSRF
are *all* correct at once. The other three probes are graded, not pass/fail:
`fetch_profile` failing costs copy quality, `fetch_activity` failing leaves
warm-up nothing to like, and **`fetch_inbox` failing is the one that matters** —
reply detection goes blind and sequences would talk over a real conversation.

**Known failure signature.** `curl: (47) Maximum (30) redirects followed` means
LinkedIn is bouncing to the login page: the cookie is wrong or expired. Anything
else is a payload shape worth reading closely.

**Then, and only then**, do one real write and confirm it in a browser with your
own eyes before trusting the success response.

### 4.2 After that

1. **Bind the Playwright fallback** (`get_transport(..., playwright_executor=None)`
   in `src/infrastructure/api_client.py`) — deliberately *after* 4.1, so it is
   bound against known-good behaviour rather than guesses.
2. **A scheduler.** Nothing drives `warmup.runner.run_today`,
   `outreach.sync.sync_account` or `outreach.execute.run_due` on a tick, and
   `main.py` does not call them either — so deploying the agent runtime as-is
   would not help. **This is the largest remaining gap:** the programme is fully
   built but not autonomous, and today someone has to poke an endpoint for a
   warm-up day to happen at all.
3. WebSocket server so the approval queue stops polling.

### 4.3 Smaller things noticed but not done

- No preflight button on the Accounts page — you connect on `/accounts`, then go
  to `/warmup`, select the account and press "Test connection".
- No credential-rotation UI, though `accountApi.rotateCredentials` exists
  (`frontend/src/lib/api.ts:176-182`) and the docs tell users to rotate there.
  `scripts/validate_account.py --rotate` covers it from the CLI meanwhile.
- `proxy_url` and `timezone` are supported by the API and typed in
  `frontend/src/types/index.ts`, but absent from the connect form.
- The mobile session follows redirects, so a bad cookie surfaces as a redirect
  loop rather than a clean 401 (see §2.5). Worth cleaning up *after* 4.1
  establishes a known-good baseline, not before.

---

## 5. Change log

| Date | Entry |
|---|---|
| 2026-08-10 | Document created. Sections 2.1, 2.2, 2.3, 2.4 completed and verified. |
| 2026-08-10 | 2.5 added: transport fallback was masking every Voyager error behind the unbound-Playwright message. Found while dry-running the change-5 runbook locally; fixed and tested. Suite now 173 passing. |
| 2026-08-10 | 2.6 added: `scripts/validate_account.py` replaces the curl runbook for change 5. Claude in Chrome evaluated and ruled out (reasons recorded in 2.6). Suite now 192 passing. |
| 2026-08-10 | **Workstream paused after 4c.** §3 rewritten as a resume guide (environment, commit plan, file manifest); §4 expanded into an executable runbook for change 5. Flagged that nothing is committed and that the §2.2 backfill decision is still outstanding. |
| 2026-08-12 | Resumed. State verified against the repo: `HEAD` still `10f9fcd`, 27 files uncommitted, 192 passing — the §1 table was accurate. |
| 2026-08-12 | 2.7 added: the §2.2 open decision resolved by the user — `0002` aborts, never deletes. Writing the test for it exposed that the abort left DDL behind on SQLite and broke its own documented recovery path; check moved above all DDL. Suite 193. |
| 2026-08-12 | **Work committed** on `hardening/campaign-auth-and-migrations` in the three-commit split from §3.2. §3's "nothing is committed" warning is now historical. |
| 2026-08-12 | Change 5 deferred by the user (account to be obtained later). Change 7 (scheduler) brought forward, since it needs no live account — see §6. |
