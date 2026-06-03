# The Burn List — Field-Usage Percentages

**Date:** 2026-06-03
**Status:** Approved design, pending implementation plan
**Branch:** `feature/burn-list`
**Process:** Brainstormed via `superpowers:brainstorming` + `impeccable shape` (product register). Visual direction chosen via two interactive mockup rounds (inline-dropdown treatment; searchable Burn List table).

## 1. Problem & Purpose

Members have no way to see how much of the league has already consumed a given golfer. That number is strategic intel in a once-per-season format:

- "Cam Young has been burned by 80% of the field" → he's gone for most rivals; picking him is contrarian-proof.
- "90% of the field still has Rahm" → he's a live, contested option this week.

The feature surfaces each golfer's **burn rate**: the share of the league that has used them this season.

## 2. Decisions (settled during brainstorming)

| Question | Decision |
|---|---|
| Where does it live? | Both surfaces: `/pick/<id>` and the Stats Hub |
| Denominator ("the field") | **All registered users** (`User.query.count()`) — matches the standings table exactly |
| Framing | Per-page: pick page shows **% remaining**; Stats Hub shows **% burned**. Same data, complements. |
| Pick-page treatment | **Inline in both Tom Select dropdowns** (mini bar + % per option row) — no new panels |
| Stats Hub treatment | **"The Burn List"**: full searchable table, fixed-sorted most→least burned |
| Relationship to "Most Picked" | The Burn List **replaces** Most Picked (identical ranking; the Burn List subsumes it and keeps the return column) |
| Sorting | Fixed default sort (burned% desc); search box filters by name; **no** interactive column sorting |

## 3. Data Model & Source of Truth

- **Source of truth: `SeasonPlayerUsage`** — the same table that gates pick availability (`User.get_used_player_ids()`). A golfer is "burned" by a user iff a usage row exists for `(user_id, player_id, season_year)`.
- Usage rows are written **only at tournament finalization** (`resolve_pick()` → rebuilt by `process_tournament_results()`). Consequences, both intentional:
  - The Burn List never moves mid-tournament and **never leaks the current week's secret picks**.
  - In-flight picks (deadline passed, results not finalized) do not count as burned.
- Math (integer, ledger-stable):
  - `pct_burned = round(100 * times_used / total_users)`; guard `total_users == 0` → 0.
  - `pct_remaining = 100 - pct_burned` (computed as the complement of the *rounded* value so the two pages never disagree).
- **No model changes. No migration.**

## 4. Backend Changes

### `stats.py`
- New `burn_list(season_year)` → list of dicts, one per golfer with ≥1 usage row:
  - `golfer` (display name), `times_used` (count of usage rows), `pct_burned`, `total_return` (coalesced sum of `Pick.points_earned` for completed-tournament picks where `active_player_id` is the golfer; 0 if none).
  - Counts come from `SeasonPlayerUsage` (authoritative), returns from the `Pick` join — if an admin override ever creates usage without a matching pick, the row still appears with $0 return.
  - Order: `pct_burned` desc, then `total_return` desc, then last name asc (mirrors the old `most_picked` ordering with a stable tail).
- `field_form(season_year)`: **remove `most_picked`** (queries, dict key). `form_guide` and `untouched_stars` unchanged.

### `app.py`
- `stats_hub`: pass `burn=stats.burn_list(season_year)` (and field dict no longer carries `most_picked`).
- `make_pick`: build `remaining_pct = {player.id: pct_remaining}` for the available players. **Suppression rule:** if the season has zero `SeasonPlayerUsage` rows, pass `remaining_pct=None` — the template renders plain dropdowns (all-100% is noise, not signal).

## 5. UI — Pick Page (`make_pick.html`)

- Server renders a JSON map keyed by player id (inline `<script>` via `tojson`); the Tom Select render overrides look percentages up by option value. (Tom Select does not auto-ingest `<option>` data attributes, so the map is the mechanism, not a fallback.)
- Tom Select `render.option` override: `Last, First` + horizontal bar + `NN%` (right-aligned, `tabular-nums`). `render.item` override: compact `NN%` pill beside the selected name.
- Applies to **both** Primary and Backup selects.
- One-line legend under the form intro: "% = share of the field that still has this golfer."
- **Regression guard:** the existing normalized search ("jj" → "J.J.") and the mutual-exclusion option rebuild (`excludeFrom`) must keep working — the rebuild reads `primarySelect.options`, so the custom data must survive `clearOptions()`/`addOption()` round-trips.
- When `remaining_pct` is None (week 1): no bars, no pills, no legend — exactly today's rendering.

