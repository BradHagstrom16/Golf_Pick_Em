# Impeccable Fix Campaign — Design

**Date:** 2026-05-27
**Status:** Approved, ready for implementation plan
**Goal:** Remediate the issues found by the impeccable critique sweep — the 13 globals (G1–G13) and every unit's P0–P3 locals — in a prioritized, branch-per-phase campaign that raises the Nielsen scores (especially the admin cluster at 19–21/40) without re-introducing the AI-slop tells the sweep caught.

## Relationship to the sweep

This is the **fix-campaign spec** the diagnostic sweep handed off (`docs/superpowers/specs/2026-05-26-impeccable-critique-sweep-design.md`, "Fix-campaign handoff"). The sweep critiqued all 10 units and pooled findings; this spec turns that pool into an ordered remediation plan.

**Authoritative issue list:** `docs/design/critique-sweep-findings.md` → "Deferred prioritization & fix campaign". That section's master table (every issue → phase + command) is the source of truth; this spec defines the *campaign structure*, not a re-listing of issues. Per-unit reports and global definitions (G1–G13) in the same doc carry the detail.

## Decisions (locked)

These were settled in the Session-F interactive prioritization (the deferred critique "Ask the User" step, run once):

1. **Logic/route correctness opens the campaign, not CSS.** The two code P0s (U4 hidden live penalty, U7 register form-wipe) plus the U9 re-resolve logic gate are the highest-severity items and touch `app.py`/templates/JS — disjoint from the token work, so no rework risk. They ship first. The global-token foundation still precedes every *page* phase that consumes it.
2. **Admin cluster = one phase, G12+G13 led.** The lowest group collapses to G12 (a largely mechanical class-swap onto existing design-system classes) + G13 (mutation safety). Migrate all three admin templates and add the safety pattern together.
3. **Re-baseline the gated units first.** Before fixing, re-run the detector on Units 3/5/7/10 through the Session-E authenticated render harness so their before/after deltas are deterministic, not Assessment-A-only.
4. **Brand integrity over linter-appeasement.** The green-gradient detector flags are a tool-classifier limitation (brand greens at hue ~161°), not a design error. Pinehurst Pine `#006747` stays. The CLI has no ignore flag, so a signature-tight known-FP filter goes in the harness post-processing (Setup), never a design change.
5. **Branching.** Each phase = its own branch + PR tagged `@coderabbitai review`. The Session-F consolidation (findings section + this spec + the plan) commits to `docs/impeccable-critique-sweep`.

## Phase architecture

A re-baseline **Setup** step, then **five ordered phases**. Within each phase, fix P0 → P1 → P2 → P3.

```
Setup (re-baseline + harness FP filter; no fixes)
  │
  ├─ Phase 1  Logic & route correctness      (app.py / templates / JS)   ─┐ parallelizable
  └─ Phase 2  Global shell & token foundation (style.css / base.html)     ─┘ (disjoint files)
                          │  (Phase 2 must merge before 3–5)
       ┌──────────────────┼──────────────────┐
   Phase 3            Phase 4            Phase 5
   Core-loop pages    Lighter public     Admin cluster
```

