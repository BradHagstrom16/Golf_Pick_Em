# Impeccable Critique Sweep Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run an impeccable `critique` on every HTML page in Golf Pick 'Em as a deferred-fix diagnostic sweep, pooling all findings into one living doc that hands off to a separate fix campaign.

**Architecture:** Each of 10 critique units follows the impeccable critique workflow: an isolated LLM design-review sub-agent (Assessment A) plus a parent-run deterministic detector + browser overlay (Assessment B), synthesized into a combined report appended to `docs/design/critique-sweep-findings.md`. Pages render in the live Flask dev app, viewed through a logged-in Chrome session driven by the chrome-devtools MCP. The dev SQLite DB is a **disposable playground** (cleared before the sweep): seed whatever state a unit needs — an in-progress tournament with live/projected earnings, a major mid-round to show the 1.5× multiplier and missed-cut penalty live, the admin user with a submitted pick, another user with none — rather than depending on fixed rows or building harnesses. Per-unit interactive Q&A is deferred; prioritization happens once at consolidation.

**Tech Stack:** Flask + Jinja2 + Bootstrap 5 (server-rendered), SQLite dev DB, `npx impeccable` CLI (Node v24), chrome-devtools MCP for browser automation, Claude `Agent` tool for assessment isolation.

**Scope of THIS plan:** Task 1 (setup), Task 2 (the reusable Unit Critique Procedure, defined once), and Tasks 3–4 (Unit 1 Shell + Unit 2 Home) — i.e. **Session A** of the spec, fully detailed. Validating the mechanic on 2 units before committing the rest. Units 3–10 are listed as parameterized instantiations in the "Remaining Units" roadmap at the end; each subsequent session reuses Task 2's procedure with the unit's parameter row.

**Spec:** `docs/superpowers/specs/2026-05-26-impeccable-critique-sweep-design.md`

---

## File Structure

This sweep writes NO production code. Files touched:

- **Create:** `docs/design/critique-sweep-findings.md` — the living findings doc (status checklist, scorecard matrix, global-issues list, per-unit reports, deferred prioritization). One responsibility: accumulate critique output across sessions.
- **Read-only (never modified during the sweep):** all `templates/**/*.html`, `static/css/style.css`, `PRODUCT.md`, `DESIGN.md`.
- **Disposable playground DB** (`golf_pickem.db`): seed/mutate freely via `flask shell` + the `models.py` models to produce any state a unit needs. Cleared before the sweep, so capture the ids you seed and use those (do NOT assume prior ids like 18/20). Harnesses are now a last resort only if a state genuinely can't be seeded.

---

## Task 1: Environment setup

**Files:**
- Create: `docs/design/critique-sweep-findings.md`

- [ ] **Step 1: Start the dev server on port 5001 (background)**

Run (from repo root, `/Users/bhagstrom/Golf_Pick_Em`):
```bash
FLASK_ENV=development flask run --port 5001
```
Run this in the background. Expected: server boots, "Running on http://127.0.0.1:5001". (Port 5001 avoids the macOS AirPlay conflict on 5000.)

- [ ] **Step 2: Bootstrap the cleared playground DB**

The DB is cleared before the sweep, so build it up. First ensure the schema (`flask db upgrade`). Then read `models.py` for exact field names before seeding, and via `flask shell` create:
- an **admin user** with known creds: username `Sun Day Regrets`, password `CritiqueSweep!2026`, `is_admin=True` (use `u.set_password(...)`);
- a **second non-admin user** (to populate standings and an "unsubmitted pick" state);
- enough **tournaments** to cover the sweep's render targets: at least one `complete` (with finalized `TournamentResult` rows + earnings), one `upcoming` with picks open (drives `make_pick`), and one `active`/in-progress — make this one a **major** (Masters/PGA/US Open/The Open) mid-round with a live leaderboard so `tournament_detail` and `index` show projected earnings, the 1.5× multiplier, and the live missed-cut penalty;
- **picks**: the admin user with a submitted pick on the in-progress tournament, the second user with none.

