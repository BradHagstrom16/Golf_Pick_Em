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
- [x] 2. Home (index.html)
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
| 2 | index.html | 28/40 | Not AI slop (.column-divider 2px→1px fixed in Session A) | 0 |

## Global issues (recur across pages → fix-campaign Phase 1)

These trace to `base.html` / design tokens / `style.css` and therefore recur on every page. Units 2–10 should reference these by id rather than re-reporting.

- **[G1] Low-contrast global color tokens fail WCAG AA.** `--text-muted: #8b95a2` computes **2.9:1** on `--bg` (`#faf8f4`) and **3.0:1** on white; gold accents `--gold-500: #b8993e` compute **2.7:1** on white. Used pervasively (nav subtext, footer line, every `.text-muted`, gold links/`.text-gold`, points chip ~3.48:1, admin badge ~4.16:1). Detector flagged 12 low-contrast instances on `/`; Assessment A independently flagged the badge/chip. _Source: `style.css:21` (`--gold-500`), `style.css:33` (`--text-muted`). Fix once at the token level → propagates everywhere. P1._
- **[G2] Keyboard focus ring uses Bootstrap default status-blue.** `:focus` shows `rgba(13,110,253,0.25)` blue glow on nav/links/buttons — violates the design system's role-locked "blue = tournament status only" rule and is low-contrast on the pine-green nav. Define a brand `:focus-visible` ring (gold/paper). Applies to all focusable chrome on every page. P1.
- **[G3] No skip-to-content link; `<nav>` and `<main>` lack landmarks/ids.** No skip link, `<nav>` has no `aria-label`, `<main>` has no `id`. Keyboard/SR users tab through the full nav on every page. PRODUCT.md commits to WCAG 2.1 AA. P2.
- **[G4] No active-nav / `aria-current` state.** The nav never marks the current section (`.nav-link.active` style exists in CSS but is unused). Forces working memory on every page; breaks Visibility-of-System-Status site-wide. P1.

**Detector false positive (do not fix):** `ai-color-palette → "Cyan gradient background"` — the only gradients in `style.css` are the **green** navbar (`:95`) and footer (`:670`) brand gradients (Augusta pine, per DESIGN.md). The detector misclassifies the brand green gradient as cyan. Genuinely intentional.

**Resolved in Session A (user-authorized, isolated):** `.column-divider` `border-left` was `2px` (style.css:262-270) — a real **DESIGN.md:261 violation** ("no colored side-stripe >1px"), *not* a false positive. The prior "intentional exception" framing predated adopting impeccable/DESIGN.md standards. Since this class is used **only in `index.html`** (already critiqued — zero cross-contamination with un-examined pages), it was reduced to a **1px hairline** (`td` `rgba(0,103,71,0.25)`, `th` `0.4`) per DESIGN.md's prescribed fix and verified (computed 1px + visual). Unlike the green-gradient, do **not** treat a `border-left`/side-stripe detector finding as a blanket false positive going forward.

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

### Unit 2 — Home (index.html)

**Scope:** home body content only — standings (desktop table + mobile card list), pick CTA, earnings/dollar presentation, deadline visibility, the active "In Progress" banner, projected-vs-earned distinction, penalty/backup state legibility, empty states. (Shell = Unit 1.)
**Rendered:** `http://127.0.0.1:5001/` logged in as admin (rank 1) with the seeded **in-progress major (U.S. Open)** → active-tournament state: "In Progress / 1.5× Major" banner, "U.S. Open Pick / Position / Projected" columns, projected badges, a backup-activation row (Denny McCarthy 🔄), two live penalty badges (CUT +$15, DQ +$15). Assessment A inspected desktop (1280) + phone (390×844). Assessment B = `impeccable detect --json /` + `[Human]` screenshot.

**Nielsen scorecard: 28/40 (Good, lower end)**

| # | Heuristic | /4 | Key issue |
|---|-----------|----|-----------|
| 1 | Visibility of system status | 3 | "Projections" stated but no "as-of" timestamp / no refresh — board can go silently stale |
| 2 | Match real world | 3 | Fluent golf, but raw CUT/DQ/🔄/+$15 codes with no key |
| 3 | User control & freedom | 3 | Read-only board; no in-context next-pick exit during active week |
| 4 | Consistency & standards | 3 | Backup-pick affordance differs by breakpoint (desktop tooltip, mobile nothing) |
| 5 | Error prevention | 3 | Low error surface; good defaults (self-highlight, leader mark) |
| 6 | Recognition vs recall | 2 | Dense encoded board (🔄 👑 🏆 CUT DQ +$15, gold/green badges) with no legend |
| 7 | Flexibility & efficiency | 2 | No sort/filter/jump-to-me; 11/19 rows are "No Pick" noise during the major |
| 8 | Aesthetic & minimalist | 4 | Ledger identity fully realized; role-locked color, clear hierarchy |
| 9 | Error recovery | 3 | Empty cells (No Pick/None/$0) handled gracefully; no real error path |
| 10 | Help & documentation | 2 | Rules card is good but doesn't decode on-board symbols; bottom-of-page on mobile |

