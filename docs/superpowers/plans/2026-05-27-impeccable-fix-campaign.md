# Impeccable Fix Campaign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remediate the impeccable critique sweep's pooled findings (13 globals + every unit's P0–P3 locals) in a prioritized, branch-per-phase campaign that raises the Nielsen scores without re-introducing AI-slop tells.

**Architecture:** A re-baseline Setup step, then five ordered phases — (1) logic & route correctness [code/TDD], (2) global shell & token foundation [`style.css`/`base.html`], (3) core-loop pages, (4) lighter public, (5) admin cluster. Phases 1 and 2 may run in parallel (disjoint files); Phase 2 must merge before 3–5. Each phase is its own branch + PR tagged `@coderabbitai review`, verified by re-running `impeccable critique` on the changed pages.

**Tech Stack:** Flask + Jinja2 + Bootstrap 5 (server-rendered), SQLite, pytest, `npx impeccable detect` (Node v24), the `.critique_shots/harness.py` authenticated render harness, chrome-devtools MCP for visual verification.

**Spec:** `docs/superpowers/specs/2026-05-27-impeccable-fix-campaign-design.md`
**Findings source of truth:** `docs/design/critique-sweep-findings.md` → "Deferred prioritization & fix campaign" (master table maps every issue → phase + command).

---

## Plan structure (read first)

This campaign spans 5 PRs and ~50 issues. Following this repo's own plan convention (the sweep plan fully detailed Session A and parameterized the rest), this plan **fully details the Setup step and Phase 1's three P0s** (the code work, where TDD detail and the trust-breaking bugs live), then presents **Phases 2–5 as parameterized roadmap rows**. Each roadmap row carries its branch, pages, findings, commands, and verification; it is expanded into full bite-sized tasks at the start of that phase's branch (the CSS edits depend on live `impeccable`-command rendering, so specifying exact diffs now would be guessing). Phase 1's logic locals beyond the P0s are listed as task stubs with file + fix + test-intent, detailed at Phase-1 kickoff.

**File-structure decisions locked here:**
- Phase 1 adds an authenticated `client` fixture to `tests/conftest.py` (reused by all route/template tests).
- Phase 1 touches `app.py` (register + override routes), `templates/tournament_detail.html`, `templates/register.html`, `templates/admin/override_pick.html`, `templates/make_pick.html`, plus their tests.
- Phase 2 is confined to `static/css/style.css` + `templates/base.html` (+ the shared inline snippets it tokenizes).
- Phases 3–5 touch only their named templates (and `static/css/style.css` for any page-specific rule).
- Setup adds/maintains `.critique_shots/harness.py` (ephemeral tooling, gitignored or kept under `.critique_shots/`).

---

## Execution strategy (per phase) — read at the start of every session

This campaign is executed **one phase (or a natural grouping of phases) per session, with a `/clear` between sessions**, NOT as a single blanket subagent-driven or inline run. Each phase is assigned the execution strategy that fits the work; a cleared session re-orients by reading this section, then expands that phase's roadmap row into bite-sized tasks and executes with the assigned strategy. Phase boundaries are natural break points: each ends in a PR + a re-critique verification gate, and the Phase-2-before-3–5 merge dependency is enforced by doing one PR per session.

