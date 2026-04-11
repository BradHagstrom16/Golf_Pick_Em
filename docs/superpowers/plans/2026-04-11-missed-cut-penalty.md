# Missed-Cut-At-Major Penalty Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **⚠️ PROVISIONAL:** This plan contains unresolved design questions in the **Open Questions** section below. Do **not** execute until those are answered and the plan is revised. Task placeholders that depend on a question are tagged `[Q#]`.

**Goal:** Charge any user an extra $15 into the season pot when their active pick at a major tournament finishes with a `'cut'` or `'dq'` status. Surface the penalty in the standings, tournament detail, and my-picks pages in the existing "Greenside Ledger" visual language.

**Architecture:** Pure additive. One new boolean column on `Pick` (`penalty_triggered`), set during `Pick.resolve_pick()` when the active player's result at a major is `cut`/`dq`. One new integer column on `User` (`penalty_paid_cents` or equivalent) so the admin can track cash collected. Total owed is derived on demand by counting penalty-triggered picks × $15. No new routes, no JavaScript, no background jobs.

**Tech Stack:** Python, Flask, SQLAlchemy, Flask-Migrate (Alembic), SQLite, Jinja2, Bootstrap 5, pytest

---

## Confirmed Decisions (locked in)

1. **Rule trigger:** User's **active player** (the one whose `Pick.active_player_id` is set after resolution) at a major tournament (`Tournament.is_major == True`) finishes with `TournamentResult.status` in `('cut', 'dq')`. WDs do **not** trigger; they're already handled by backup activation.
2. **Amount:** $15 per occurrence. Hardcoded constant — no per-tournament variance. Must be one of the 4 Major tournaments.
3. **Retroactive:** Rule applies to **Masters 2026 and forward**. Everyone knew the rule before locking their Masters picks, so no grandfathering. Today is 2026-04-11; Masters finalizes Sunday/Monday, so this will trigger naturally via the existing results sync — **no backfill command needed**.
4. **Active == Used:** Confirmed during brainstorming that `active_player_id` and the `*_used` flags are equivalent in every branch of `resolve_pick()`. The plan uses `active_player_id` because that's the existing surface.
5. **Visual idiom:** A small red pill badge (`badge-penalty`) reading `+$15`, rendered next to the existing `badge-cut` / `badge-dq` badges on every pick display. No stamps, no animations, no new colors. Matches the existing refined ledger aesthetic.

---

## Open Questions

Please answer each of these in order. I've given my lean and the reasoning so you can reject fast.

### Q1. Tracking model — how do we store the penalty?

I originally listed three options, but after reading the models I want to pitch a fourth that's cleaner. All four:

- **A. Single `User.penalty_owed_cents` integer.** Admin updates manually. No link back to which pick triggered what.
- **B. New `PenaltyLedger` table** — one row per incident with `user_id`, `pick_id`, `tournament_id`, `amount`, `paid_at`. Most auditable.
- **C. `User.penalty_owed` + `User.penalty_paid`** — two integers, no per-incident granularity.
- **D. `Pick.penalty_triggered` boolean + `User.penalty_paid_cents` integer.** ← **my recommendation.** Owed is always `count(picks where penalty_triggered) * 1500` — never drifts, always matches reality. Paid is a single admin-managed tally. Supports partial payment (owes $45, paid $30, outstanding $15) without a new table.

**Why D:** the penalty is a deterministic consequence of a pick + result, so the source of truth should be on `Pick`, not a denormalized sum. `resolve_pick()` is already the one place that touches earnings math — adding one line there (`self.penalty_triggered = self.tournament.is_major and active_result.status in ('cut', 'dq')`) is the smallest correct change. Paid tracking is separate because payment is an out-of-band human action.

→ **Your answer: D**

### Q2. Does the penalty affect `total_points`?

- **A.** No. `total_points` stays pure "prize money earned" — standings are still sorted by earnings only. Penalty is displayed separately and doesn't move your rank. ← my lean.
- **B.** Yes. Subtract penalties from total points, so `total_points = sum(earnings) - sum(penalties)`. Missing a major cut actively drops your standings rank.

