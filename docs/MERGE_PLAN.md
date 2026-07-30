# Merging B2B Pulse and Social Bot

An assessment of how much the two products actually overlap, which should be
the base, and the order to do the work in.

---

## 0. The headline answer

**The overlap is smaller than it looks — roughly a third, and almost all of it
is plumbing rather than features.**

That sounds like bad news and isn't. Two products with 70% feature overlap are a
painful merge: you spend the effort deleting one team's work and arguing about
whose version of the same feature wins. These two barely compete on features at
all. They are two halves of the same product that were built separately:

| | B2B Pulse | Social Bot |
|---|---|---|
| Direction | **Inbound amplification** | **Outbound growth** |
| Shape | Many accounts → one post | One account → many people |
| Trigger | A tracked page publishes | An ICP match is found |
| Question it answers | "Our team should all engage with this" | "Who should I be talking to, and what do I say?" |
| Human role | Set it up, then it runs | Approve each outbound touch |

The genuine collisions are five things, listed in §3. Everything else composes.

---

## 1. What each one actually is

### B2B Pulse — 11,300 LOC, 7 Alembic migrations, 823 LOC of tests

Team amplification. You track LinkedIn company pages; when one publishes, every
subscribed team member auto-likes and posts an AI-generated comment, staggered
so it doesn't look like a bot swarm.

**Infrastructure it has that we don't:**

- **Celery + Celery Beat.** Real scheduled work: page polling every 5 min,
  session health checks every 6 h, stale-action cleanup every 10 min. *We have
  no scheduler at all.*
- **Alembic migrations** — seven of them, in sequence. *We have zero and rely on
  `AUTO_CREATE_TABLES`, which cannot alter an existing column.*
- **Docker Compose** for the whole stack, dev and prod, plus nginx.
- **Teams inside orgs** (`Org → Team → User`) and a **platform super-admin**
  (`is_platform_admin`) that can see across every org.
- **Org invites** with shareable codes, org-wide or team-scoped.
- **Audit log** with CSV export and an analytics summary endpoint.

**Product it has that we don't:**

- **LinkedIn OAuth as the login.** Signing in *is* connecting the integration —
  one step, not two.
- **Tracked pages + polling**, with official `/v2/ugcPosts` reads.
- **Coordinated engagement** with stagger, quiet hours, weekend dampening.
- **Persona groundwork**: `UserProfile.markdown_text` + `tone_settings` +
  `automation_settings` per user.
- **Two-pass comment generation** (generate → review) with a substantial
  AI-tell avoid-phrase list.
- **Instagram and Facebook** alongside LinkedIn.
- **WhatsApp sidecar + `/webhooks/whatsapp-link`** — the original use case,
  already built and working there.

### Social Bot — 22,300 LOC total, ~5,500 of portable domain logic, 3,150 of tests

Individual account growth. Warm a fresh account into looking human, then run
targeted outbound where a person approves every message.

**What only we have — and it is all safety and targeting:**

- **The warm-up programme.** Staged capability unlocking over ~21 days.
  B2B Pulse has *nothing* comparable, and it is currently driving real accounts.
- **Acceptance-rate governor.** Measures real acceptance, throttles, stops
  invitations below 15%, demotes the stage.
- **Rolling weekly invite cap** — the window LinkedIn actually enforces.
- **ICP + deterministic relevance scoring** with human-readable reasons.
- **Approval queue** — nothing outbound sends without a person seeing it.
- **Copy quality gate** — rules-based, blocks leaked placeholders, booking links
  in first touches, pitches in connection notes.
- **Sequences with pause-on-reply**, and step-aware scheduler links.
- **Per-account device fingerprints** and the Voyager mobile transport.
- **Preflight** — read-only live validation.
- **Funnel metrics** measured from real outcomes.

---

## 2. Where they genuinely overlap

Shared foundations — these merge cleanly because they're the same choices:

- FastAPI + async SQLAlchemy 2.0 + Postgres + Redis
- React 18 + Vite + TypeScript + Tailwind
- OpenRouter for all LLM inference
- Fernet-encrypted credentials at rest
- Playwright + stored session cookies as the execution path
- Org-scoped multi-tenancy
- LinkedIn like + comment as actions

Shared *features*, honestly, amount to: **like a post, comment on a post, store
a LinkedIn session, scope things to an org.** That's it.

---

## 3. The five real collisions

Everything else composes. These five need a decision.

| # | Collision | Recommendation |
|---|---|---|
| 1 | **Auth**: Clerk vs LinkedIn OAuth | **LinkedIn OAuth.** Sign-in *is* integration connect — one step. Clerk is an extra vendor, an extra bill and an extra login for a product where every user must connect LinkedIn anyway. |
| 2 | **Account model**: `ConnectedAccount` vs `IntegrationAccount` | Keep `IntegrationAccount`'s name and platform enum (it already spans LinkedIn/IG/FB); graft on our `device_fingerprint`, `daily_caps`, `warmup` state and `mode`. |
| 3 | **Comment generation**: two implementations | Keep B2B Pulse's two-pass generate→review pipeline; run our deterministic quality gate as the final arbiter after it. Their generator is better at producing; ours is better at refusing. |
| 4 | **Execution**: our Voyager transport vs their Playwright actions | Keep our `LinkedInTransport` protocol + `CompositeTransport`, and bind **their** Playwright actions as the fallback executor — which closes the gap I've been flagging in ours. Best of both. |
| 5 | **Org model**: `Org→User` vs `Org→Team→User` | Take theirs. Teams are what makes the LakeB2B case work. |