| Session | Phase(s) | Execution strategy | Rationale |
|---|---|---|---|
| **S1** | Setup + Phase 1 (logic) | Setup **inline**; Phase 1 **subagent-driven** (`superpowers:subagent-driven-development`) | Setup is tooling you adapt to live output. Phase 1 is the textbook subagent fit — discrete TDD tasks, binary pass/fail, file-disjoint — and the review-between-tasks step is where `pick-resolution-audit` guards the U4/U9 money logic. Both are non-visual code; pair them. |
| **S2** | Phase 2 (global tokens) | **Inline** (`superpowers:executing-plans`) | Highest-coupling, highest-blast-radius work — contrast tokens, focus ring, gold contrast, penalty component, money treatment all interact. One operator holding the token system in context beats farmed-out edits; the `/audit`→`/colorize`→`/typeset` passes are interactive in-browser. Own focused session; **merge before S3–S5.** |
| **S3** | Phase 3 (core loop) | **Inline**, with a small **subagent batch** for mechanical fixes | Bottleneck is design taste + 2-breakpoint visual verification (inline strength). Exception: pure template-binding fixes (U5 row-status class, live-row link, as-of timestamp) are a mechanical subagent batch up front. Split into two sessions (front doors / trust surfaces) if context grows. |
| **S4** | Phase 4 (lighter public) | **Inline**, light | Mostly applying S2's tokens + small locals; the auth trio shares one pattern so a single fix propagates. Small enough that inline is simpler than dispatching. |
| **S5** | Phase 5 (admin) | **Split**: subagent-driven for G12 migration, **inline** for G13 + U9 confirm UI | G12 is a well-specified mechanical class-swap (three templates → three verifiable subagent tasks). G13 + the confirm UI is interaction safety on a money-re-resolve flow — must be verified in-browser against Phase 1's logic gate, so it needs a careful inline eye. Likely 1–2 sessions. |

**Per-session ritual:** (1) read this section + the target phase's roadmap row; (2) cut the phase branch; (3) expand the row into bite-sized tasks; (4) execute with the assigned strategy; (5) run the phase's re-critique verification and record the score delta in the findings doc; (6) open the PR tagged `@coderabbitai review`; (7) `/clear` before the next session (merge S2 before starting S3).

---

## Setup: Re-baseline + harness false-positive filter

**Files:**
- Create/rebuild: `.critique_shots/harness.py`
- Read: `docs/design/critique-sweep-findings.md` (Tooling note — the harness snippet)

- [ ] **Step 1: Rebuild the authenticated render harness**

Recreate `.critique_shots/harness.py` from the findings-doc Tooling note: a Flask test client that injects an admin session (`sess['_user_id']='1'`, `WTF_CSRF_ENABLED=False` on the in-process client only), renders each gated template (it links the real `/static/css/style.css`), writes the HTML to a repo-root file under `.critique_shots/`, so `python -m http.server 8765` + `impeccable detect --json http://localhost:8765/<file>.html` renders the real gated DOM + real CSS. Non-mutating: GET + the non-saving `load_field` POST only.

- [ ] **Step 2: Add the signature-tight green-gradient false-positive filter**

In the harness's detector-JSON post-processing, drop a finding only when it matches BOTH a known-FP rule id AND a brand-green signature:

```python
GREEN_FP_COLORS = {"#00432e", "#005c3f"}  # --green-900 / --green-800
GREEN_FP_SELECTORS = ("nav", ".navbar", "footer", ".footer")

def is_green_gradient_fp(finding: dict) -> bool:
    rule = finding.get("rule", "")
    if rule not in ("ai-color-palette", "dark-glow"):
        return False
    blob = (finding.get("message", "") + finding.get("selector", "")).lower()
    color_hit = any(c in blob for c in GREEN_FP_COLORS)
    selector_hit = any(s in finding.get("selector", "").lower() for s in GREEN_FP_SELECTORS)
    return color_hit or selector_hit

# filtered = [f for f in findings if not is_green_gradient_fp(f)]
```

Never broaden to a bare `"cyan" in message` match — that would mask a genuinely-wrong cyan gradient added later (see findings-doc note + memory `feedback-brand-over-linter`).

- [ ] **Step 3: Re-baseline Units 3/5/7/10 through the harness**

Run the harness + `impeccable detect --json` on `make_pick`, `my_picks`, the auth trio, and the three admin tables. Record each page's deterministic detector finding count (post-filter) next to the existing Assessment-A Nielsen scores in the findings doc under a new "Re-baseline (Session F+)" subheading. This is the before-snapshot the per-phase verification compares against.

- [ ] **Step 4: Commit the harness + baseline**

