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
- [x] 3. Make a pick (make_pick.html)
- [x] 4. Tournament detail (tournament_detail.html)
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
| 3 | make_pick.html | 28/40 | Not AI slop | 0 |
| 4 | tournament_detail.html | 25/40 | Not AI slop | 1 |

## Global issues (recur across pages → fix-campaign Phase 1)

These trace to `base.html` / design tokens / `style.css` and therefore recur on every page. Units 2–10 should reference these by id rather than re-reporting.

- **[G1] Low-contrast global color tokens fail WCAG AA.** `--text-muted: #8b95a2` computes **2.7–3.0:1** on the cream/white/mint backgrounds; gold accents `--gold-500: #b8993e` compute **2.7:1** on white. Also confirmed on tournament_detail: the **major-multiplier alert text + "You" badge** (gold-deep on gold-wash) at **4.07:1** and the warning-alert gold `#92722a` at **4.1:1** — both just under the 4.5:1 AA threshold for normal text, on the page's most important brand message ("multiplied by 1.5×"). Used pervasively (nav subtext, footer, every `.text-muted`, gold links/`.text-gold`, points chip ~3.48:1, admin badge ~4.16:1). Detector flagged 12 instances on `/`, 20 on `/tournament/23`. _Source: `style.css:21` (`--gold-500`), `:33` (`--text-muted`), alert at `:481-486`. Fix at the token level → propagates. P1._
- **[G2] Keyboard focus ring uses Bootstrap default status-blue.** `:focus` shows `rgba(13,110,253,0.25)` blue glow on nav/links/buttons — violates the design system's role-locked "blue = tournament status only" rule and is low-contrast on the pine-green nav. Define a brand `:focus-visible` ring (gold/paper). Applies to all focusable chrome on every page. P1.
- **[G3] No skip-to-content link; `<nav>` and `<main>` lack landmarks/ids.** No skip link, `<nav>` has no `aria-label`, `<main>` has no `id`. Keyboard/SR users tab through the full nav on every page. PRODUCT.md commits to WCAG 2.1 AA. P2.
- **[G4] No active-nav / `aria-current` state.** The nav never marks the current section (`.nav-link.active` style exists in CSS but is unused). Forces working memory on every page; breaks Visibility-of-System-Status site-wide. P1.
- **[G5] Heading-level skips (card-header `<h5>` after the page `<h2>`/`<h3>`).** Confirmed on home (h2 "Season Standings" → h5 "League Rules") and tournament_detail (h3 "U.S. Open" → h5 "Current Picks & Standings"). Card headers hardcode `<h5>` regardless of document depth, breaking the SR outline. Detector `skipped-heading` on both pages. _Fix the shared card-header heading level (or set levels contextually). P2._
- **[G6] Penalty marker "+$15" reads as a gain, not a debt.** Confirmed on home (Unit 2) and tournament_detail (Unit 4): the shared `.badge-penalty` renders a red `+$15` adjacent to/around earnings; the `+` connotes winnings in a money context. The conceptual ambiguity (owe vs earn) recurs wherever penalties show (home, tournament_detail, and likely my_picks + admin/payments). _Fix the shared component framing: "Penalty $15" / "Owes $15" / debit styling. P1._

**Watch-list (candidate globals — confirm on later units before promoting):** `#fff` hardcoded in `.badge-status-*` / `.badge-cut` / `.badge-dq` etc. (violates DESIGN No-Pure-White rule, code-level); the "est." purse badge uses Bootstrap `bg-secondary` cool-gray (Status-Is-Cool drift, off-palette) on home/make_pick/tournament_detail; purse figures rendered in body sans rather than the gold/serif "Money-Is-Gold" register; rendered `&mdash;` em dashes in copy (skill/DESIGN copy rule). Several rank/standings tables reuse `loop.index` as "rank".

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

### Unit 3 — Make a pick (make_pick.html)