---

## 4. Which should be the base

**B2B Pulse is the base. Social Bot's domain logic ports into it.**

The reasoning is asymmetric in a way that makes this an easy call:

- Our **value is domain logic** — warm-up, governor, ICP scoring, quality gate,
  sequences. About 5,500 lines, most of it pure functions over duck-typed
  inputs, with 3,150 lines of tests that come along. It is genuinely portable.
- Our **infrastructure is the weaker half** — no scheduler, no migrations, no
  Docker Compose, no teams, no audit log, no super-admin.
- Their **infrastructure is production-shaped** and their domain logic is
  thinner — which is exactly the gap we fill.

Porting tested logic onto better infrastructure is mechanical. Adding a
scheduler, a migration history, teams, an audit log and an admin console to our
codebase is a rebuild.

> **One caveat worth stating plainly:** this means the Railway deployment we've
> been testing against becomes a staging ground rather than the final product.
> The warm-up work isn't wasted — it's the piece B2B Pulse most needs — but the
> merged product will be built in B2B Pulse's repo, not this one.

---

## 5. The risk nobody has designed for yet

This matters more than any of the above, and it sits exactly at the intersection
of the two products.

**Five LakeB2B accounts all liking and commenting on the same post is a
coordinated-inauthenticity pattern**, and it is one of the easiest things for a
platform to detect. B2B Pulse staggers delays, which helps with *timing* — but
staggering doesn't change the underlying signal:

- the same five accounts engage with the same pages, repeatedly
- often within the same hours
- with comments generated by the same model, on the same post, from the same
  prompt template

Detection doesn't need to catch one account. It catches the *cluster*, and then
all five go at once. That is a materially worse outcome than any single account
being restricted, and it is the specific risk of running five real employees'
accounts through one system.

The merged product needs, and neither half currently has:

1. **Participation sampling** — not every account engages with every post. Pick
   a subset per post, weighted by persona relevance, so the overlap between any
   two accounts stays low.
2. **Cluster-level rate limiting** — a cap on *how many of our accounts* touch
   any single post or company, on top of each account's own caps.
3. **Persona-differentiated copy** — comments generated from *different*
   personas with different angles, not one prompt with a name swapped. Two
   near-identical comments from two colleagues is the tell.
4. **Independent schedules** — different active hours and rhythms per account,
   not one org-wide quiet-hours setting.
5. **Correlation monitoring** — an admin-visible metric for "how similar is our
   accounts' behaviour", so drift toward a detectable pattern is visible before
   the platform acts on it.

I'd treat this as a first-class feature of the merged product rather than a
hardening pass at the end, because it changes the data model (participation
decisions have to be recorded per post per account).

---

## 6. The persona layer — the genuinely new build

Your ask: *five real people, represented online, each with a direction, with
admin oversight and the option to work as one campaign or independently.*

Neither product has this. The pieces exist in fragments:

- B2B Pulse: `UserProfile.markdown_text`, `tone_settings` — voice, per user
- Social Bot: `ICPProfile`, `EngagementMode` — who to target, per account

A `Persona` should own both, plus what neither has:

```
Persona
├── voice          tone, vocabulary, sentence length, what they never say
├── expertise      what this person is credible talking about
├── content_pillars  3-5 themes their posts and comments orbit
├── icp            who they should be connecting with  (from Social Bot)
├── guardrails     topics to avoid, competitors not to engage, tone limits
├── autonomy       what runs unattended vs what needs their approval
└── inherits_from  an org-level persona, overridable per person
```

`inherits_from` is what makes the LakeB2B case work: set the campaign direction
once at org level, let each person diverge where they should. An admin changes
the org persona and all five shift; one person's `content_pillars` override
survives that change.

---

## 7. Roadmap

Six phases. Each is independently shippable — you're never mid-migration with
nothing working.

### Phase 1 — Foundation (1 week)

Decide and scaffold, in B2B Pulse's repo.

- Settle auth on LinkedIn OAuth; drop Clerk. Keep our `RequestContext` shape so
  ported code doesn't care which auth produced it.
- Extend `IntegrationAccount` with `device_fingerprint`, `daily_caps`,
  `warmup_state`, `mode` — one Alembic migration.
- Port `LinkedInTransport` + `CompositeTransport`, binding their
  `linkedin_actions.py` as the Playwright fallback executor.

**Ships:** nothing user-visible. **Unblocks:** everything.

### Phase 2 — Safety (1–2 weeks) ← *do this before scaling accounts*

Port the entire safety layer. This is the highest-value phase and it is urgent:
B2B Pulse is driving real accounts today with stagger delays as its only
protection, and no warm-up at all.