```bash
git add .critique_shots/harness.py docs/design/critique-sweep-findings.md
git commit -m "chore(critique): rebuild auth harness + green-gradient FP filter; re-baseline gated units"
```

---

## Phase 1 — Logic & route correctness (branch `fix/phase1-logic-correctness`)

Code/logic only — NOT an impeccable pass. TDD throughout; invoke the `pick-resolution-audit` skill before and after the U4 and U9 tasks (they sit near earnings/resolution logic). May run in parallel with Phase 2 (disjoint files).

### Task 1.0: Add an authenticated test client fixture

**Files:**
- Modify: `tests/conftest.py`

- [ ] **Step 1: Add the fixture**

```python
@pytest.fixture
def client(app):
    app.config['WTF_CSRF_ENABLED'] = False
    return app.test_client()


@pytest.fixture
def login(client):
    def _login(user):
        with client.session_transaction() as sess:
            sess['_user_id'] = str(user.id)
        return client
    return _login
```

- [ ] **Step 2: Verify it imports**

Run: `python -m pytest tests/ -q --collect-only`
Expected: collection succeeds (no fixture errors).

- [ ] **Step 3: Commit**

```bash
git add tests/conftest.py
git commit -m "test: add authenticated client + login fixtures"
```

### Task 1.1 (P0): Desktop tournament_detail must render the live missed-cut penalty

**Bug:** `tournament_detail.html:287-289,310-312` gate the desktop penalty badge on `result.penalty_triggered and (result.active_is_primary or result.active_is_backup)`; on un-finalized live majors `active_player_id` is null, so both flags are false and the badge never renders on desktop — while the mobile card (`:211`) and the desktop legend both show it. Trust-surface failure: a $15 debt the legend advertises is silently hidden.

**Files:**
- Test: `tests/test_tournament_detail_penalty.py`
- Modify: `templates/tournament_detail.html:287-289,310-312`

- [ ] **Step 1: Write the failing test**

```python
def test_desktop_table_shows_live_penalty_badge(login, make_user, make_player,
                                                 make_tournament, make_result, make_pick):
    admin = make_user(username='admin', is_admin=True)
    p_cut = make_player(first_name='Sam', last_name='Stevens')
    backup = make_player(first_name='Denny', last_name='McCarthy')
    major = make_tournament(name='U.S. Open', is_major=True, status='active', purse=0)
    # live, un-finalized: the pick's active_player_id stays null
    make_result(major, p_cut, status='cut', earnings=0, rounds_completed=2)
    make_pick(make_user(username='member'), major, primary=p_cut, backup=backup,
              penalty_triggered=True)

    resp = login(admin).get(f'/tournament/{major.id}')
    html = resp.get_data(as_text=True)
    desktop = html.split('mobile-card-list')[0]  # the desktop table precedes mobile cards
    assert 'badge-penalty' in desktop, 'desktop table must render the live penalty badge'
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python -m pytest tests/test_tournament_detail_penalty.py -v`
Expected: FAIL — `badge-penalty` absent from the desktop slice (current gate suppresses it).

- [ ] **Step 3: Fix the template gate**

In `templates/tournament_detail.html` at the two desktop penalty conditionals (`:287-289` and `:310-312`), change the gate from
`{% if result.penalty_triggered and (result.active_is_primary or result.active_is_backup) %}`
to `{% if result.penalty_triggered %}` — matching the mobile gate at `:211`. Do not touch the resolve/earnings logic; this is display only.

- [ ] **Step 4: Run it to verify it passes**

Run: `python -m pytest tests/test_tournament_detail_penalty.py -v`
Expected: PASS.

- [ ] **Step 5: pick-resolution-audit + commit**

Invoke the `pick-resolution-audit` skill to confirm the display change does not alter penalty/earnings logic. Then:

```bash
git add tests/test_tournament_detail_penalty.py templates/tournament_detail.html
git commit -m "fix(tournament_detail): render live missed-cut penalty on desktop table (U4 P0)"
```