Capture the seeded tournament/user ids and record them at the top of the findings doc (the roadmap's example ids 18/20 are gone). Sweep credentials: `Sun Day Regrets` / `CritiqueSweep!2026`.

- [ ] **Step 3: Warm the impeccable CLI**

Run:
```bash
npx impeccable --help
```
Expected: usage text (downloads the package on first run; node v24 is present). If it prints command help, the detector is reachable.

- [ ] **Step 4: Open Chrome and log in (once) via chrome-devtools MCP**

Actions (chrome-devtools MCP):
1. `new_page` → navigate to `http://127.0.0.1:5001/login`
2. `fill` the `#username` input with `Sun Day Regrets`
3. `fill` the `#password` input with `CritiqueSweep!2026`
4. `click` the submit button
5. `navigate_page` to `http://127.0.0.1:5001/admin` and confirm it loads (admin route = proof of authenticated admin session).

Expected: `/admin` renders without redirecting to `/login`. This browser instance now holds the session cookie; every tab opened later (parent's `[Human]` tab, the sub-agent's `[LLM]` tab) shares it. If a later tab lands on `/login`, re-run steps 1–4 in that tab.

- [ ] **Step 5: Create the findings-doc skeleton**

Create `docs/design/critique-sweep-findings.md` with exactly:
```markdown
# Impeccable Critique Sweep — Findings

Living doc, updated at the end of each unit. Spec: `docs/superpowers/specs/2026-05-26-impeccable-critique-sweep-design.md`. Plan: `docs/superpowers/plans/2026-05-26-impeccable-critique-sweep.md`.

## Status

- [ ] 1. Shell (base.html)
- [ ] 2. Home (index.html)
- [ ] 3. Make a pick (make_pick.html)
- [ ] 4. Tournament detail (tournament_detail.html)
- [ ] 5. My picks (my_picks.html)
- [ ] 6. Lighter public (schedule.html, errors/404, errors/500)
- [ ] 7. Auth trio (login, register, change_password)
- [ ] 8. Admin dashboard (admin/dashboard.html)
- [ ] 9. Admin override-pick (admin/override_pick.html)
- [ ] 10. Admin tables (admin/tournaments, users, payments)

## Scorecard matrix

| Unit | Page | Nielsen /40 | AI-slop verdict | P0 count |
|------|------|-------------|-----------------|----------|

## Global issues (recur across pages → fix-campaign Phase 1)

_None recorded yet._

## Per-unit reports

## Deferred prioritization & fix campaign

_Filled at consolidation (Session F)._
```

- [ ] **Step 6: Verify setup**

Run:
```bash
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:5001/login
test -f docs/design/critique-sweep-findings.md && echo "doc exists"
```
Expected: `200` then `doc exists`. Confirm via chrome-devtools that `/admin` is reachable while logged in.

- [ ] **Step 7: Commit the skeleton**

```bash
git add docs/design/critique-sweep-findings.md
git commit -m "docs: add critique-sweep findings doc skeleton"
```

---

## Task 2: The Unit Critique Procedure (reference — every unit follows this)

This is the parameterized procedure each unit instantiates. Tasks 3–4 fill it in with concrete values; Units 5–10 (roadmap) reuse it identically. Parameters per unit: **PAGES** (template files), **URL** (route to render), **SCOPE** (what this critique focuses on), **PERSONAS** (2–3 to walk through), **SLUG** (findings-doc heading).

**Procedure steps:**

1. **Render check (parent):** `navigate_page` to **URL** in the existing logged-in tab; confirm it renders. Note any state the dev data can't show; only then build a throwaway harness for that state.

2. **Assessment A — isolated LLM design review (sub-agent):** Dispatch a `general-purpose` sub-agent. It must NOT run the impeccable detector or see Assessment B. Its prompt instructs it to:
   - Read for brand context: `PRODUCT.md`, `DESIGN.md`.
   - Read impeccable references: `~/.claude/skills/impeccable/reference/heuristics-scoring.md`, `~/.claude/skills/impeccable/reference/cognitive-load.md`, `~/.claude/skills/impeccable/reference/personas.md`, and the parent skill's anti-pattern/DON'T list at `~/.claude/skills/impeccable/SKILL.md`.
   - Read the unit's **PAGES** templates + `static/css/style.css`.
   - Open its OWN new Chrome tab (`new_page`), navigate to **URL**, run `document.title = '[LLM] ' + document.title` via `evaluate_script`. If redirected to `/login`, log in (`Sun Day Regrets` / `CritiqueSweep!2026`) then re-navigate.
   - Evaluate within **SCOPE**: AI-slop verdict; Nielsen's 10 heuristics scored 0–4 each with key issue; cognitive-load 8-item checklist (report failure count + band); emotional journey (peak-end, anxiety valleys); 2–3 what's-working; 3–5 priority issues (what / why / fix, each P0–P3); persona red flags for **PERSONAS**; minor observations; provocative questions.
   - Return structured markdown only. Do NOT write any file.

3. **Assessment B — deterministic detection (parent):** _(CLI reality, corrected in Session A — the installed `impeccable` has no `--json <file>` form and no `live` overlay server; `/live` is an AI-harness slash command, not a CLI.)_
   - **Primary — live-URL render:** `npx impeccable detect --json <URL>` (Puppeteer renders real linked CSS). **JSON is written to stderr; exit code 2 = findings, 0 = clean.** Capture with `> out.raw 2>&1` then slice from the first `[`. NOTE: the URL render is **anonymous** — for `@login_required` / `@admin` routes it hits the login redirect, so for those pages fall back to (a) scanning the rendered HTML another way and (b) a logged-in `[Human]`-tab screenshot for the visual; public routes (`/`, `/schedule`, `/login`, `/register`, `/tournament/<id>`) render fully.
   - **Secondary — file scan:** `npx impeccable detect --json templates/<file>` is weak for these templates (jsdom can't resolve the Jinja `{{ url_for }}` stylesheet link → usually returns `[]`); run it only as a cross-check, don't rely on it.
   - **Visual (replaces the nonexistent overlay):** in a NEW tab `navigate_page` to **URL** (shares the logged-in session), `document.title = '[Human] ' + document.title`, `take_screenshot` (and a phone-width `resize_page` + screenshot where mobile matters). Read findings off the detector JSON, not a console overlay.
   - Note false positives (Jinja artifacts; the intentional `.column-divider` `border-left`; the brand **green** gradient that the detector misreads as a "Cyan gradient").
   - No server to stop (no `live` process).

4. **Synthesize combined report (parent):** Merge A + B into the standard critique report — Nielsen scorecard table `/40`; Anti-Patterns verdict (LLM + detector + overlay summary); Overall impression; What's working; Priority issues (P0–P3, each with a **suggested impeccable command**); Persona red flags; Minor observations; Questions. Tag each priority issue **[global]** (recurs / traces to shell/tokens/CSS) or **[local]**.

5. **Append to findings doc:** Add a `### Unit N — SLUG` section under "Per-unit reports" with the full report. Add a scorecard-matrix row per page. Promote any **[global]** issue into the "Global issues" section (dedup). Check the unit's box in "Status".

6. **Verify (parent):** `grep` the findings doc for the unit heading and confirm a new matrix row exists and the status box is checked.

7. **Commit:** `git add docs/design/critique-sweep-findings.md && git commit -m "docs(critique): Unit N — SLUG findings"`.

**Persona note:** impeccable's `personas.md` supplies generic personas (e.g. Alex the power user, Jordan the first-timer). Also generate 1–2 project personas from PRODUCT.md: the **casual friends-and-family member on a phone in sunlight mid-banter**, and the **single league admin settling payments/penalties**.

---

## Task 3: Unit 1 — Shell (base.html)

**Files:**
- Read: `templates/base.html`, `static/css/style.css`, `PRODUCT.md`, `DESIGN.md`
- Modify: `docs/design/critique-sweep-findings.md`

**Parameters:** PAGES = `base.html` · URL = `http://127.0.0.1:5001/` (authenticated home; the shell wraps it) · SCOPE = global chrome only (top nav, footer, brand lockup, global type scale, color tokens, button styles, link styles, focus states, mobile nav) — NOT the home page's content (that's Unit 2) · PERSONAS = Jordan (first-timer), casual-member-on-phone · SLUG = `Shell (base.html)`

- [ ] **Step 1: Render check**

`navigate_page` to `http://127.0.0.1:5001/` in the logged-in tab. Confirm nav + footer render. (Home is public, but view it authenticated so the real member nav shows.)

- [ ] **Step 2: Dispatch Assessment A sub-agent**

Dispatch a `general-purpose` agent with this prompt:
> You are Assessment A (LLM design review) in an impeccable `critique`. Work in isolation: do NOT run the impeccable CLI/detector and do NOT look for any detector output. First read `PRODUCT.md` and `DESIGN.md` (this app is "The Greenside Ledger" heritage-golf clubhouse, register=product). Read `~/.claude/skills/impeccable/SKILL.md` (anti-patterns/absolute bans), `~/.claude/skills/impeccable/reference/heuristics-scoring.md`, `~/.claude/skills/impeccable/reference/cognitive-load.md`, `~/.claude/skills/impeccable/reference/personas.md`. Then read `templates/base.html` and `static/css/style.css`. Using the chrome-devtools MCP, open a NEW tab (`new_page`), navigate to `http://127.0.0.1:5001/`, and run `document.title = '[LLM] ' + document.title` via evaluate_script. If you land on `/login`, log in with username `Sun Day Regrets` password `CritiqueSweep!2026`, then re-navigate. **Evaluate ONLY the global shell chrome: top navigation, footer, brand lockup, global typographic scale, color-token usage, button/link styles, focus/hover states, and mobile nav behavior — NOT the home page's body content.** Produce: (1) AI-slop verdict (does the chrome look AI-generated? check the absolute bans), (2) Nielsen's 10 heuristics scored 0–4 with a one-line key issue each, (3) cognitive-load 8-item checklist with failure count and band, (4) emotional journey for the chrome, (5) 2–3 things working, (6) 3–5 priority issues each as what/why/fix tagged P0–P3, (7) persona red flags for Jordan the first-timer and a casual friends-and-family member checking on a phone in sunlight, (8) minor observations, (9) provocative questions. Return structured markdown only. Do NOT write any file.

- [ ] **Step 3: Run Assessment B (detector + overlay)**

```bash
npx impeccable --json templates/base.html
```
Capture JSON. Then start the overlay and inject (per Task 2 step 3) at `http://127.0.0.1:5001/`, label the tab `[Human]`, read console for `impeccable` findings, then:
```bash
npx impeccable live stop
```
Note: `.column-divider` `border-left` is intentional/structural (per CLAUDE.md) — flag as a false positive if the detector reports it.

- [ ] **Step 4: Synthesize + append to findings doc**

Build the combined report (Task 2 step 4) scoped to the shell. Append as `### Unit 1 — Shell (base.html)` under "Per-unit reports", add a scorecard row `| 1 | base.html | ?/40 | <verdict> | <P0 count> |`, promote `[global]` issues, and check box 1 in Status.

- [ ] **Step 5: Verify**

```bash
grep -c "Unit 1 — Shell" docs/design/critique-sweep-findings.md
grep -c "| 1 | base.html |" docs/design/critique-sweep-findings.md
```
Expected: `1` and `1`.

- [ ] **Step 6: Commit**

```bash
git add docs/design/critique-sweep-findings.md
git commit -m "docs(critique): Unit 1 — Shell (base.html) findings"
```

---

## Task 4: Unit 2 — Home (index.html)

**Files:**
- Read: `templates/index.html`, `static/css/style.css`, `PRODUCT.md`, `DESIGN.md`
- Modify: `docs/design/critique-sweep-findings.md`

**Parameters:** PAGES = `index.html` · URL = `http://127.0.0.1:5001/` (authenticated) · SCOPE = home page body content only (standings table/leaderboard, this-week's-pick CTA, earnings display, deadline visibility, empty/loading states) — treat shell chrome as already covered by Unit 1 · PERSONAS = Alex (power user / dedicated follower), casual-member-on-phone · SLUG = `Home (index.html)`

- [ ] **Step 1: Render check**

`navigate_page` to `http://127.0.0.1:5001/` (logged in). Confirm standings + pick CTA render with real dev data.

- [ ] **Step 2: Dispatch Assessment A sub-agent**

Dispatch a `general-purpose` agent with this prompt:
> You are Assessment A (LLM design review) in an impeccable `critique`. Work in isolation: do NOT run the impeccable CLI/detector and do NOT look for detector output. Read `PRODUCT.md` and `DESIGN.md` ("The Greenside Ledger", register=product; key principles: points are real dollars shown like a ledger, glanceable-first on phones, two equal front doors). Read `~/.claude/skills/impeccable/SKILL.md`, `~/.claude/skills/impeccable/reference/heuristics-scoring.md`, `~/.claude/skills/impeccable/reference/cognitive-load.md`, `~/.claude/skills/impeccable/reference/personas.md`. Then read `templates/index.html` and `static/css/style.css`. Via chrome-devtools MCP, open a NEW tab (`new_page`), navigate to `http://127.0.0.1:5001/`, run `document.title = '[LLM] ' + document.title`. If on `/login`, log in (`Sun Day Regrets` / `CritiqueSweep!2026`) and re-navigate. **Evaluate ONLY the home page body content — standings/leaderboard, the "make this week's pick" CTA, earnings/dollar presentation, deadline visibility, rank glanceability, and empty/loading states. Assume the nav/footer shell is critiqued separately; do not score it.** Judge against the design principles: does the one number that matters (your rank / active pick / deadline) read in a single glance on a phone? Do earnings read like a ledger? Produce the full structured output: (1) AI-slop verdict, (2) Nielsen 10 heuristics 0–4 with key issue each, (3) cognitive-load 8-item checklist + failure count + band, (4) emotional journey (peak-end; any anxiety at the deadline moment?), (5) 2–3 things working, (6) 3–5 priority issues what/why/fix tagged P0–P3, (7) persona red flags for Alex the dedicated golf follower and a casual member on a phone in sunlight, (8) minor observations, (9) provocative questions. Return structured markdown only. Do NOT write any file.

- [ ] **Step 3: Run Assessment B (detector + overlay)**

```bash
npx impeccable --json templates/index.html
```
Capture JSON. Start overlay, inject at `http://127.0.0.1:5001/`, label tab `[Human]`, read console for `impeccable`, then `npx impeccable live stop`. Note Jinja-template artifacts as potential false positives.

- [ ] **Step 4: Synthesize + append to findings doc**

Build the combined report scoped to home content. Append as `### Unit 2 — Home (index.html)`, add scorecard row `| 2 | index.html | ?/40 | <verdict> | <P0 count> |`, promote `[global]` issues (dedup against Unit 1's), check box 2 in Status.

- [ ] **Step 5: Verify**

```bash
grep -c "Unit 2 — Home" docs/design/critique-sweep-findings.md
grep -c "| 2 | index.html |" docs/design/critique-sweep-findings.md
```
Expected: `1` and `1`.

- [ ] **Step 6: Commit**

```bash
git add docs/design/critique-sweep-findings.md
git commit -m "docs(critique): Unit 2 — Home (index.html) findings"
```

---

## Task 5: Session A checkpoint

- [ ] **Step 1: Review the mechanic**

Confirm before continuing to later sessions: (a) sub-agent `[LLM]` tab was authenticated and isolated; (b) `npx impeccable --json` and the overlay produced usable output; (c) the findings doc has 2 reports, 2 matrix rows, 2 checked boxes, and a populated Global-issues section. If any failed, fix the procedure in Task 2 before Session B.

- [ ] **Step 2: Stop the dev server and overlay**

Stop the backgrounded `flask run` and confirm no stray `npx impeccable live` server is running.

---

## Remaining Units (roadmap — subsequent sessions reuse Task 2)

Each row is a parameter set for the Task 2 procedure. URLs use the ids seeded in Task 1 step 2 (the DB is a playground — seed/adjust state per row as needed). Detail these into full tasks (like Tasks 3–4) at the start of each session.

| Unit | PAGES | URL | SCOPE focus | PERSONAS |
|---|---|---|---|---|
| 3 Make-pick | `make_pick.html` | `/pick/<upcoming-id>` (seed an upcoming tournament with picks open; seed some used players to show lockout) | Tom Select golfer dropdown, deadline clarity, used-player lockout display, primary/backup pick affordance, confirm/submit | casual-member-on-phone, Alex |
| 4 Tournament detail | `tournament_detail.html` | `/tournament/<major-id>` (seed a *major* in-progress or complete to exercise the 1.5× multiplier + missed-cut penalty + earnings ledger) | leaderboard table, earnings-as-ledger, status pills, major-multiplier & penalty visibility | Alex, casual-member-on-phone |
| 5 My-picks | `my_picks.html` | `/my-picks` (logged in) | season pick history, WD/backup/penalty state legibility, totals, "subtle rules → obvious state" | casual-member, Alex |
| 6 Lighter public | `schedule.html`, `errors/404.html`, `errors/500.html` | `/schedule`; for errors `/tournament/99999` (404) and a forced 500 or a harness | season schedule scanability + est-purse badge; error-page copy + recovery path (link home) | Jordan, casual-member |
| 7 Auth trio | `login.html`, `register.html`, `change_password.html` | `/login`, `/register`, `/change-password` (log out first for the first two) | form clarity, validation/error states, brand presence on entry, tap targets | Jordan, casual-member |
| 8 Admin dashboard | `admin/dashboard.html` | `/admin` | admin command-center IA, glanceable league state, clubhouse warmth (not cold gray panel) | league-admin |
| 9 Admin override-pick | `admin/override_pick.html` | `/admin/override-pick` | high-stakes form safety (anxiety valley), confirmation/undo, error prevention on WD/backup override | league-admin |
| 10 Admin tables | `admin/tournaments.html`, `admin/users.html`, `admin/payments.html` | `/admin/tournaments`, `/admin/users`, `/admin/payments` | table legibility, payment/penalty money-as-ledger, edit affordances, density vs warmth | league-admin |

**Session F (consolidation):** fill the findings doc's "Deferred prioritization & fix campaign" — run the deferred critique "Ask the User" prioritization once across all pooled issues, then produce the ordered impeccable-command fix sequence (shell/tokens → core loop → boilerplate). That fix campaign gets its own spec.

---

## Self-Review

- **Spec coverage:** workflow model (deferred-fix sweep) → Tasks defer Q&A + pool into doc ✓; render strategy (live logged-in dev app) → Task 1 steps 1,4 ✓; hybrid granularity / 10 units → Tasks 3–4 + roadmap ✓; two isolated assessments → Task 2 steps 2–3 ✓; findings doc structure → Task 1 step 5 ✓; pacing → Sessions A–F ✓; fix handoff → Session F note ✓.
- **Placeholder scan:** sub-agent prompts and CLI commands are written out in full for the two executed units; `?/40` and `<verdict>` in matrix rows are runtime outputs, not plan placeholders; roadmap rows are explicitly flagged as to-be-detailed per session.
- **Type/parameter consistency:** credentials (`Sun Day Regrets` / `CritiqueSweep!2026`), port (`5001`), tab labels (`[LLM]` / `[Human]`), and doc path (`docs/design/critique-sweep-findings.md`) are identical across all tasks. Tournament ids (18 major-complete, 20 upcoming) match the verified dev DB.