- `warmup/` — programme, planner, service, runner, ledger
- `outreach/health.py` — the acceptance governor
- `accounts/caps.py` + the weekly window in `rate_policy.py`
- `accounts/preflight.py`
- Wire the warm-up gate into their engagement tasks, so a warming account can't
  be swept into a tracked-page engagement it hasn't earned.
- Schedule `runner.run_today` on Beat — **this also fixes the biggest gap in
  our side**, which is that warm-up is planned but not autonomous.

**Ships:** every account gets a warm-up ramp, a health verdict, and caps that
match what LinkedIn actually enforces. Tests port largely unchanged.

### Phase 3 — Cluster safety (1 week) ← *the §5 risk*

- Participation sampling per post
- Cluster-level caps (max N of our accounts per post/company/day)
- Per-account independent schedules
- Behaviour-correlation metric on the admin dashboard

**Ships:** five accounts can safely share a workspace.

### Phase 4 — Personas (1–2 weeks)

- `Persona` model with org-level inheritance
- Merge `UserProfile.tone_settings` and `ICPProfile` into it
- Persona-differentiated comment generation — distinct angles per persona, then
  our quality gate as the arbiter
- Admin UI: set org persona, see per-person overrides

**Ships:** the thing you actually described. Five accounts, five voices, one
direction, admin-steerable.

### Phase 5 — Outbound (2 weeks)

- `targeting/` — ICP + relevance scoring
- `outreach/` — suggestions, approval queue, quality gate, sequences, sync
- Approval queue UI

**Ships:** the accounts stop only reacting and start reaching out — under
approval, under the safety layer built in Phases 2–3.

### Phase 6 — Admin console (1 week)

Extend their platform-admin dashboard into the operator view you described:

- Every account: warm-up stage, health verdict, funnel, today's activity
- Campaign view: which accounts are on which campaign, and their combined effect
- Cross-account correlation and cluster-cap headroom
- One control to steer all five, and per-account overrides that survive it

**Ships:** the managerial view over all five accounts.

---

## 8. Sequencing rationale

Two things drive the order:

**Safety before scale.** Phases 2 and 3 come before personas and outbound
because B2B Pulse is already running real accounts without a warm-up, and the
cluster risk in §5 gets worse with every account added. Building persona
features first would mean scaling up an unsafe system.

**Nothing is thrown away.** Every phase leaves a working product. Phase 1 ships
nothing visible but breaks no existing feature; Phase 2 makes what exists safer;
Phases 4–6 add. There is no window where the merged product is worse than either
half.

---

## 9. Decisions (settled)

| Question | Decision | Notes |
|---|---|---|
| **Auth** | **Clerk** | Chosen over my LinkedIn-OAuth recommendation. Trade accepted: onboarding gains a second step (sign in, then connect LinkedIn), and in exchange login survives a LinkedIn session expiring, works for admins who never connect an account, and stays independent of the platform we automate. LinkedIn OAuth is retained purely as integration-connect. |
| **Base repo** | **B2B Pulse** | This repo becomes reference. |
| **Platforms** | **LinkedIn first, Meta in V2** | Instagram and Facebook code stays in place and keeps working; personas, warm-up and the safety layer target LinkedIn only for now. Shrinks Phase 4 materially. |
| **Approval model** | **Bulk for engagement, per-account for messaging** | See below — this one has real design consequences. |

### What the approval split means

Splitting approval by action type rather than by account is the right call, and
it changes more than it looks:

**Engagement (likes, comments) — bulk approve.** An admin sees one queue across
all five accounts and can approve in a sweep. This is what makes the LakeB2B
case workable: five separate comment queues would go unread by Friday, and an
unread queue is the same as no review at all.

The safety consequence: bulk approval removes the per-item human pause that was
implicitly slowing engagement down. **The cluster-safety work in Phase 3 stops
being a nice-to-have and becomes load-bearing**, because a single click can now
approve five accounts commenting on the same post. Participation sampling has
to run *before* the queue is built, not after approval — the admin should be
approving "these three accounts engage with this post", never "all five do".

**Messaging (invitations, DMs) — per account.** Correct, and worth the
friction. A direct message goes out under one named person's identity, in their
voice, to someone who will reply to *them*. Nobody should be able to bulk-send
messages as five colleagues. Volume also makes this tractable: caps hold
invitations to ~15/day per account, so a per-account queue stays small enough
to actually read.

Practical shape:

```
Engagement queue    org-wide, grouped by post, bulk approve
                    → sampled to a subset of accounts before it is shown
Messaging queue     per account, reviewed by that account's owner
                    → admin can see all of them, but approves within one
```

---

## 10. Status

- ✅ **Phase 1 complete** — branch `claude/merge-social-bot-phase-1` in B2B Pulse.
  Clerk auth, extended account model + migration, transport layer with the
  browser path bound as fallback. 110 tests passing (was 67, with 9 failures
  and 7 errors on the baseline).
- ⏭ **Phase 2 next** — port the safety layer. Urgent: B2B Pulse drives real
  accounts today with stagger delays as its only protection and no warm-up.