**Scope:** the pick-submission experience only — Tom Select primary/backup golfer dropdowns (search, formatting, touch), deadline clarity, used-player lockout communication, primary-vs-backup model, WD/backup rules messaging, "Available Golfers" count, confirm/submit/cancel + the same-player JS `alert()`. (Shell = Unit 1.)
**Rendered:** `http://127.0.0.1:5001/pick/20` (Charles Schwab Challenge, upcoming/picks-open, deadline Thu May 28 07:00 CT) logged in as admin. Seeded a 60-player field + deadline; admin's 18 used players reduce the list to **56 available** (lockout via exclusion). Assessment A = isolated sub-agent (`[LLM]` tab; interacted with the Tom Select dropdown + phone width). **Assessment B limitation:** `/pick/20` is `@login_required`, so the anonymous URL-mode detector only reaches the login redirect; the file scan returns `[]` (Jinja template). Deterministic detector contributed nothing here — findings rest on Assessment A's authenticated DOM inspection + the `[Human]` screenshot. (This limitation applies to all 6 login/admin pages: make_pick, my_picks, change_password, admin/*.)

**Nielsen scorecard: 28/40 (Good, lower band)**

| # | Heuristic | /4 | Key issue |
|---|-----------|----|-----------|
| 1 | Visibility of system status | 3 | No inline "pick saved/locked" state; deadline is a static timestamp (no countdown) |
| 2 | Match real world | 3 | "Last, First" inverts how fans name golfers; "WD" jargon unglossed |
| 3 | User control & freedom | 3 | Same-player error force-clears backup instead of letting user correct |
| 4 | Consistency & standards | 3 | Native `alert()` validation clashes with the otherwise inline branded form |
| 5 | Error prevention | 2 | Same-player conflict is allowed then alerted, not prevented; no confirm before locking |
| 6 | Recognition vs recall | 2 | Used-player lockout is silent omission — forces recall of who's been used |
| 7 | Flexibility & efficiency | 3 | Type-to-search works, but punctuated names ("jj" vs "J.J.") fail |
| 8 | Aesthetic & minimalist | 4 | Exemplary restraint — two fields, quiet rules card, a count |
| 9 | Error recovery | 2 | Lone error path is a blunt `alert()` that wipes the field; server validation not surfaced |
| 10 | Help & documentation | 3 | Pick Rules sidebar is good but below the fold on mobile |

**Anti-patterns verdict:** **Not AI slop.** Clears all bans (no side-stripes — CSS comment documents the deliberate avoidance; no gradient text/glassmorphism/hero-tiles/card-grid; no modal). Recognizably Greenside Ledger (Augusta-green header, serif title, gold rules card, role-locked color; Tom Select highlight uses Mint Wash `--green-100` per DESIGN). Detector: n/a (login-required — see limitation above).

**Overall impression:** Clean, on-brand, low-load form. The drag is **error prevention/recovery** (the native `alert()` crutch) and **recognition** (the invisible used-player rule) — plus a thin, unconfirmed submit moment for what is a real-money, once-per-season lock.

**Priority issues** (each with suggested impeccable command):

- **P1 [local] Same-player conflict uses a native `alert()` that wipes the field, not prevention.** *What:* the chosen primary stays selectable as backup; picking them fires `window.alert(...)` and clears the backup (make_pick.html:128-145). *Why:* error-prevention failure dressed as handling; the OS popup shatters the clubhouse tone and destroys the user's selection. *Fix:* filter the chosen primary out of the backup Tom Select options live (collision becomes impossible); if a guard remains, inline branded helper text, never `alert()`, and don't clear. → `/harden` (validation) + `/polish`.
- **P2 [local→candidate global] Used-player lockout communicated only by silent omission.** *What:* used golfers are simply absent; no "X used this season" context, no used-roster, no per-row "used" treatment. *Why:* PRODUCT demands "an unambiguous picture of who is available" + "subtle rules → obvious state"; silent omission forces recall and can read as a bug. *Fix:* a cue near the count ("56 available · 18 used this season") and/or a collapsible "players you've used" list. → `/clarify`. _Candidate global with Unit 5 (my_picks) — the season-usage model surfaces there too._
- **P3 [local] No submit confirmation / locked-in reassurance.** *What:* "Submit Pick" posts immediately, redirects away, no on-screen success ceremony. *Why:* the money moment of the app; a fat-finger phone submit on a once-per-season lock deserves certainty ("Your pick is in — editable until Thu 7:00 AM CT"). *Fix:* echo deadline + "you can still edit" at the submit affordance and a branded post-submit success state. **Avoid a modal** (ban) — use an inline confirmation summary. → `/onboard` / `/harden`.
- **P2 [local] Plain-letter search fails for punctuated names.** *What:* typing `jj` returns nothing; only `J.J.` (with periods) matches Spaun. *Why:* no one types periods on a phone; a "no results" for an available player reads as "taken/used," undermining trust. *Fix:* normalize search (strip periods, nickname/first-name matching via Tom Select `searchField`/custom score). → `/harden`.
- **P3 [local] Pick Rules + Available count below the fold on mobile.** *What:* on 390px they stack beneath Submit/Cancel. *Why:* the casual/first-timer needs the WD/backup rule + available context exactly while deciding, on the phone. *Fix:* hoist a condensed "X available · backup activates only if primary WDs before R2" line under the field labels on small screens. → `/adapt`.

**Persona red flags:**
- *Casual member, phone, sunlight:* **no decision support** in a flat 56-name list (no notable players / odds / tee-time ordering) → random-pick / abandonment risk; punctuated-name search dead-ends read as "unavailable" in glare; the `alert()` hijacks a distracted thumb and deletes the backup; no locked-in confirmation after a tab-switch. Positive: 48px targets, full-width buttons, bold glanceable deadline/purse.
- *Alex (power user):* thinks in first names/nicknames — last-name-first + no nickname match + punctuation gap slow the expert path; `alert()` interrupts the keyboard flow and clears a field; **no at-a-glance "who I've already used" ledger** on the pick screen (must leave to My Picks) — removes the exact info the once-per-golfer strategist optimizes around; no inline tee-time/odds context forces a tab switch.

**Minor observations:** selected single Tom Select value has no clear-"X" affordance (reopen to change); "Purse: $9,900,000" is body sans, not the serif/gold "Money-Is-Gold" register on a money screen (_candidate global — recurs on tournament_detail header_); 5-item rules list slightly exceeds the ≤4 chunk; "WD" unglossed; empty-submit relies on native `required` tooltip; static deadline could carry a relative cue ("in 2 days") without sportsbook urgency. The helper sub-labels use muted small text → **[G1]**.

**Questions:** (1) If "unambiguous picture of who is available" is a promise, why is the *used* pool invisible? (2) For a once-per-season real-money lock, is *no* confirmation right, or have we conflated "avoid modals" with "avoid all ceremony"? (3) Is the pick form actually a *front door*, or a form that assumes you already decided elsewhere (zero signal of who's good among 56)? (4) Why does the only validation use the one interaction guaranteed to feel un-designed (`alert()`)? (5) On a phone, the rules sit below the submit button — which user does that serve?

**Detector raw (Assessment B):** file scan `templates/make_pick.html` → `[]` (Jinja template, no computed CSS); URL `/pick/20` → login redirect (anonymous), 1× `ai-color-palette` = the green-gradient **false positive** on the login nav, not make_pick. No usable deterministic signal for this page.

### Unit 4 — Tournament detail (tournament_detail.html)

**Scope:** the picks "leaderboard"/standings (desktop table + mobile card list), earnings-as-ledger (projected vs earned badges), status pills (Active/Major), 1.5× communication, missed-cut **penalty** visibility & legibility, backup-activation, stat cards, projection/last-synced honesty, the legend, the `#` ranking, and no-pick states. (Shell = Unit 1.) **This is the money/trust surface.**
**Rendered:** `http://127.0.0.1:5001/tournament/23` (in-progress **major** U.S. Open, active) — public route, so the URL detector works. Assessment A = isolated sub-agent (`[LLM]` tab, desktop + phone). Assessment B = `detect --json /tournament/23` (24 findings) + `[Human]` desktop & mobile screenshots. **Two findings verified empirically by the parent** via `querySelectorAll` (see P0/P1).

**Nielsen scorecard: 25/40 (Acceptable — lowest unit so far)**

| # | Heuristic | /4 | Key issue |
|---|-----------|----|-----------|
| 1 | Visibility of system status | 3 | Excellent "projections/last-synced" honesty; but projected-vs-final is signaled by badge color only — and that color is wrong on mobile |
| 2 | Match real world | 3 | $ ledger language lands; "+$15" reads like a gain, not a debt ([G6]) |
| 3 | User control & freedom | 3 | Breadcrumb + Back exits; no jump-to-my-row in 19 rows |
| 4 | Consistency & standards | 1 | **Desktop/mobile disagree on money facts**: projected renders gold (desktop) vs green/"settled" (mobile); penalty shows on mobile but not desktop; active-$0 shows "$0" desktop vs "—" mobile |
| 5 | Error prevention | 3 | Read-only; ambiguous "+$15" invites misread |
| 6 | Recognition vs recall | 2 | Legend is at the very bottom after 19 rows; desktop legend promises a penalty symbol the desktop table never renders |
| 7 | Flexibility & efficiency | 2 | No sort/filter/jump-to-me; can't collapse 13 no-pick rows |
| 8 | Aesthetic & minimalist | 2 | 13/19 rows are "No Pick / – / $0" filler at full weight, burying the 8 real picks + leader |
| 9 | Error recovery | 3 | Graceful sync-pending fallback; little error surface |
| 10 | Help & documentation | 3 | Legend + major/projection alerts are real inline help; placement + phantom desktop penalty symbol cost a point |

**Anti-patterns verdict:** **Not AI slop** (no side-stripes, gradient text, glassmorphism, modal; green header/nav gradients intentional). Weakest block = the three equal stat cards (closest to a hero-metric template, survives on serif-ledger treatment). Code-level DESIGN drifts: `#fff` hardcoded in several badges (No-Pure-White), "est." badge uses Bootstrap gray `bg-secondary` (Status-Is-Cool drift) → see watch-list. Detector: 20× low-contrast ([G1]), 3× `ai-color-palette` (green brand gradients — **false positives**, incl. the inline header gradient), 1× `skipped-heading` h3→h5 ([G5]).

**Overall impression:** On-brand and, on desktop, genuinely ceremonial (gold leader row, 🏆, serif money). But as the **trust surface it has real correctness gaps**: the live penalty is hidden on desktop, projected money looks "banked" on mobile, and rank numbering misleads. The projection-honesty copy is the best single element in the whole sweep so far.

**Priority issues** (each with suggested impeccable command):

- **P0 [local] Desktop table never shows the live missed-cut penalty.** *What:* `+$15` renders on mobile cards and in the desktop **legend** but on **zero desktop rows** — verified: `.desktop-table .badge-penalty` = **0** vs `.mobile-card-list .badge-penalty` = **2**. Root cause: desktop badge is gated on `result.penalty_triggered and result.active_is_primary/active_is_backup` (tournament_detail.html:287-289, 310-312), but `active_player_id` is null for un-finalized live majors, so both flags are false; mobile (`:211`) gates on `penalty_triggered` alone. *Why:* on the money/trust surface the admin runs from desktop, a $15 obligation the main layout silently hides — while the legend advertises it — is the most trust-destroying failure possible. *Fix:* render the desktop penalty badge on `result.penalty_triggered` (drop/repair the `active_is_*` gate for live state), matching mobile. **Logic bug, not just visual** → fix-campaign, not a styling pass. → `/harden`.
- **P1 [local] Projected earnings render as "settled green" on mobile.** *What:* verified — desktop `.badge-earnings-projected` (gold) ×6, mobile `.badge-earnings` (green/final) ×6 for the same live rows (tournament_detail.html:187-195). *Why:* phones are primary; gold-vs-green "is this final?" is a core ledger principle — mobile users can't tell projected from banked and could screenshot "$2.8M green" as won. *Fix:* branch the mobile badge on `tournament.status` to match desktop. → `/harden` / `/adapt`.
- **P1 [local] Ranking is broken below paying positions.** *What:* `#` = `loop.index` over a list including 13 no-pick rows, so a $0 DQ pick is "#8" and a CUT pick "#19" with gaps, while $0 non-pickers occupy #7/#9-18. *Why:* a rank that misorders $0 rows erodes trust in the numbers on a standings table. *Fix:* rank only rows with a pick by earnings (shared ties); push no-pick rows below a divider / into a collapsed group; never let `loop.index` double as rank. → `/layout`.
- **P1 [global G6] "+$15" reads as a gain, not a debt** (shared `badge-penalty`; also on home). *Fix:* debit framing "Owes $15" / "Penalty $15", keep red, drop the bare `+`. → `/clarify`.
- **P2 [local] 13 empty no-pick rows bury the 8 real picks + leader.** *What:* >⅔ of the table is "No Pick / – / $0" at full visual weight, pushing real content below the fold both breakpoints. *Why:* violates glanceable-first + minimalist. *Fix:* collapse non-pickers into a muted "Didn't pick (13): …" line/toggle. → `/distill` / `/layout`.
- **P3 [global G1] Major-multiplier alert + "You" badge at 4.07:1** (gold-deep on gold-wash) — under AA on the key 1.5× message. *Fix:* darken text / deepen wash; reconsider "You" reusing gold `badge-major` (collides identity with the money/major register). → `/audit`.

**Persona red flags:**
- *Alex (power user, desktop):* no sort/filter/jump-to-me over 19 rows (13 noise); will spot the **missing desktop penalty** (in legend, not table) and read it as a bug; rank putting a $0 DQ at #8 reads as plainly wrong.
- *Casual member, phone, sunlight:* sees projected $2.8M in a **green "final" badge** → may think it's banked (the exact doubt the product exists to prevent); must thumb-scroll past ~15 cards to the bottom legend to decode 🔄/DQ; own "+$15" CUT reads as a bonus; three stacked stat cards eat the first mobile screen before any standing shows.

**Minor observations:** active-$0 shows "$0" (desktop) vs "—" (mobile) — pick one; mobile rank sequence jumps 6→8→19 with gaps (omitted badge but counted index); legend below table on both breakpoints (consider above-table or touch-discoverable tooltips — `title=` exists on desktop only); "est." badge Bootstrap gray off-palette; `#fff` hardcodes (No-Pure-White); rendered `&mdash;` em dash in the In-Progress copy (copy rule); stat-card trio is the most generic block (consider folding "Current Leader" into the table). _Code refs from sub-agent: template 187-195, 287-289/310-312, 179/259-264; CSS 285-300, 383-391, 481-486, `#fff` at 304/313/321/366/379._

**Questions:** (1) If desktop can hide a $15 debt while the legend advertises it, which surface does the admin trust when settling the pot? (2) Should a non-picker occupy a numbered standings row at all? (3) Is hue alone enough for projected-vs-final on a phone in sunlight (especially when it's the wrong hue)? (4) For a "well-run clubhouse" voice, should the page end on its most painful row (a CUT that owes money)? (5) In a ledger, debits are negative — why is a debt rendered with a `+`?

**Detector raw (Assessment B, `/tournament/23`, 24 findings):** 20× low-contrast (`#8b95a2` muted + gold `#92722a` 4.1:1 → **[G1]**); 3× `ai-color-palette` "Cyan gradient" (navbar + footer + inline header green gradients → **false positives**); 1× `skipped-heading` h3→h5 (→ **[G5]**).

## Deferred prioritization & fix campaign

_Filled at consolidation (Session F)._
