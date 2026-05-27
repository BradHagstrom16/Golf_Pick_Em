# Impeccable Critique Sweep — Design

**Date:** 2026-05-26
**Status:** Approved, ready for implementation plan
**Goal:** Run an `impeccable critique` across every HTML page in Golf Pick 'Em, producing one consolidated findings doc and a prioritized fix campaign. This spec covers the *diagnostic sweep only*; the fix campaign is a separate spec handed off at the end.

## Decisions (locked)

1. **Workflow model: diagnose all, fix later.** Critique every unit first, pool findings, defer all fixes. Reason: all pages share one `static/css/style.css`, so fixing mid-sweep would silently invalidate critiques of pages not yet examined.
2. **Render strategy: live dev app, logged in.** Run Flask, log in as admin, navigate real rendered pages with existing dev data. Spin a CLAUDE.md-style standalone harness only for a state the dev data cannot produce (live/projected earnings; error pages if needed).
3. **Granularity: hybrid.** Solo critiques for the shell and high-stakes core-loop pages; grouped critiques for the auth trio, admin tables, and error pages. 10 critique units total.

## Page inventory

15 templates (~1,750 lines core + 780 admin), all extending `base.html`, all rendered server-side via Jinja2 + Bootstrap 5.

| Route | Template | Auth | Lines |
|---|---|---|---|
| `/` | `index.html` | public | 442 |
| `/schedule` | `schedule.html` | public | 125 |
| `/tournament/<id>` | `tournament_detail.html` | public | 374 |
| `/login` | `login.html` | public | 68 |
| `/register` | `register.html` | public | 58 |
| `/my-picks` | `my_picks.html` | login | 365 |
| `/pick/<id>` | `make_pick.html` | login | 148 |
| `/change-password` | `change_password.html` | login | 45 |
| `/admin` | `admin/dashboard.html` | admin | 206 |
| `/admin/override-pick` | `admin/override_pick.html` | admin | 235 |
| `/admin/payments` | `admin/payments.html` | admin | 152 |
| `/admin/users` | `admin/users.html` | admin | 103 |
| `/admin/tournaments` | `admin/tournaments.html` | admin | 68 |
| error handler | `errors/404.html` | — | 9 |
| error handler | `errors/500.html` | — | 9 |
| (shell) | `base.html` | — | 129 |

## Critique units & sequencing

10 units, ordered foundation-first → highest-stakes → boilerplate.

| # | Unit | Pages | Rationale |
|---|---|---|---|
| 1 | **Shell** | `base.html` | First, always. Nav/footer/global type scale/color tokens/button styles live here; its findings become the canonical "global issues" list so units 2–10 reference rather than re-report them. |
| 2 | Home / standings | `index.html` | Front door #1 (checking standings). Highest traffic. Solo. |
| 3 | Make a pick | `make_pick.html` | Front door #2 (locking the weekly golfer). Equal front door per PRODUCT.md. Solo. |
| 4 | Tournament detail | `tournament_detail.html` | Leaderboard + earnings ledger — the trust surface. Solo. |
| 5 | My picks | `my_picks.html` | Personal history; WD/backup/penalty state display. Solo. |
| 6 | Lighter public | `schedule.html` + `errors/404` + `errors/500` | Schedule is a lighter standalone; 9-line error pages warrant only a copy/recovery-path check, so they ride along. |
| 7 | Auth trio | `login` + `register` + `change_password` | Share one form pattern; critique once. |
| 8 | Admin dashboard | `admin/dashboard.html` | Admin command center. Solo. |
| 9 | Admin override-pick | `admin/override_pick.html` | Most complex admin form (WD/backup override). Solo. |
| 10 | Admin tables | `admin/tournaments` + `users` + `payments` | Three table/list surfaces sharing patterns. Grouped. |

**Ordering rationale:** shell sets the foundation; the two front doors and money/trust pages come next so the most important pages are covered first if energy runs out; auth and admin (lower traffic, conventional, but PRODUCT.md still demands clubhouse warmth) come last.

## Per-unit procedure

Each unit follows the impeccable `critique` workflow faithfully, with two sweep adaptations (defer interaction, pool findings).

1. **Render setup.** Confirm the dev app is up and logged in as admin. Navigate to the unit's real route(s) using existing dev data: a *complete* tournament gives `tournament_detail` its rich final-earnings state; an *upcoming* one with open picks drives `make_pick`. Spin a harness only for a state the dev data can't show.

2. **Two isolated assessments** (core of critique's honesty — non-negotiable; neither sub-agent sees the other's output):
   - **Assessment A — LLM design review:** dedicated sub-agent reads the template + `style.css`, opens its own new browser tab labeled `[LLM]`, scores AI-slop tells, Nielsen's 10 heuristics (0–4), cognitive load (8-item checklist), emotional journey. Returns structured findings only.
   - **Assessment B — automated detection:** `npx impeccable --json <template>` (27-pattern detector) + live overlay (`npx impeccable live`) injected into its own new tab labeled `[Human]`, results read from console.
   - ~20 sub-agent assessments across the campaign. Intrinsic to the requested workflow, not convenience spawning.

3. **Combined report.** Synthesize A + B into the standard critique report: Nielsen scorecard `/40`, anti-patterns verdict, what's working, P0–P3 priority issues with suggested commands, persona red flags, minor observations.

4. **Defer & pool (sweep adaptation).** Do NOT run critique's interactive "Ask the User" / "Recommended Actions" per page. Append the report to the consolidated findings doc, tagging each priority issue **global** (recurs; traces to shell/tokens/CSS) or **local** (this page only). Interactive prioritization happens once at consolidation.

## Pacing

1–2 units per working session (each unit is heavy: render + 2 isolated assessments + report).

| Session | Units |
|---|---|
| A | Setup + 1 Shell + 2 Home |
| B | 3 Make-pick + 4 Tournament detail |
| C | 5 My-picks + 6 Schedule/errors |
| D | 7 Auth trio + 10 Admin tables |
| E | 8 Admin dashboard + 9 Override-pick |
| F | Consolidation + interactive prioritization + fix-campaign plan |

≈5 sweep sessions + 1 consolidation. Adjustable.

## Consolidated findings doc

`docs/design/critique-sweep-findings.md`, a living file updated at the end of every session.

- **Status checklist** of all 10 units (cross-session continuity — each session resumes by reading this doc to know what is done).
- **Cross-page scorecard matrix:** rows = pages; columns = Nielsen `/40`, AI-slop verdict, P0 count.
- **Global issues** section: recurring tells traced to shell/tokens/CSS → become Phase 1 of the fix campaign.
- **Per-unit reports** appended in full.
- **Deferred prioritization + fix campaign:** filled only at consolidation.

## Fix-campaign handoff (defined, not executed here)

Consolidation turns pooled findings into one prioritized impeccable-command sequence, ordered **shell/tokens first → core-loop pages → boilerplate**, so global CSS edits land before dependent pages. Each phase = its own branch + PR tagged `@coderabbitai review` (per branch-strategy preference). Re-run `critique` on changed pages to confirm the score moved. That campaign is a separate spec; this one ends at delivering the prioritized plan.

## Out of scope

- Executing any fixes (separate spec).
- Changing `style.css`, templates, or any project file during the sweep.
- Re-architecting routes or adding new pages/states beyond throwaway render harnesses.
