# How This Application Works — A Plain-English Walkthrough

*A guided tour of the codebase for someone new to it. Minimal jargon, maximum understanding.*

---

## What it is, in one sentence

It's a tool that helps a salesperson (or a small sales team) find the right people on LinkedIn, write a personal-sounding message to each one, get a human to approve it, and then send those messages slowly and carefully over days and weeks so LinkedIn never suspects a robot is involved.

The important word is **approve**. This is not a "press start and it spams 500 people" tool. Almost every piece of code in here exists to *stop* things from being sent. That's the whole design philosophy, and once you see it, the rest of the code makes sense.

---

## The four parts of the system

Think of it like a small office:

| Part | Where it lives | What it does |
|---|---|---|
| **The screen** (front end) | `frontend/` | The web pages the user clicks on — a dashboard, an approvals inbox, an accounts page. Built with React. |
| **The front desk** (API) | `src/api/` | Receives every click from the screen and decides what to do. Built with FastAPI (Python). |
| **The rulebook** (business logic) | `src/outreach/`, `src/targeting/`, `src/warmup/`, `src/accounts/` | All the actual thinking: who to contact, what to say, whether it's safe to send. This is the heart of the app. |
| **The hands** (transports) | `src/infrastructure/transports/` | The only code that actually touches LinkedIn. |

Two storage systems sit underneath:

- **A database** (Postgres) — the permanent memory. People, messages, approvals, history.
- **Redis** — a fast scratchpad. Used mainly as a *counter*: "how many invitations has this account sent in the last hour?"

---

## The journey of one message, start to finish

This is the best way to understand the app. Follow one message from idea to inbox.

### Step 1 — You connect your LinkedIn account
`src/accounts/service.py`

You don't give it your password. You give it your LinkedIn **session cookie** (`li_at`) — the thing your browser already holds that proves you're logged in.

The app immediately does something smart: it uses that cookie to ask LinkedIn "who am I?" If LinkedIn answers, the account is marked **active**. If not, it's marked "needs attention" *right then* — rather than you finding out three days later that nothing was working.

The cookie is encrypted before being saved (`src/accounts/crypto.py`). When it needs to be used, it's decrypted onto a temporary object that is never written back to the database — so the plain-text version can't accidentally leak into storage.

The account is also given a permanent fake "device identity" (`fingerprints.py`) derived from its ID. LinkedIn trusts accounts that always appear from the same device; an account that looks like a different phone every day looks stolen.

### Step 2 — You describe who you want to meet
`src/targeting/`

You fill in an **ICP** ("Ideal Customer Profile"): job titles, seniority, industries, keywords, locations — plus things to *exclude*.

Then you upload a list of people (from a CSV, a LinkedIn search export, etc.).

### Step 3 — Each person gets scored out of 100
`src/targeting/scoring.py`

Here's a design choice worth understanding. Most modern apps would throw this at an AI. This one deliberately **doesn't**. It uses plain matching rules:

- Title match → 35 points
- Industry match → 20 points
- Keywords → 20 points
- Seniority → 15 points
- Location → 10 points

Three reasons the file gives for avoiding AI here:

1. **You can see why.** The app tells you *"Title matches 'Head of Growth'; industry matches 'SaaS'"*. An AI similarity score explains nothing.
2. **It's consistent.** The same person always scores the same.
3. **It's cheap.** Scoring runs over thousands of people; AI runs only over the handful that survive.

Exclusions are absolute — one banned keyword zeroes the score no matter how well everything else matches. And there's a lovely defensive touch: an ICP with *no* criteria at all matches **nobody**, not everybody. An empty form can't accidentally mean "message the entire database."

### Step 4 — The app decides who's actually worth contacting
`src/outreach/suggest.py`

Every person must survive six gates:

1. **Score floor** — below your minimum? Dropped, not just ranked lower.
2. **Suppression** — if you ever said "never contact this person", they're permanently untouchable.
3. **Duplicates** — nobody gets the same type of message twice, ever.
4. **Remaining capacity** — it won't suggest more than the account can legally send today.
5. **Approval budget** — a hard daily ceiling on how many suggestions you're shown. The reason is quietly brilliant: *a queue of 200 items gets rubber-stamped*, which would silently destroy the entire value of human review.
6. **Copy quality** — covered next.

