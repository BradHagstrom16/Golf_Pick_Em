# Impeccable Critique Sweep — Findings

Living doc, updated at the end of each unit. Spec: `docs/superpowers/specs/2026-05-26-impeccable-critique-sweep-design.md`. Plan: `docs/superpowers/plans/2026-05-26-impeccable-critique-sweep.md`.

## Seeded environment (Session A)

The dev DB (`golf_pickem.db`) was **not** cleared — it holds a full, realistic 2026 season. Per user decision (2026-05-26), we **preserved & augmented** rather than wiping. Captured ids/state below; later sessions reuse these.

- **Admin / sweep creds:** user id **1**, username `Sun Day Regrets`, password `CritiqueSweep!2026`, `is_admin=True`. (Password (re)set during seeding.)
- **Second non-admin user (no pick on the active major):** plenty exist; e.g. user id **9** (`Rbrook11`, display "RiBrooks") shows the "No Pick / $0" state. 17 of 19 users have no pick on tournament 23.
- **In-progress MAJOR (live leaderboard):** tournament id **23** — `U.S. Open`, repurposed to `status='active'`, `is_major=True`, `purse=0` → `effective_purse=$21,500,000` with `est.` badge. Dates shifted to the current week (start 2026-05-21, end 2026-05-31, deadline 2026-05-21 06:30 CT = passed) so the home route features it as `next_tournament`. 16 `TournamentResult` rows (live), 8 picks. **NOTE for Session C:** this shifts U.S. Open out of its real June slot on `/schedule` — restore or annotate before the schedule critique (Unit 6).
  - Picks exercise: projected earnings (e.g. Brice Garnett T1 → $2.8M), **backup activation** (user 3 primary WD R1 → Denny McCarthy 🔄 T12 $250k), and **two live missed-cut penalties** (user 2 Sam Stevens CUT +$15; user 6 Sahith Theegala DQ +$15).
- **Complete majors (final earnings, 1.5×):** Masters (id **13**, finalized), PGA Championship (id **18**, finalized).
- **Upcoming (picks-open target for Unit 3 make_pick):** Charles Schwab Challenge (id **20**, starts 2026-05-28) — **field not yet seeded** (0 players); seed a field in Session B.

**Tooling note (affects Assessment B for all units):** the installed `impeccable` CLI uses `impeccable detect [--json] <file|dir|url>` and has **no `impeccable live` overlay server** (`/live` is an AI-harness slash command, not a CLI). JSON output is written to **stderr**, exit code 2 = findings found. Template files scanned standalone return `[]` (jsdom can't resolve the Jinja `{{ url_for }}` stylesheet link → no computed styles). So Assessment B runs the detector against the **live URL** (`detect --json http://127.0.0.1:5001/<route>`, Puppeteer renders real CSS but **anonymous** — login-required routes redirect, fall back to a logged-in screenshot), plus a logged-in `[Human]` tab screenshot in place of the nonexistent overlay.

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