**Anti-patterns verdict:** **Not AI slop.** Ledger identity executed (Augusta green, gold-for-money, cream, serif-over-sans, flat-at-rest). No gradient text/glassmorphism/hero-tiles/icon-card-grid/modals. Assessment A raised `.column-divider` `border-left: 2px` (style.css:262-270) as a by-the-letter side-stripe-ban trip — on review this was a **real DESIGN.md:261 violation**, not the intentional exception it had been labeled; it is used only in this template, so it was **fixed in Session A** (2px → 1px hairline, user-authorized — see Global-issues note). Detector home-scoped flags: `skipped-heading` (h2→h5) and `layout-transition` (`transition: width` on progress bar); contrast greys trace to global **[G1]**.

**Overall impression:** Strong, on-brand, glanceable foundation. The recurring drag is **symbol/state legibility without a key** and **projection honesty over time** — both most acute on mobile, the primary device.

**Priority issues** (each with suggested impeccable command):

- **P1 [local→candidate global] Encoded board symbols have no on-screen legend.** *What:* 🔄 (backup), 👑 (override), CUT, DQ, +$15 (penalty), green-vs-gold badge split — no key on the page. *Why:* breaks Recognition-over-recall + "subtle rules demand obvious state"; members can't trust numbers they can't decode. *Fix:* compact legend row beneath standings (and mobile cards) shown when `results_tournament` is active; reuse the unused `.legend-bar` class. → `/clarify` + `/polish`. _Re-evaluate as global once Units 4 (tournament_detail) & 5 (my_picks) confirm the same vocabulary._
- **P1 [local→candidate global] Penalty marker reads as earnings, not a debt.** *What:* red `badge-penalty` "+$15" sits beside the projected-earnings column; "+$" parses as money gained. *Why:* in a money game, "owe $15" vs "earned $15" is trust-breaking. *Fix:* label explicitly (`Penalty +$15` / minus glyph) and/or move out of the earnings-adjacent slot; the `title` is hover-only (absent on mobile). → `/clarify`. _Shared component (`badge-penalty`) → likely global._
- **P1 [local] No "as-of" timestamp on a live projected board.** *What:* "projections, updated Monday" says *that* but never *when last updated*; no auto-refresh. *Why:* glanceable-first + ledger-trust demand freshness certainty on a Sunday. *Fix:* "Projected as of {{ last_sync }} CT" in the In Progress banner; consider soft refresh. → `/harden` (live-data states).
- **P2 [local] Mobile loses the backup-WD explanation desktop has.** *What:* desktop 🔄 has a tooltip ("{primary} WD — backup activated"); the mobile card (index.html:166-167) has 🔄 with no tooltip/label. *Why:* phone is primary yet gets the weaker explanation of the most confusing state. *Fix:* render backup state as visible text on mobile (e.g. "↳ replaces {primary}"). → `/adapt`.
- **P2 [local] No next-pick deadline / front door during an active tournament.** *What:* when a tournament is `active`, the upcoming-pick CTA is suppressed; page shows no deadline and no path to next week's pick. *Why:* breaks "two equal front doors" — a member opening to lock a golfer has no thread. *Fix:* keep a lightweight "Next pick: {tournament} · deadline {time}" line/CTA visible during active play when an upcoming tournament with a field exists. → `/onboard` / `/layout`.

**Persona red flags:**
- *Alex (power user):* no locate-rival / jump-to-self / sort / filter (wants "who still has skin in the U.S. Open"); 11/19 "No Pick" rows dilute the 8 live ones; the live-projection watcher is exactly who distrusts a no-timestamp board.
- *Casual member, phone, sunlight:* the muted score-to-par greys ("(-10)", "(+2)", "No Pick") are the lowest-contrast tokens and wash out first ([G1]); hits 🔄/CUT/DQ/+$15 with no key and no tappable explanation (tooltips hover-only); opens to "lock this week's golfer" and finds no deadline/pick button in the active state.

**Minor observations:** two rank vocabularies (desktop medals 🏆🥈🥉 vs mobile mint/gold `.rank-badge`); **dead CSS** — `.row-leader` / `.row-active-tournament` / `.row-complete` are defined but the desktop `<tr>` only ever gets `.row-current-user`, so the leader mint-wash and active-row blue never render on desktop (missing class binding or dead rules); inline `style="…"` on the est-purse badge + standings subtitle (index.html:10,45,371) bypasses tokens; long display names wrap and desync row-height/baseline.

**Questions:** (1) During a live major should the hero flip to "your pick + your projected money + next deadline," with full standings one tap below? (2) If a member can't tell whether `+$15` is won or owed, is the ledger *metaphor* honored or just the ledger *aesthetic*? (3) Is "honest about projection category but silent about freshness" enough to keep Sunday trust? (4) Are 11 "No Pick" rows information or noise — should active state lead with who's actually playing? (5) Should any explanation that exists only on hover be considered missing, given a mostly-phone audience?

**Detector raw (Assessment B, home-scoped from `/`):** `skipped-heading` h2 "Season Standings" → h5 "League Rules" (missing h3/h4 — add a visually-styled but correctly-leveled sidebar heading or aria); `layout-transition` `transition: width` on `.progress-bar` (style.css:526 — Season Progress bar; animate `transform`/`grid-template` instead, minor perf); muted-grey contrast → **[G1]**.

## Deferred prioritization & fix campaign

_Filled at consolidation (Session F)._