## 6. UI — Stats Hub (`stats.html`)

"The Field" section keeps its grid. In the `field-pool` column:

- **"Most Picked" panel is removed.**
- **"The Burn List"** takes its place: subhead + subnote, a search input, and a table: `Golfer · ×Used · % of field (bar + numeral) · Return $`.
- "Still on the Board" stays beneath it — the 0%-burned counterpoint.
- Search: client-side filter on golfer name, reusing the same character-normalization as the pick page. Filtering updates a polite live-region row count.
- Renders only golfers with ≥1 burn; absence = unburned, made explicit by the search-miss copy.

## 7. Design System Constraints (Greenside Ledger)

- **Bars are Pinehurst Pine (#006747) only.** No second color for high/low: Money-Is-Gold and Status-Is-Cool role-lock gold and amber/blue away from this data. Bar length + numeral carry the signal. Track in a pale neutral (mint-tint family), rounded ends consistent with existing badge radii.
- % numerals: Plus Jakarta Sans, weight 600+, `tabular-nums`, right-aligned, AA contrast on white/cream.
- No serif in the table (Serif-For-Gravity rule); table follows `table-greenside`/`field-table` idiom; header row in Label type.
- Search input follows existing input vocabulary: faint green border, Sage focus ring, 6px radius, 48px-comfortable on mobile.
- Bars are decorative: `aria-hidden="true"`, with the % present as text in option labels and table cells.
- Elevation, spacing, zebra striping: inherit the existing Field tables; nothing floats, nothing animates beyond existing hover states. No new motion.

## 8. Copy (clubhouse voice, no hype, no em dashes)

| Spot | Copy |
|---|---|
| Burn List subnote | "Who the league has spent: the share of the field that has burned each golfer. Updates when results go final." |
| Pick-page legend | "% = share of the field that still has this golfer." |
| Empty state (no usage yet) | "No golfer has been burned yet. The ledger opens when the first tournament pays out." |
| Search miss | "Not on the list: no one has burned them yet." |

## 9. Key States

| State | Behavior |
|---|---|
| Default | Bars + % on both surfaces, completed tournaments only |
| Season start (no usage rows) | Burn List renders empty state; pick page suppresses indicators entirely |
| Search miss | Miss copy row (absence = 0% burned) |
| Mid-tournament | No movement; subnote explains the timing so members trust it |
| Golfer burned by all | 100%, full bar |
| New user joins mid-season | Denominator grows; percentages dilute (consistent with standings) |

## 10. Testing (TDD, per CLAUDE.md)

- `burn_list()` math: counts, rounding, zero-user guard, ordering (incl. ties).
- Denominator is all registered users (add a pick-less user; % drops).
- Empty season → `[]`.
- In-flight picks excluded (active tournament pick ≠ burned).
- `total_return` coalesces to 0 when usage exists without matching completed pick.
- `make_pick` context: `remaining_pct` map correct; `None` when season has no usage; complement consistency (`pct_remaining = 100 - pct_burned`).
- `stats` route: `burn` in context; `most_picked` gone (update any existing tests that reference it).
- Template smoke: Burn List renders rows/empty state; make_pick renders data attributes when map present, plain when None.
- Manual browser verification (Chrome DevTools MCP harness per CLAUDE.md): dropdown rendering, mutual-exclusion regression, mobile 48px rows, search filter.

## 11. Out of Scope

- Current-week pick popularity (live picks are secret until lock; burns only exist at finalization).
- Sortable columns, pagination, per-user burn breakdowns.
- Listing unburned golfers in the Burn List ("Still on the Board" + search-miss copy cover that story).
- Any change to `Pick.resolve_pick()`, earnings logic, or schema.

## 12. Implementation Process Requirements

- `writing-plans` skill next; plan encodes per-phase subagent-vs-inline execution mapping.
- `impeccable` governs all UI work (this spec inherits its constraints); `test-driven-development` for all code; `pyright` after `.py` edits; `coderabbit` review after route changes; PR off `feature/burn-list` with `@coderabbitai review`; `pr-review-toolkit` before merge.
- `pick-resolution-audit` not required: no resolution/earnings logic is touched (reads only).
