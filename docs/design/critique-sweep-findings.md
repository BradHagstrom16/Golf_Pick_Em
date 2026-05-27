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

- [x] 1. Shell (base.html)
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
| 1 | base.html | 27/40 | Not AI slop (1 detector flag = false positive) | 0 |

## Global issues (recur across pages → fix-campaign Phase 1)

These trace to `base.html` / design tokens / `style.css` and therefore recur on every page. Units 2–10 should reference these by id rather than re-reporting.

- **[G1] Low-contrast global color tokens fail WCAG AA.** `--text-muted: #8b95a2` computes **2.9:1** on `--bg` (`#faf8f4`) and **3.0:1** on white; gold accents `--gold-500: #b8993e` compute **2.7:1** on white. Used pervasively (nav subtext, footer line, every `.text-muted`, gold links/`.text-gold`, points chip ~3.48:1, admin badge ~4.16:1). Detector flagged 12 low-contrast instances on `/`; Assessment A independently flagged the badge/chip. _Source: `style.css:21` (`--gold-500`), `style.css:33` (`--text-muted`). Fix once at the token level → propagates everywhere. P1._
- **[G2] Keyboard focus ring uses Bootstrap default status-blue.** `:focus` shows `rgba(13,110,253,0.25)` blue glow on nav/links/buttons — violates the design system's role-locked "blue = tournament status only" rule and is low-contrast on the pine-green nav. Define a brand `:focus-visible` ring (gold/paper). Applies to all focusable chrome on every page. P1.
- **[G3] No skip-to-content link; `<nav>` and `<main>` lack landmarks/ids.** No skip link, `<nav>` has no `aria-label`, `<main>` has no `id`. Keyboard/SR users tab through the full nav on every page. PRODUCT.md commits to WCAG 2.1 AA. P2.
- **[G4] No active-nav / `aria-current` state.** The nav never marks the current section (`.nav-link.active` style exists in CSS but is unused). Forces working memory on every page; breaks Visibility-of-System-Status site-wide. P1.

**Detector false positive (do not fix):** `ai-color-palette → "Cyan gradient background"` — the only gradients in `style.css` are the **green** navbar (`:95`) and footer (`:670`) brand gradients (Augusta pine, per DESIGN.md). The detector misclassifies the brand green gradient as cyan. Intentional, analogous to the `.column-divider` border-left exception.

## Per-unit reports

### Unit 1 — Shell (base.html)

**Scope:** global chrome only — top nav, footer, brand lockup, global type scale, color tokens, button/link styles, focus/hover, mobile nav. (Home body content = Unit 2.)
**Rendered:** `http://127.0.0.1:5001/` logged in as admin `Sun Day Regrets`. Assessment A = isolated `general-purpose` sub-agent (`[LLM]` tab, read template + `style.css` + PRODUCT/DESIGN + impeccable refs). Assessment B = `impeccable detect --json http://127.0.0.1:5001/` (anonymous Puppeteer render) + logged-in `[Human]` tab screenshot.

**Nielsen scorecard: 27/40 (Acceptable, top of band)**

| # | Heuristic | /4 | Key issue |
|---|-----------|----|-----------|
| 1 | Visibility of system status | 1 | No active-nav indication ([G4]) |
| 2 | Match real world | 4 | Plain clubhouse language |
| 3 | User control & freedom | 3 | Brand=home, logout in dropdown |
| 4 | Consistency & standards | 3 | Focus uses status-blue ([G2]) |
| 5 | Error prevention | 3 | Little to prevent at shell level |
| 6 | Recognition vs recall | 2 | No active state; menu hides actions behind caret |
| 7 | Flexibility & efficiency | 2 | No skip link / accelerators ([G3]) |
| 8 | Aesthetic & minimalist | 4 | Restrained, ledger-like |
| 9 | Error recovery | 3 | Dismissible flash region, clear semantics |
| 10 | Help & documentation | 2 | No help/about/rules link in nav or footer |

**Anti-patterns verdict:** **Not AI slop.** Assessment A: clears every absolute ban (no side-stripes, no gradient text, no glassmorphism, no hero-metric template, real nav). Committed identity (pine-green gradient, DM Serif wordmark, role-locked gold). Detector: 1 `ai-color-palette` flag = **false positive** (brand green gradient misread as cyan). Overlay: n/a (no `live` CLI). Net: authored, on-brand chrome.