**Why A:** the penalty is a **side-pot mechanic**, not a scoring mechanic. The existing app literally tells users "Points = Prize Money Earned" in the footer and league rules. Conflating them changes the meaning of the leaderboard. The penalty is visible on the standings page in its own line — it doesn't need to distort the ranking to be felt.

→ **Your answer: A**

### Q3. Admin waiver capability — can the commissioner undo a penalty?

- **A.** No. Penalty is mechanical. Edge cases can be fixed by editing the DB directly. ← my lean.
- **B.** Yes — add a `penalty_waived` boolean + `waived_reason` string to `Pick`, toggleable from the admin override page. Waived penalties still show but with strikethrough.

**Why A:** the rule is simple and the league is small. If some pathological case arises (e.g., DQ for a reason the league thinks is fair to excuse), you can `UPDATE pick SET penalty_triggered=0 WHERE id=...` in a console. Adding waiver infrastructure is YAGNI.

→ **Your answer: A**

### Q4. Admin payment tracking UI — where does the admin mark penalties paid?

- **A.** Reuse the existing `admin/payments.html` page. Add a second column next to the existing "Paid" checkbox showing penalty owed/paid and a small input to update `User.penalty_paid_cents`. ← my lean.
- **B.** New dedicated `admin/penalties.html` page.
- **C.** Skip admin UI entirely — just show the tally, collect cash at season-end, and update via DB console.

**Why A:** everything about side-pot money lives on the payments page already. Putting penalty collection next to entry-fee collection means one place for the commissioner to look. New page is overkill for a single integer field.