**Ordering rationale:** logic carries the trust-breaking P0s and is file-disjoint, so it opens (and may run parallel to Phase 2). Global tokens must land before the page phases that consume them (the spec's "shell/tokens first"). Core loop before boilerplate; admin last but highest-leverage.

### Setup — re-baseline (no fixes)

- Rebuild `.critique_shots/harness.py` from the snippet in the findings-doc Tooling note (Flask test client + injected admin session → repo-root HTML → `python -m http.server 8765` → `impeccable detect --json`). Non-mutating (GET + the non-saving `load_field` POST only).
- Re-run `impeccable detect` on Units 3/5/7/10 through the harness; record deterministic baseline scores alongside the existing Assessment-A scores.
- Add the **signature-tight green-gradient known-FP filter** to the harness post-processing: strip the `ai-color-palette` "Cyan gradient" and `dark-glow` "#00432e on dark" findings only when keyed to the `#00432e`/`#005c3f` brand tokens or the navbar/footer selectors. Never a loose "contains cyan" match. Document the filter inline.

### Phase 1 — Logic & route correctness (code/logic, NOT an impeccable pass)

Fixes nothing with a styling command; uses `test-driven-development`, and `pick-resolution-audit` wherever earnings/resolution logic is touched. Contents (see findings master table, Phase 1 block): U4 P0 penalty-gate bug, U7 P0 register repopulation, U9 P0 re-resolve logic gate, U4 ranking (`loop.index`), U3/U9 same-player `alert()`-wipe + USED-not-disabled, U10 reset-pw default + payment-toggle silent-swallow, U3 punctuated-name search. The U9 P0 **confirm UI** is deferred to Phase 5 (it depends on the admin design-system migration); only its logic gate + consequence wiring ships here.

### Phase 2 — Global shell & token foundation (`style.css` + `base.html`)

The propagating fixes; must merge before Phases 3–5. Contents: G1 contrast tokens, G2 brand focus ring, G3 skip-link/landmarks, G4 active-nav/`aria-current`, G5 heading discipline, G6 penalty component reframe, G8 gold-register est-purse chip token, G9 44px tap-target floor, G10 flash `role="alert"`/`aria-live` + field-error scaffold, G11 shared money-figure treatment, plus the U1 mobile-points-total shell local. Commands per the master table (`/audit`, `/polish`, `/harden`, `/typeset`, `/colorize`, `/adapt`).

### Phase 3 — Core-loop pages (`index`, `make_pick`, `tournament_detail`, `my_picks`)

Per-page locals + the per-surface application of G7 (mobile money pill keyed on `tournament.status`). Contents per the master table Phase 3 block (legend, as-of timestamp, row-status binding, live-row link, collapse no-pick rows, used-player cue, inline submit confirmation, etc.).

### Phase 4 — Lighter public (`schedule.html`, auth trio, `errors/{404,500}.html`)

Per-surface application of G8/G9/G10 + locals: schedule current-week anchor + label parity; auth Forgot-pw modal→inline, autocomplete, `.auth-card` float + `<h1>`; error-page lead contrast + 500 recovery path.

### Phase 5 — Admin cluster (`admin/dashboard`, `admin/override_pick`, `admin/{tournaments,users,payments}`)

One phase, G12+G13 led. G12 design-system migration (class-swap to `.table-greenside`/`.btn-greenside`/`.badge-status-*`/`.stat-card`/`.mobile-card-list`); G13 mutation-safety pattern (inline confirm + plain-language consequence + old→new summary) including the **U9 P0 confirm UI**; G11 gold/serif money on all admin figures; admin locals (Process-Results guard, mobile cards, hero-metric strip removal, 19 eager modals → one reusable dialog, jargon, badge contrast).

## Branching & verification workflow

- **One branch + PR per phase**, tagged `@coderabbitai review`. Phases 1 and 2 may proceed in parallel (disjoint files). **Phase 2 must merge before 3–5** (they consume its tokens/components).
- **Per-phase verification (folded in):** after each phase, re-run `impeccable critique` on the changed pages and confirm the Nielsen `/40` moved up; record the delta in the findings doc. Admin pages (Phase 5) require the authenticated harness for a real detector signal.
- **Domain-logic guardrails:** Phase 1 invokes `pick-resolution-audit` before and after any change to `Pick.resolve_pick()` / `process_tournament_results()` / override re-resolve. Any schema change invokes the `migration-reviewer` agent before `flask db upgrade` (none anticipated — these are display/route/CSS fixes).
- **Deferred-fix discipline ends here:** unlike the sweep, this campaign *does* edit templates, `style.css`, and routes. Each phase verifies its own pages; because Phase 2 touches shared CSS, it re-critiques a representative core-loop page to confirm no regression on already-good pages.

## Out of scope

- The green-gradient detector false positive as a *design* change (handled by the Setup harness filter; brand colors untouched).
- Re-architecting routes, adding new pages, or new tournament states beyond what a fix requires.
- Unrelated refactors not serving a specific finding.
- Backend/sync/API changes except the minimal route logic behind the P0s.

## Risks & constraints

- **Phase 1 touches money logic.** The U4 penalty-gate and U9 re-resolve fixes sit near `Pick.resolve_pick()`; TDD + `pick-resolution-audit` are mandatory, and the U9 confirm must not alter the re-resolution math, only gate and summarize it.
- **Phase 2 is high-blast-radius.** Token edits propagate to every page; the re-critique-a-core-page check guards against silently degrading an already-good surface (e.g., a contrast bump that dulls a gold badge).
- **Admin migration is mechanical but broad.** G12 is mostly a class swap, but the three templates lack any `.mobile-card-list`; adding it is net-new markup per table, the largest single chunk of work in the campaign.