**Overall impression:** Visually excellent and genuinely on-brand; the chrome recedes so data leads (cognitive load = 1 failure, Low band). The drag is interaction/state plumbing, not aesthetics.

**Priority issues** (each with suggested impeccable command):

- **P1 [global G4] No active-state / current-page indication.** *What:* zero `.active`/`aria-current` on nav (the `.nav-link.active` style exists but is unused). *Why:* breaks Visibility-of-Status + Recognition-over-recall; forces working memory site-wide. *Fix:* set `active`+`aria-current="page"` from the route endpoint; style with the existing white-wash bg + subtle gold underline. → `/polish` (nav state) or `/clarify` (wayfinding).
- **P1 [global G2] Focus ring uses role-locked status-blue.** *What:* Bootstrap default blue glow on nav/brand/toggler/dropdown. *Why:* violates "blue = tournament status only"; low-contrast on pine. *Fix:* brand `:focus-visible` ring in gold/paper. → `/audit` (a11y) then `/polish`.
- **P1 [local] Season points total hidden on mobile — the primary device.** *What:* `.badge-points` is `d-none d-md-inline`; the user's own total (`$13,172,924`) is `display:none` < 768px and surfaced nowhere else in mobile chrome. *Why:* PRODUCT.md says most visits are on a phone and "the one number that matters reads in a single glance" — the shell hides exactly that. *Fix:* show the chip inside the expanded mobile menu / a compact total in the collapsed bar. → `/adapt` (responsive) or `/layout`.
- **P2 [global G3] No skip link; `<nav>` unlabeled, `<main>` has no id.** *Fix:* visually-hidden-focusable "Skip to content"→`#main`, `aria-label="Primary"` on `<nav>`, `id="main"` on `<main>`. → `/harden` or `/audit`.
- **P2 [global G1] Marginal AA contrast on admin badge (~4.16:1) & points chip (~3.48:1)** — token-level, see [G1]. *Fix:* darken chip figure toward `--gold-400/500` or solidify chip bg; re-verify ≥4.5:1. → `/audit` (contrast).
- **P3 [local] Tap targets a hair under 44px** (toggler 40px, nav links 43px). *Fix:* pad to ≥44px. → `/adapt`.

**Persona red flags:**
- *Jordan (first-timer):* no "where am I" cue; no help/rules entry point anywhere in the chrome (rules happen to live in a home body card, but the shell promises nothing); username-as-menu (caret only) may not read as a menu.
- *Casual member, phone, sunlight, mid-banter:* **their own total is invisible on mobile** (worst chrome failure for this persona — it's the number they'd glance at to win the argument); hamburger is the lowest-contrast control (thin `rgba(255,255,255,0.2)` outline on green) — easy to miss squinting; sub-44px targets risk missed taps. Positive: once open, tall rows + big serif standings are sun-legible.

**Minor observations:** wordmark is text+emoji-favicon only (no custom mark); footer defines a gold `footer a` link style that's never used (dead style — footer was likely meant to hold rules/contact links); brand `letter-spacing 0.01em` vs DESIGN spec `-0.01em`; year tag "2026" is inline-styled (only presentational inline CSS in shell); dropdown border is neutral `rgba(0,0,0,0.08)` rather than a green-tinted hairline (deviates from Green-Tint elevation rule).

**Questions:** (1) Why hide the user's points total on the device most people check from? (2) Is the missing active-nav state deliberate or never wired? (3) Where is the shell's "ask the steward" (rules/help) affordance for a new member? (4) Should focus be gold to stay in brand voice? (5) Wordmark-only lockup — intentional restraint or unfinished?

**Detector raw (Assessment B, `/` anonymous render, 15 findings):** 12× low-contrast (3 unique pairs → [G1]), 1× `ai-color-palette` "Cyan gradient" (**false positive**), 1× `layout-transition` `transition: width` (home progress bar → Unit 2), 1× `skipped-heading` h2→h5 (home content → Unit 2).

## Deferred prioritization & fix campaign

_Filled at consolidation (Session F)._