It then tells you honestly what it did: *"Reviewed 40 people, suggesting 6; skipped: 12 below relevance floor, 8 already suggested."*

### Step 5 — The message gets written
`src/outreach/copy.py`

An AI model (via OpenRouter) writes the message. It's given everything known about the recipient and a list of hard prohibitions — no flattery, no invented facts, no links, no emoji, no "I hope this finds you well", no asking for a meeting.

If no AI key is configured, it falls back to plain templates. A missing key makes the writing duller; it never breaks the product.

### Step 6 — The spam filter checks its own work
`src/outreach/quality.py`

This is arguably the most interesting file in the repo. Every drafted message is graded 0–100 by **plain rules, not AI**. The reasoning is stated directly in the file: *a model asked "is this spammy?" will happily approve its own output.*

It checks for:

- Leftover placeholders like `{{first_name}}` → **instant block**
- A calendar/booking link in a first message → **instant block**
- Too long for the message type → **block**
- Tired phrases ("just checking in", "circle back", "synergy") → points off
- Generic openers ("Hi there") → 30 points off
- SHOUTING, too many `!`, too many emoji → points off
- Talking only about yourself ("I/we" far outweighing "you") → points off
- **No personal detail at all** → 25 points off, with the note: *"this could have been sent to anyone"*

That last check is clever. It looks for whether the person's actual name, company, title, or a *distinctive* word from their headline appears in the message. Generic business words like "growth" or "solutions" don't count — echoing "growth" back at a growth lead proves nothing.

If the message fails, the app tells the AI exactly what was wrong and asks it to rewrite — up to three tries.

### Step 7 — A human says yes or no
`frontend/src/pages/Approvals.tsx` → `src/outreach/execute.py`

You see the person, why they were picked, the draft, and its quality warnings. You approve, edit, or reject.

If you **edit** the text, it goes back through the quality filter — because a human typing a booking link into a connection note is just as much a problem as an AI doing it.

If you **reject**, you can tick "never contact again", which suppresses that person forever.

### Step 8 — It waits for a natural moment
`src/outreach/pacing.py`

Approval doesn't mean "send now". The app picks a send time:

- Only inside your working hours, in your timezone
- Weekends reduced but **not zero** — because being active exactly Monday–Friday 9–5 every single week is itself a robot signature
- A random 45-second to 15-minute wobble on every send, so gaps never form a pattern
- A minimum gap between consecutive sends

The file states the principle plainly: *twenty invitations spread across a Tuesday afternoon is a person; the same twenty fired in ninety seconds at 4am is software — even if both stayed under the daily limit.*

### Step 9 — Final checks at the moment of sending
`src/outreach/execute.py`

This is the only file that actually tells LinkedIn to do something, and it **re-checks everything** rather than trusting that earlier steps got it right:

- Is it genuinely approved and due?
- Does the text still pass the quality filter?
- Is the account still allowed to do this action at all? (see warm-up, below)
- Is it inside working hours? *(If not: reschedule, don't fail.)*
- Is there capacity left under the global limit?

The comment explaining why is the design philosophy in one line: **"A missed send is recoverable; an action that shouldn't have been sent is not."**

### Step 10 — The counter that actually works
`src/infrastructure/rate_policy.py`

Limits are stored in Redis, not in the app's memory. The file explains why the old approach was broken: with several copies of the app running, each kept its own private count, so "150 per day" secretly became 150 × number-of-copies, and reset every restart.

Now all copies share one counter per account. Three windows are checked together — per hour, per day, and **per rolling week** (LinkedIn's real invitation limit is weekly, so an account can stay under its daily limit every single day and still get restricted by Friday).

One detail that matters: a slot is only used up when the action is **allowed**. Being refused never burns your allowance.

### Step 11 — The message reaches LinkedIn
`src/infrastructure/transports/`

Two ways to do it:

- **Primary: the "mobile" route.** It calls LinkedIn's own internal, undocumented API (Voyager) — the same one their real app uses — disguised as a genuine mobile client. Fast, low risk.
- **Fallback: a real browser.** Playwright drives an actual Chrome window and clicks buttons. Slower and riskier, but works when the first route breaks.

A router in `api_client.py` tries the first, and silently falls back to the second if it fails. The file is refreshingly honest that Voyager is unofficial and changes without warning — so a LinkedIn change slows the product down instead of taking it offline.

---

## The two things that make this more than a script

### The warm-up programme
`src/warmup/program.py`

A brand-new LinkedIn account is the most fragile thing in the system. The single biggest trigger for a ban is a quiet account that suddenly starts sending invitations.

So every new account walks a fixed path over roughly three weeks:

```
observe → react → converse → publish → connect → full
  2d       3d       4d         5d        7d
```

- **Observe** — just signs in and reads the feed. A couple of likes. Some days nothing at all.
- **React** — likes and follows people in your space.
- **Converse** — starts writing real comments.
- **Publish** — posts its own content occasionally.
- **Connect** — first few invitations, small volume.
- **Full** — normal outreach.

Two things make this more than a delay timer:

**Each stage lists which actions are *possible*, not just how many.** During "observe", an invitation isn't rate-limited — it's *impossible*. No code path can produce one.

**Moving up requires time AND results.** An account that's been running two weeks but only gets 8% of its invitations accepted doesn't advance — it moves **backwards** a stage. And if LinkedIn ever shows a verification challenge, the account steps back immediately regardless of how good every other number looks.

Daily volumes are ranges with a *probability*, not fixed numbers — because doing exactly 12 likes every single day is as obviously robotic as doing 500.

### Listening, not just sending
`src/outreach/sync.py`

Every other part of the system decides what to *send*. This one file listens — and it's what makes the whole thing safe.

It regularly checks LinkedIn for two things:

- **Who accepted your invitation** → unlocks follow-up messages
- **Who replied** → **stops everything immediately**

That second rule is treated as sacred. The moment someone replies, every queued and pending message to that person is cancelled. The reasoning in `sequences.py`: an automated follow-up landing after a real person already answered is the clearest possible sign they were talking to software, and it costs you the meeting the whole sequence existed to book.

The follow-up sequence is deliberately short — invite, then three messages after acceptance, then **stop**. Sequences that run six or seven messages into silence are how a brand gets a reputation.

And booking links? Blocked in every automated message. Allowed *only* after the person has replied and shown interest — because the same link is spam before a reply and exactly what they wanted after one.

---

## One thing you should know about this repo

There are effectively **two generations of code** here, and it's worth not being confused by it:

**The older layer** — `main.py`, `README.md`, `src/agents/`, `src/infrastructure/orchestrator.py`. This describes a grand "multi-agent" system with eight autonomous workers, WhatsApp monitoring, Kubernetes scaling, and Prometheus dashboards. Some of it is real code (the interaction and content-analysis agents are ~1000 lines each), but several agents are **empty placeholders** — `scheduler_agent.py` is 21 lines and says so in its own docstring: *"Phase 0 ships a booting skeleton."*

**The newer layer** — `src/api/`, `src/accounts/`, `src/targeting/`, `src/outreach/`, `src/warmup/`, and the React frontend. This is the real, working, carefully-built product, and it's where all the thinking described above lives.

One practical consequence: **nothing runs on its own yet.** Generating suggestions, sending due messages, and syncing replies all happen when the API is asked to do them (`POST /api/v1/outreach/.../run-due`, etc.). The background timer that would fire these automatically is the piece the agent skeletons are placeholders for. `docs/BACKEND_HANDOFF.md:492` confirms this is known and planned.

---

## Running it

```bash
pip install -r requirements.txt
docker-compose up -d          # starts Postgres + Redis
uvicorn src.api.main:app --reload
cd frontend && npm install && npm run dev
```

Health check: `GET /healthz`. It's unusually honest — it reports not just "am I alive" but what the app can currently *do*: whether Redis is up, whether an encryption key exists, whether AI writing is available, and critically **whether sending is enabled at all** (it refuses to send without Redis, because limits can't be enforced globally without it).

Tests: `pytest` — 14 test files covering scoring, quality, rate limits, sequences, and warm-up.

---

## The one idea to take away

Read the file docstrings — this codebase explains its own reasoning better than most. But if you only remember one thing:

**Every feature in this app is a brake, not an accelerator.** Scoring drops people. Quality blocks messages. Warm-up forbids actions. Pacing delays sends. Rate limits refuse. Reply-sync cancels everything. The app's actual product isn't "send lots of LinkedIn messages" — anyone can write that in fifty lines. It's *"send few enough, slowly enough, and personally enough that neither LinkedIn nor the recipient can tell software was involved."*