### Task 1.2 (P0): Register must repopulate fields on a validation error

**Bug:** the `app.py` register route re-renders `register.html` on error with no context, wiping username/email/display name. Highest-likelihood abandonment trigger.

**Files:**
- Test: `tests/test_register_repopulation.py`
- Modify: `app.py` (register route error branch), `templates/register.html`

- [ ] **Step 1: Write the failing test**

```python
def test_register_error_repopulates_nonpassword_fields(client):
    resp = client.post('/register', data={
        'username': 'jordan_new',
        'email': 'jordan@example.test',
        'display_name': 'Jordan',
        'password': 'secret1',
        'confirm_password': 'MISMATCH',
    }, follow_redirects=True)
    html = resp.get_data(as_text=True)
    assert 'jordan_new' in html, 'username must survive a validation error'
    assert 'jordan@example.test' in html
    assert 'Jordan' in html
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python -m pytest tests/test_register_repopulation.py -v`
Expected: FAIL — submitted values absent from the re-rendered form.

- [ ] **Step 3: Fix the route + template**

In the register route's error branch, pass the submitted values into `render_template('register.html', username=..., email=..., display_name=...)`. In `templates/register.html`, set each non-password input's `value="{{ username|default('') }}"` (and email/display_name). Never repopulate password fields.

- [ ] **Step 4: Run it to verify it passes**

Run: `python -m pytest tests/test_register_repopulation.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_register_repopulation.py app.py templates/register.html
git commit -m "fix(register): repopulate non-password fields on validation error (U7 P0)"
```

### Task 1.3 (P0): Override-pick must gate a money-re-resolving commit (logic half of G13)

**Bug:** submitting an override on a `complete` tournament re-resolves the member's earnings/total/1.5×/penalty (`app.py:1010-1023,1041-1047`) with no confirmation or consequence summary. Phase 1 ships the **server-side gate + consequence computation**; the confirm UI lands in Phase 5.

**Files:**
- Test: `tests/test_override_confirmation_gate.py`
- Modify: `app.py` (override route)

- [ ] **Step 1: Write the failing test**

```python
def test_complete_tournament_override_requires_confirm(login, make_user, make_player,
                                                        make_tournament, make_result, make_pick):
    admin = make_user(username='admin', is_admin=True)
    member = make_user(username='member')
    old_p = make_player(first_name='Patrick', last_name='Cantlay')
    new_p = make_player(first_name='Xander', last_name='Schauffele')
    backup = make_player(first_name='Backup', last_name='Golfer')
    done = make_tournament(name='RBC Heritage', status='complete')
    make_result(done, new_p, status='complete', earnings=1_000_000)
    make_pick(member, done, primary=old_p, backup=backup)

    c = login(admin)
    # Without confirm: must NOT mutate; must return the consequence summary
    resp = c.post('/admin/override-pick', data={
        'tournament_id': done.id, 'user_id': member.id,
        'primary_player_id': new_p.id, 'backup_player_id': backup.id,
    })
    body = resp.get_data(as_text=True).lower()
    assert 'recalculat' in body or 'confirm' in body, 'must surface the re-resolve consequence'
    from models import Pick
    pick = Pick.query.filter_by(user_id=member.id, tournament_id=done.id).first()
    assert pick.primary_player_id == old_p.id, 'must not commit without confirm'
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python -m pytest tests/test_override_confirmation_gate.py -v`
Expected: FAIL — current route commits immediately, pick already changed.

- [ ] **Step 3: Implement the gate**