→ **Your answer: A and read entire payments.html** *(I have not read `admin/payments.html` yet; I'll need to before finalizing this task. Flag if you want me to read it now.)*

### Q5. UI wording — what do we call it?

- **A.** "Penalty" throughout. Pill badge says `+$15`. Sidebar card header: "Penalty Pool". Stat card label: "Penalties Assessed". ← my lean.
- **B.** "Debit" / "Owes" — more ledger-flavored but less immediately readable.
- **C.** Custom copy you supply.

→ **Your answer: A**

### Q6. Prize Pool sidebar card — how should the new lines read?

Current card (on `index.html`):
> **Prize Pool**
> $25 entry fee × 11 players = **$275** pot

Proposed (my lean — option A below):
> **Prize Pool**
> Entry: $25 × 11 = $275
> Penalties: +$90
> **Total: $365**

Other options:
- **B.** Keep the card identical and add a new separate "Penalty Pool" sidebar card right below it.
- **C.** Merge into a single line: `$275 base + $90 penalties = $365`.

→ **Your answer: A**

### Q7. Standings — does the penalty get its own column on the desktop table?

Current desktop standings table has: Rank, Player, Total Points, [Season Score], [Tournament Pick], [Position], [Earned/Projected]. It's already dense.

- **A.** No new column. Penalty appears as a small red secondary line **under** the Total Points badge — same pattern as how `cumulative_scores` already renders under-par/over-par next to points. No horizontal space cost. ← my lean.
- **B.** New "Penalty" column between Total Points and Season Score. Cleaner separation but crowds the table.
- **C.** Show penalty as a small red icon next to the player name with a tooltip.

→ **Your answer: It should be like A, but only for current tournament and not season standings but ONLY when a major is ongoing or being displayed. Once the next tourney starts to display we can get rid of it. So since R3 is ongoing for the masters, those with missed cut picks will have it for R3 and R4 and then once the site flips to next tourney it can go away. Long answer, let me know if I should clarify anything for you**

### Q8. Exact badge visuals — confirm the `badge-penalty` spec

Proposed CSS:

```css
.badge-penalty {
  background-color: #fef2f2;           /* soft red tint, matches alert-danger bg */
  color: var(--danger);                /* #b91c1c — existing danger red */
  font-weight: 700;
  font-size: 0.7rem;
  padding: 0.3em 0.6em;
  border-radius: var(--radius-sm);
  border: 1px solid rgba(185, 28, 28, 0.3);
}
```

Reads as: light-red pill, dark-red "+$15" text, thin red border. Sits next to `badge-cut` (solid red fill, white text) — visually related but distinct. Matches the outlined-pill style of `badge-major` and `badge-unpaid`.

→ **Your answer: approve**

---

## Data Model Changes (assumes D + A + A answers above)

### New columns

**`pick.penalty_triggered`** — `Boolean`, default `False`, nullable=False.
- Set in `Pick.resolve_pick()` to `True` when `self.tournament.is_major` AND the **active player's** `TournamentResult.status` is in `('cut', 'dq')`. Otherwise `False`.
- Reset to `False` at the top of `resolve_pick()` on re-resolution (already how other fields work).

**`user.penalty_paid_cents`** — `Integer`, default `0`, nullable=False.
- Admin-managed only. No automatic writes.
- Stored in cents to avoid float issues (consistent with how money is generally handled; existing code uses integer dollars for `total_points` — **decision:** stay consistent and use `penalty_paid` as integer dollars, not cents. Single source-of-truth: integer dollars everywhere.)

**Final decision:** use `user.penalty_paid` (integer dollars), not cents. Matches existing codebase.

### Derived properties on `User`

```python
PENALTY_PER_INCIDENT = 15  # module-level constant, goes in models.py

def penalty_owed(self):
    """Total penalty amount this user has incurred this season (sum, not outstanding)."""
    from sqlalchemy import func as sqla_func
    count = db.session.query(sqla_func.count(Pick.id)).filter(
        Pick.user_id == self.id,
        Pick.penalty_triggered == True,
    ).join(Tournament).filter(
        Tournament.season_year == current_season_year(),  # see note
    ).scalar() or 0
    return count * PENALTY_PER_INCIDENT

def penalty_outstanding(self):
    """Amount still owed (owed - paid), clamped at zero."""
    return max(0, self.penalty_owed() - (self.penalty_paid or 0))
```

**Note on season scoping:** `current_season_year()` doesn't exist yet. The existing code reads `season_year` from config in various places (`SEASON_YEAR`). I'll pull it from `current_app.config['SEASON_YEAR']`. Confirmed convention by reading `config.py` during implementation.

### Migration

Single Alembic migration adding two columns. Both nullable-safe since they have defaults. Downgrade drops them. Will be generated with `flask db migrate -m "add missed-cut major penalty tracking"` and **must be reviewed with `migration-reviewer` agent** before `flask db upgrade` per CLAUDE.md.

---

## Pick Resolution Change (the core)

Exactly one spot in `models.py` needs a change: the bottom of `Pick.resolve_pick()`, after `active_player_id` and `points_earned` are set, **before** the `SeasonPlayerUsage` insert.

```python
# Determine if this pick triggers a major missed-cut/DQ penalty.
# active_player_id has been set in one of the branches above.
active_result = (
    primary_result if self.active_player_id == self.primary_player_id else backup_result
)
self.penalty_triggered = bool(
    self.tournament.is_major
    and active_result is not None
    and active_result.status in ('cut', 'dq')
)
```

**Edge cases handled:**
- Primary WD early → backup plays and misses cut → `active_result` is `backup_result`, status `cut`, penalty triggered ✓
- Primary plays, misses cut → `active_result` is `primary_result`, status `cut`, penalty triggered ✓
- Both WD early → `active_player_id == primary_player_id`, `active_result.status == 'wd'` → `'wd' not in ('cut', 'dq')` → **no penalty** ✓
- Non-major → `is_major == False` → no penalty regardless ✓
- Missing result rows (early-return cases in existing code) → we never reach this line because the function already returned → field keeps its default of `False` ✓

---

## Display Surfaces

Each surface is a small surgical edit to an existing template. All four templates use the same pattern: `{% if result.primary_result.status in ('cut', 'dq') and tournament.is_major %}<span class="badge-penalty">+$15</span>{% endif %}` — or for views that already have the resolved pick, `{% if pick.penalty_triggered %}<span class="badge-penalty">+$15</span>{% endif %}`.

### 1. `templates/index.html` — Season standings

**a. New `badge-penalty` pill** next to the user's tournament pick name (in both mobile card and desktop table), shown when `tournament_picks[user.id].penalty_triggered`. Requires adding `penalty_triggered` to the `tournament_picks` dict built in `app.py`'s index route.

**b. Small red secondary line** under the Total Points badge (mobile and desktop) showing `Penalty: $45` when `user.penalty_owed() > 0`. Sits next to the existing `cumulative_scores` line — same visual pattern.

**c. Prize Pool sidebar card** updated to three lines (see Q6).

### 2. `templates/tournament_detail.html` — Tournament page

**a. New `badge-penalty` pill** next to the existing `badge-cut` / `badge-dq` badge on both primary and backup pick cells, shown when `tournament.is_major` and the status triggers it **and** the badge is on the row's active player. Important: the current template shows cut/dq badges on **both** primary and backup columns regardless of which was active. The penalty badge must only appear next to the **active** player's name. If primary missed cut but backup activated and placed top-20, no penalty; the cut badge still shows on the primary cell but no penalty badge appears next to it.

**b. New 4th stat card** above the picks table, shown only when `tournament.is_major`, `tournament.results_finalized`, and at least one pick has `penalty_triggered`:
> **Penalties Assessed**
> **$90**
> 6 picks

**c. Legend bar** gets a new entry: `<span class="badge-penalty">+$15</span> Major CUT/DQ penalty`.

### 3. `templates/my_picks.html` — User's own picks

**a. New `badge-penalty` pill** next to `badge-cut`/`badge-dq` on the active-player cell (primary column if `active == primary`, backup column if `active == backup`). Same active-only rule as tournament detail.

**b. Season Summary sidebar card** gets a new line below Total Points: `Penalty Owed: $45 (Outstanding: $15)` in red, only shown when `current_user.penalty_owed() > 0`.

**c. Legend card** gets the same new entry as tournament detail.

### 4. `templates/admin/payments.html` — **[Q4]**

**Depends on Q4.** If A: add a column showing `penalty_owed` and an input bound to `penalty_paid` with a save button. If B: new page. If C: no template edit.

---

## File Inventory

**Modify:**
- `models.py` — add two columns, `PENALTY_PER_INCIDENT` constant, `User.penalty_owed()` / `penalty_outstanding()` methods, one block in `Pick.resolve_pick()`
- `app.py` — augment `tournament_picks` dict in the `index()` route to include `penalty_triggered`; augment tournament detail route similarly if needed; **[Q4]** admin payments route handler for `penalty_paid` field
- `static/css/style.css` — add `.badge-penalty` class (see Q8)
- `templates/index.html` — two insertions (per-pick badge, per-user penalty line) + Prize Pool card update
- `templates/tournament_detail.html` — per-pick badge (active only), stat card, legend
- `templates/my_picks.html` — per-pick badge (active only), sidebar line, legend
- `templates/admin/payments.html` — **[Q4]**

**Create:**
- `migrations/versions/<new>.py` — Alembic migration (generated)
- `tests/test_penalty_resolution.py` — new test file for penalty logic

**No changes:**
- `sync_api.py` — results sync calls `Pick.resolve_pick()` which is where we intercept; no sync-layer changes
- `send_reminders.py`
- `config.py`

---

## Task Breakdown

> Every task below assumes **Q1=D, Q2=A, Q3=A, Q4=A, Q5=A, Q6=A, Q7=A, Q8=approved**. If any answer differs, the affected tasks are retagged and replanned before execution.

### Task 1: Model changes — add `Pick.penalty_triggered` and `User.penalty_paid` columns (failing migration test first)

**Files:**
- Modify: `models.py`
- Create: `tests/test_penalty_model.py`

- [ ] **Step 1: Write failing test for the new columns**

```python
# tests/test_penalty_model.py
import pytest
from models import db, User, Pick, Tournament, Player, TournamentResult

def test_pick_has_penalty_triggered_column(session):
    pick = session.query(Pick).first()
    assert hasattr(pick, 'penalty_triggered')
    assert pick.penalty_triggered is False  # default

def test_user_has_penalty_paid_column(session):
    user = session.query(User).first()
    assert hasattr(user, 'penalty_paid')
    assert user.penalty_paid == 0  # default
```

- [ ] **Step 2: Run test to see it fail**

```bash
python -m pytest tests/test_penalty_model.py -v
```
Expected: FAIL with `AttributeError: 'Pick' object has no attribute 'penalty_triggered'`

- [ ] **Step 3: Add columns to `models.py`**

In `class Pick`, after the existing `backup_used` column (around line 362):
```python
penalty_triggered = db.Column(db.Boolean, default=False, nullable=False)
```

In `class User`, after `has_paid` (around line 55):
```python
penalty_paid = db.Column(db.Integer, default=0, nullable=False)
```

At the top of `models.py` after the `format_score_to_par` function:
```python
PENALTY_PER_INCIDENT = 15  # dollars, for missed cut / DQ at a major
```

- [ ] **Step 4: Generate migration**

```bash
DATABASE_URL="sqlite:////Users/bhagstrom/Golf_Pick_Em/golf_pickem.db" flask db migrate -m "add missed-cut major penalty tracking"
```

- [ ] **Step 5: Review migration with `migration-reviewer` agent**

Per CLAUDE.md — never run `flask db upgrade` on a new migration without review.

- [ ] **Step 6: Apply migration**

```bash
DATABASE_URL="sqlite:////Users/bhagstrom/Golf_Pick_Em/golf_pickem.db" flask db upgrade
```

- [ ] **Step 7: Run tests, confirm they pass**

```bash
python -m pytest tests/test_penalty_model.py -v
```
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add models.py tests/test_penalty_model.py migrations/versions/
git commit -m "feat: add penalty_triggered + penalty_paid columns for major-cut rule"
```

---

### Task 2: `Pick.resolve_pick()` sets `penalty_triggered` for major CUT/DQ

**Files:**
- Modify: `models.py` — `Pick.resolve_pick()`
- Create: `tests/test_penalty_resolution.py`

**⚠️ Per CLAUDE.md: invoke the `pick-resolution-audit` skill before AND after this task.** Any change to `resolve_pick()` requires it.

- [ ] **Step 1: Invoke `pick-resolution-audit` skill for pre-change audit**

- [ ] **Step 2: Write failing tests covering every branch**

```python
# tests/test_penalty_resolution.py
# Tests for each case:
#   - Primary plays, misses cut at a major → penalty_triggered = True
#   - Primary plays, misses cut at a non-major → False
#   - Primary plays, DQ at major → True
#   - Primary plays, makes cut at major → False
#   - Primary WD early, backup plays and misses cut at major → True
#   - Primary WD early, backup plays, makes cut at major → False
#   - Primary WD early, backup WD early at major → False (neither actually cut)
#   - Primary WD after R2 at major → False (wd ≠ cut/dq)
#   - Primary plays at team event (non-major) → False
```

(Full test bodies to be written using existing `tests/conftest.py` fixtures — engineer: read `tests/test_pick_resolution.py` for the pattern before writing.)

- [ ] **Step 3: Run tests, confirm they fail**

```bash
python -m pytest tests/test_penalty_resolution.py -v
```

- [ ] **Step 4: Edit `resolve_pick()` in `models.py`**

After the major-multiplier block and before the `SeasonPlayerUsage` insert (around line 517), add:

```python
# Determine if this pick triggers a major missed-cut/DQ penalty.
# Only applies when the active player's result is CUT or DQ at a major.
active_result = (
    primary_result if self.active_player_id == self.primary_player_id else backup_result
)
self.penalty_triggered = bool(
    self.tournament.is_major
    and active_result is not None
    and active_result.status in ('cut', 'dq')
)
```

- [ ] **Step 5: Run tests, confirm they pass**

- [ ] **Step 6: Invoke `pick-resolution-audit` skill for post-change audit**

- [ ] **Step 7: Commit**

```bash
git commit -am "feat: flag picks with penalty_triggered when active player cuts/DQs at a major"
```

---

### Task 3: `User.penalty_owed()` and `penalty_outstanding()` helper methods

**Files:**
- Modify: `models.py` — `User` class
- Modify: `tests/test_penalty_model.py`

- [ ] **Step 1: Write failing test**

```python
def test_user_penalty_owed_counts_triggered_picks_this_season(session, user_with_two_major_cuts):
    user, season_year = user_with_two_major_cuts
    assert user.penalty_owed(season_year) == 30

def test_user_penalty_owed_ignores_other_seasons(session, user_with_old_penalty):
    user, current_season = user_with_old_penalty
    assert user.penalty_owed(current_season) == 0

def test_user_penalty_outstanding_subtracts_paid(session, user_with_two_major_cuts):
    user, season = user_with_two_major_cuts
    user.penalty_paid = 15
    assert user.penalty_outstanding(season) == 15

def test_user_penalty_outstanding_clamps_at_zero(session, user_overpaid):
    user, season = user_overpaid  # owed 15, paid 30
    assert user.penalty_outstanding(season) == 0
```

- [ ] **Step 2: Run tests, confirm they fail**

- [ ] **Step 3: Implement methods on `User`**

```python
def penalty_owed(self, season_year):
    """Total penalty amount ($) this user has incurred in the given season."""
    from sqlalchemy import func as sqla_func
    count = db.session.query(sqla_func.count(Pick.id)).filter(
        Pick.user_id == self.id,
        Pick.penalty_triggered == True,
    ).join(Tournament, Pick.tournament_id == Tournament.id).filter(
        Tournament.season_year == season_year,
    ).scalar() or 0
    return count * PENALTY_PER_INCIDENT

def penalty_outstanding(self, season_year):
    """Amount still owed after subtracting what's been paid."""
    return max(0, self.penalty_owed(season_year) - (self.penalty_paid or 0))
```

- [ ] **Step 4: Run tests, confirm they pass**

- [ ] **Step 5: Commit**

```bash
git commit -am "feat: User.penalty_owed() and penalty_outstanding() helpers"
```

---

### Task 4: Add `.badge-penalty` CSS class

**Files:**
- Modify: `static/css/style.css`

- [ ] **Step 1: Add the class** in the Badges section (after `.badge-dq`, around line 385)

```css
.badge-penalty {
  background-color: #fef2f2;
  color: var(--danger);
  font-weight: 700;
  font-size: 0.7rem;
  padding: 0.3em 0.6em;
  border-radius: var(--radius-sm);
  border: 1px solid rgba(185, 28, 28, 0.3);
}
```

- [ ] **Step 2: Commit**

```bash
git commit -am "feat: add badge-penalty style for major missed-cut UI"
```

---

### Task 5: Template — `templates/tournament_detail.html`

**Files:**
- Modify: `templates/tournament_detail.html`

- [ ] **Step 1: Add penalty badge next to primary-cell CUT/DQ**

In the primary pick cell block (around line 264), change:

```jinja
{% if result.primary_result.status == 'cut' %}
    <span class="badge badge-cut">CUT</span>
{% elif result.primary_result.status == 'dq' %}
    <span class="badge badge-dq">DQ</span>
...
```

to also emit the penalty badge when the pick was active and the tournament is a major:

```jinja
{% if result.primary_result.status == 'cut' %}
    <span class="badge badge-cut">CUT</span>
    {% if tournament.is_major and result.active_is_primary %}
        <span class="badge-penalty">+$15</span>
    {% endif %}
{% elif result.primary_result.status == 'dq' %}
    <span class="badge badge-dq">DQ</span>
    {% if tournament.is_major and result.active_is_primary %}
        <span class="badge-penalty">+$15</span>
    {% endif %}
```

*Note: requires `result.active_is_primary` boolean in the `pick_results` dict built in `app.py`'s `tournament_detail` route. See Task 7.*

- [ ] **Step 2: Same treatment on backup cell** (around line 285) using `result.active_is_backup`.

- [ ] **Step 3: Same on mobile card view** (around line 193) — single insertion at the pick-name area.

- [ ] **Step 4: Add 4th stat card** in the stat row (around line 110), conditional:

```jinja
{% if tournament.is_major and tournament.results_finalized and penalty_count > 0 %}
<div class="col-md-3 mb-3">
    <div class="stat-card">
        <div class="stat-card-label">Penalties Assessed</div>
        <div class="stat-card-value" style="color: var(--danger);">${{ "{:,}".format(penalty_total) }}</div>
        <div class="text-muted small">{{ penalty_count }} pick{% if penalty_count != 1 %}s{% endif %}</div>
    </div>
</div>
{% endif %}
```

Adjust col sizing of the existing 3 stat cards from `col-md-4` → `col-md-3` when the penalty card is visible (use a Jinja set to pick the class).

- [ ] **Step 5: Update legend bar** (around line 336) — add after the `badge-dq` entry:

```jinja
&middot; <span class="badge-penalty">+$15</span> Major CUT/DQ penalty
```

- [ ] **Step 6: Visual check** — start dev server, load a completed major tournament (will need fixture data since Masters isn't done yet)

- [ ] **Step 7: Commit**

---

### Task 6: Template — `templates/my_picks.html`

**Files:**
- Modify: `templates/my_picks.html`

- [ ] **Step 1: Primary-cell penalty badge** (around line 202) — same active-only pattern as Task 5 using `pick.penalty_triggered` (we already have the `Pick` object here, so no helper field needed):

```jinja
{% if pick.penalty_triggered and pick.active_player_id == pick.primary_player_id %}
    <span class="badge-penalty">+$15</span>
{% endif %}
```

- [ ] **Step 2: Backup-cell penalty badge** (around line 227).

- [ ] **Step 3: Same on mobile card view** (around line 87).

- [ ] **Step 4: Season Summary sidebar card** (around line 290) — add below total points:

```jinja
{% set owed = current_user.penalty_owed(season_year) %}
{% if owed > 0 %}
<p class="mt-2 mb-0" style="color: var(--danger);">
    <strong>Penalty Owed:</strong> ${{ owed }}
    {% set outstanding = current_user.penalty_outstanding(season_year) %}
    {% if outstanding < owed %}
        <br><small>Outstanding: ${{ outstanding }} (Paid: ${{ current_user.penalty_paid }})</small>
    {% endif %}
</p>
{% endif %}
```

- [ ] **Step 5: Legend card** (around line 330) — add entry.

- [ ] **Step 6: Commit**

---

### Task 7: Template + route — `templates/index.html` and `app.py` `index()` route

**Files:**
- Modify: `templates/index.html`
- Modify: `app.py` — `index()` route handler

- [ ] **Step 1: Augment `tournament_picks` dict in `index()` route**

Add `penalty_triggered` and `active_is_primary` / `active_is_backup` booleans to each entry.

- [ ] **Step 2: Augment users list with `penalty_owed_amount`**

Pre-compute per user to avoid N+1 queries in the template:

```python
penalty_owed_by_user = {
    u.id: u.penalty_owed(season_year) for u in users
}
```

Pass to template as `penalty_owed_by_user`.

- [ ] **Step 3: Penalty badge next to tournament pick** — both mobile card and desktop table. Use `tournament_picks[user.id].penalty_triggered`.

- [ ] **Step 4: Penalty line under Total Points** — both mobile and desktop (match `cumulative_scores` pattern).

```jinja
{% if penalty_owed_by_user.get(user.id, 0) > 0 %}
<div class="small" style="color: var(--danger);">
    Penalty: ${{ penalty_owed_by_user[user.id] }}
</div>
{% endif %}
```

- [ ] **Step 5: Update Prize Pool sidebar card** (around line 394) — three-line format:

```jinja
{% set entry_total = 25 * users|length %}
{% set penalty_total = penalty_owed_by_user.values() | sum %}
<p class="mb-0">
    Entry: $25 × {{ users|length }} = ${{ entry_total }}
    {% if penalty_total > 0 %}
        <br>Penalties: +${{ penalty_total }}
        <br><strong>Total: ${{ entry_total + penalty_total }}</strong>
    {% endif %}
</p>
```

- [ ] **Step 6: Commit**

---

### Task 8: **[Q4]** Admin payments page — penalty collection column

**Files:**
- Modify: `templates/admin/payments.html` *(unread — engineer: read first before editing)*
- Modify: `app.py` — admin payments POST handler

**⚠️ Depends on Q4. If Q4=A, this task executes. If Q4=B, replan as new page. If Q4=C, skip task entirely.**

- [ ] **Step 1: Read `templates/admin/payments.html` and the corresponding route in `app.py`**

- [ ] **Step 2: Add a "Penalty" column**

Column shows: `Owed: $X` / `Paid: $[editable input]` / `Outstanding: $Y`. A save button on each row.

- [ ] **Step 3: Route handler accepts penalty_paid updates**

Validate input is non-negative integer, update `user.penalty_paid`, commit, flash success.

- [ ] **Step 4: Commit**

---

### Task 9: End-to-end visual verification

**Files:** none

- [ ] **Step 1: Seed a fixture DB** with a finalized major containing picks in every state (miss cut, DQ, make cut, WD early with backup activation, WD after R2)

- [ ] **Step 2: Start dev server**

```bash
flask run
```

- [ ] **Step 3: Walk through each affected page** in a browser:
  - `/` — standings with penalty line + Prize Pool card
  - `/tournaments/<id>` — tournament detail with stat card + per-pick badges
  - `/my-picks` — sidebar owed/outstanding + per-pick badges
  - `/admin/payments` — penalty column *(if Q4=A)*

- [ ] **Step 4: Invoke `playwright` plugin for screenshot evidence** — capture each page state for the commit message.

- [ ] **Step 5: Invoke `code-simplifier` plugin** per CLAUDE.md workflow.

- [ ] **Step 6: Invoke `pyright-lsp`** to catch type errors.

- [ ] **Step 7: Invoke `coderabbit` for pre-merge review.**

- [ ] **Step 8: Final commit and push** (CLAUDE.md says direct commits to main — no PR).

---

## Self-Review Notes

This plan is **provisional** pending answers to Q1–Q8. When the answers come back:

1. Lock in the tracking model (Q1) — determines whether Task 1 adds one column or two, or a new table.
2. Lock in Q2 — if the answer is B, `User.calculate_total_points()` needs to subtract penalties and Task 3 expands.
3. Lock in Q4 — Task 8 either stays, becomes a new template task, or deletes.
4. Lock in Q5 + Q6 + Q7 + Q8 — tweak copy/CSS in Tasks 4–7.
5. Re-run the self-review checklist (spec coverage, placeholder scan, type consistency) and fix inline.
6. Remove this section and the Open Questions section. The clean plan is then ready to execute.

**Known non-obvious risks:**
- The `active_is_primary` / `active_is_backup` flags in `tournament_picks` dict (Task 7) don't exist yet — the existing template infers backup activation from a different field. Engineer must verify the dict-building code in `app.py` and add these flags without breaking existing uses.
- Adding a 4th stat card to `tournament_detail.html` requires changing the existing col-md-4 → col-md-3 responsively, which is a Jinja conditional. Make sure mobile layout still stacks cleanly.
- `penalty_owed()` issues one query per user on the standings page. Pre-aggregate in the route (Task 7 Step 2 already does this).
- `tests/conftest.py` fixtures may not include a major tournament with CUT/DQ results — Task 2 may need new fixtures added before the penalty tests can run.