In the override route: when `selected_tournament.status == 'complete'` and the request lacks `confirm=1`, do NOT commit. Instead compute a consequence summary (the member's current total/earnings for that tournament → the projected new value) and re-render the form with that summary + a flag that Phase 5's UI will turn into an inline confirm. When `confirm=1` is present, commit as today. Keep the re-resolution math untouched — only gate and summarize it.

- [ ] **Step 4: Run it to verify it passes**

Run: `python -m pytest tests/test_override_confirmation_gate.py -v`
Expected: PASS.

- [ ] **Step 5: pick-resolution-audit + commit**

Invoke `pick-resolution-audit` (this guards `resolve_pick` re-fire). Then:

```bash
git add tests/test_override_confirmation_gate.py app.py
git commit -m "fix(override): gate complete-tournament re-resolve behind confirm + consequence (U9 P0 logic)"
```

### Tasks 1.4–1.8: Phase-1 logic locals (detail at kickoff)

Each is a code/logic fix with a test; expand to full TDD tasks (like 1.1–1.3) when Phase 1 starts. Files + fix + test-intent:

| Task | Source | File(s) | Fix | Test intent |
|---|---|---|---|---|
| 1.4 | U4 P1 ranking | `tournament_detail.html` | Rank only rows with a pick, by earnings (shared ties); push no-pick rows below a divider — never let `loop.index` double as rank. | Render a major with picked + no-pick rows; assert no-pick rows are not numbered in the paying sequence. |
| 1.5 | U3 P1 same-player | `make_pick.html` (JS, `:128-145`) | Filter the chosen primary out of the backup Tom Select options live; remove the `alert()` + field-wipe. | JS/integration: selecting a primary removes it from backup options; no `alert`. |
| 1.6 | U9 P1 same-player + USED | `override_pick.html` (`:76,:95,:215-233`) | Add `disabled` to USED options; dynamically disable the backup option matching the primary; inline validation instead of `alert()`-wipe. | Assert USED `<option>`s carry `disabled`; backup==primary is not selectable. |
| 1.7 | U10 P2 reset-pw + toggle | `users.html`, `payments.html` (JS) | Generate a random default password (never `golf{id}`, never echo until generated); surface a failed payment toggle instead of the empty `else`. | Reset default is not `golf{id}`; failed toggle shows an error path. |
| 1.8 | U3 P2 search | `make_pick.html` (Tom Select config) | Normalize search (strip periods; nickname/first-name matching via `searchField`/score) so `jj` matches `J.J.`. | Typing `jj` returns the punctuated-name player. |

- [ ] **Final Phase-1 step: open the PR**

```bash
git push -u origin fix/phase1-logic-correctness
gh pr create --title "Fix campaign Phase 1: logic & route correctness (P0s)" --body "$(cat <<'BODY'
## Summary
- U4 P0: desktop tournament_detail now renders the live missed-cut penalty
- U7 P0: register repopulates non-password fields on validation error
- U9 P0: complete-tournament override gated behind confirm + consequence (logic; UI in Phase 5)
- Logic locals: ranking, same-player guards, reset-pw default, toggle failure, search normalization

## Test plan
- [ ] `python -m pytest tests/ -v` green
- [ ] pick-resolution-audit clean on U4 + U9 changes

@coderabbitai review
BODY
)"
```

---

## Phases 2–5 — roadmap (expand each into full tasks at its branch kickoff)

Each phase: cut its branch, expand the findings into bite-sized `impeccable`-command + edit + verify tasks, fix P0→P3, re-critique the changed pages, open a PR tagged `@coderabbitai review`. The findings-doc master table is the per-issue source of truth.

| Phase | Branch | Pages / files | Findings (from master table) | Primary commands | Verification |
|---|---|---|---|---|---|
| **2 — Global tokens** | `fix/phase2-global-tokens` | `static/css/style.css`, `templates/base.html` | G1 contrast, G2 focus ring, G3 skip-link/landmarks, G4 active-nav, G5 heading discipline, G6 penalty reframe, G8 est-purse chip token, G9 44px floor, G10 flash role + field-error scaffold, G11 money treatment, U1 mobile points total | `/audit`, `/polish`, `/harden`, `/typeset`, `/colorize`, `/adapt` | Re-critique a representative core-loop page (e.g. `index`) to confirm tokens propagate AND no regression on an already-good surface. **Must merge before Phases 3–5.** |
| **3 — Core loop** | `fix/phase3-core-loop` | `index.html`, `make_pick.html`, `tournament_detail.html`, `my_picks.html` (+ page CSS) | G7 mobile money pill (per-surface); U2 legend/timestamp/backup-text/next-pick CTA; U4 mobile gold pill, collapse no-pick rows, multiplier-alert contrast; U5 row-status binding, live-row link, legend money-code, mobile CTA height; U3 used-player cue, inline submit confirm, mobile rules | `/adapt`, `/harden`, `/clarify`, `/layout`, `/distill`, `/onboard`, `/audit` | Re-`critique` each of the 4 pages; confirm Nielsen `/40` moved up vs the unit's recorded score; record deltas. |
| **4 — Lighter public** | `fix/phase4-lighter-public` | `schedule.html`, `login.html`, `register.html`, `change_password.html`, `errors/404.html`, `errors/500.html` | U6 est-chip (G8 apply), current-week anchor, label parity, 500 recovery, error lead contrast (G1 apply); U7 Forgot-pw modal→inline, autocomplete, `.auth-card` float + `<h1>` | `/polish`, `/audit`, `/layout`, `/clarify`, `/harden`, `/distill` | Re-`critique` schedule + auth trio + both error pages; confirm scores moved; auth-trio uses the harness for a deterministic detector signal. |
| **5 — Admin cluster** | `fix/phase5-admin` | `admin/dashboard.html`, `admin/override_pick.html`, `admin/tournaments.html`, `admin/users.html`, `admin/payments.html` (+ admin CSS) | G12 design-system migration (class swap + add `.mobile-card-list`); G13 mutation-safety pattern incl. **U9 P0 confirm UI**; G11 gold money; U8 Process-Results guard, mobile cards, jargon; U9 chrome, existing-pick context, status cue; U10 `.table-greenside`, badge/toggle re-key, mobile fallback, hero-metric strip removal, 19 modals → 1 dialog | `/colorize`, `/polish`, `/harden`, `/typeset`, `/adapt`, `/distill`, `/audit` | Re-`critique` all five admin pages **through the harness** (anonymous detector redirects); confirm the cluster's 19–21/40 scores rise; verify G13 confirm flow manually in-browser (chrome-devtools MCP). |

**Per-phase task-expansion rule (applies to every phase 2–5):** for each finding in the row, create tasks of the shape — (a) run the suggested `impeccable` command on the target to get the concrete edit, (b) apply the edit, (c) verify in-browser at desktop + 390px via chrome-devtools MCP, (d) commit. Group commits by finding. End the phase by re-running `impeccable critique` per the Verification column and recording the score delta in the findings doc, then open the PR.

---

## Self-Review

- **Spec coverage:** Setup re-baseline + FP filter ✓ (spec Setup); Phase 1 logic/route incl. 3 P0s ✓ (spec Phase 1, decision 1); Phase 2 globals ✓; Phases 3–5 ✓ (spec phases); branching + parallelism + Phase-2-before-3–5 ✓ (spec workflow); per-phase re-critique verification ✓ (spec workflow); green-gradient tooling-layer filter, brand untouched ✓ (spec decision 4 + Setup); admin one-phase G12+G13 ✓ (spec decision 2, Phase 5); pick-resolution-audit on U4/U9 ✓ (spec risks). Every spec section maps to a task or roadmap row.
- **Placeholder scan:** the detailed tasks (Setup, 1.0–1.3) carry real code, exact file/line targets, and expected output. Roadmap rows for Phases 2–5 and Tasks 1.4–1.8 are *intentional parameterization* (per this repo's sweep-plan convention), each with explicit pages/files/findings/commands/verification — not vague "TODO"s; they are expanded at each branch's kickoff because the CSS edits depend on live command rendering.
- **Type/parameter consistency:** the `client`/`login` fixtures (Task 1.0) are used consistently in 1.1–1.3; the harness file path (`.critique_shots/harness.py`), port (`8765`), branch names, and the findings-doc master table are referenced identically throughout.
