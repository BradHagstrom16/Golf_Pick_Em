# Golf Pick 'Em — Full UI/Design Upgrade

## Context

Golf Pick 'Em is live mid-season with ~19 active members. The frontend works, but it looks like what it is: default Bootstrap with green headers. This task is a **design-forward upgrade** — not a feature build, not a refactor. The goal is to make the site look like something a designer built for a golf fantasy league, not something a developer scaffolded in a weekend.

Success = a league member opens the site on their phone during a tournament and thinks "damn, this looks good." The data surfaces (standings, tournament results, pick history) should be the visual highlight — they're what people stare at all week.

Brad wants **golf green as the primary color**, but that doesn't mean "Bootstrap `bg-success` everywhere." It means a thoughtful golf green palette with depth, contrast, and personality.

**Preferably no Python files are touched in this task.** Ideally this is CSS, HTML templates, and possibly JS only.

---

## Step 0: Activate Skills (Do This First)

Before reading any project files, load and internalize these two skills — they are the backbone of this task:

1. **Read and activate the `frontend-design` skill** — This must genuinely shape your aesthetic decisions and be utilized through this entire process from the planning to the execution and code changes. Do not read it and then produce generic Bootstrap. The skill demands bold, intentional design with distinctive typography, purposeful color, and spatial composition. Follow it.
2. **Activate `superpowers`** — Use advanced capabilities for thorough multi-file analysis and high-quality output.

These aren't optional enrichment. The entire point of running this through Claude Code is to leverage these skills. If the output looks like it could have been produced without them, the task has failed. While the instructions in this file exist and are sound, frontend-design is the trump card, what it reviews and says goes.

---

## Step 1: Audit Phase (Before Any Changes)

**Start in Plan Mode.** Do not write any code until Brad approves the plan.

### 1a. Catalog the frontend

Find every file in `templates/` and `static/`. Then read each of these files completely:

- `static/css/style.css`
- `templates/base.html`
- `templates/index.html` (standings — the most important page)
- `templates/tournament_detail.html` (active/complete tournament results)
- `templates/make_pick.html` (pick submission with Tom Select dropdowns)
- `templates/my_picks.html` (user's season pick history)
- `templates/schedule.html` (tournament calendar)
- `templates/login.html` and `templates/register.html`
- `templates/errors/404.html` and `templates/errors/500.html`
- Any admin templates in `templates/admin/`

### 1b. Produce a written audit

Before proposing any changes, write a summary covering:

- **Current color palette**: What colors are actually in use (CSS classes, inline styles, Bootstrap utilities)?
- **Typography**: What fonts are loaded? What's the type hierarchy?
- **Layout patterns**: How is the grid used? What's the mobile strategy (dual-render cards vs. tables, breakpoints)?
- **Component reuse**: What patterns repeat across templates? What's inconsistent?
- **Data display quality**: How do standings, leaderboard rows, and pick cards present information? What's cluttered? What's hard to scan?
- **Mobile pain points**: What breaks or degrades on small screens? Where are touch targets too small?
- **Brand identity**: What currently says "golf" or "fantasy league" beyond the ⛳ emoji? (Answer: almost nothing.)

---

## Step 2: Design Direction Decision

Still in Plan Mode. Based on the audit and the `frontend-design` skill, commit to a specific aesthetic direction.

### Required decisions:

1. **Name the aesthetic** — Give it a clear label. Examples of the caliber expected (don't need to use these verbatim, find what's right for a golf fantasy app):
   - "Augusta Editorial" — clean, premium, magazine-like data presentation with golf course greens and cream
   - "Fairway Data Utility" — modern sports data app aesthetic, dense but readable, dark mode with green accents
   - "Links Club" — warm, textured, classic club feel with serif headlines and rich greens

2. **Define the color palette** as CSS custom properties:
   - Primary green (and 2-3 shades/tints)
   - Background color(s)
   - Text colors (primary, secondary, muted)
   - Accent color (for CTAs, highlights, active states)
   - Status colors (for tournament states: upcoming/active/complete)
   - Data emphasis colors (for earnings, rankings, badges)

3. **Typography pairing**:
   - Display/heading font (Google Fonts CDN?)
   - Body/data font (Google Fonts CDN?)
   - Rationale for the pairing

**checkpoint** Present the audit and design direction to Brad for approval before implementing.

---

## Step 3: Implementation Scope

Once Brad approves the direction and plan, implement changes across these files. For each file, the goal and constraints are listed.

### `static/css/style.css` — Primary Target
- Can replace the current minimal overrides with a cohesive, purposeful stylesheet
- Define all CSS custom properties at `:root`
- Override Bootstrap defaults where they conflict with the design direction
- Mobile-first media queries
- Custom component classes for standings rows, pick cards, tournament headers, status badges
- No leftover dead CSS from the current file

### `templates/base.html` — Global Shell
- Import Google Fonts in `<head>`
- Redesign the navbar (currently: flat `bg-success` bar with default Bootstrap nav)
  - Should feel like a proper app header, not a Bootstrap example
  - Mobile hamburger behavior must remain functional
- Redesign the footer (currently: single line of grey text)
- Flash message styling should match the new palette
- The `{% block head %}` and `{% block scripts %}` patterns must remain intact

### `templates/index.html` — Standings (Most Important Page)
- This is the page people see most. The standings table IS the product.
- Desktop standings table: clean, scannable, with clear rank/player/points hierarchy
- The "column divider" pattern between season data and tournament data should be visually distinct but not heavy-handed
- Mobile standings cards: should feel native, not like a table crammed into cards
- Pick CTA banner (upcoming tournament): prominent but not disruptive
- Results tournament banner (active/complete): informative, status-aware
- Sidebar (desktop): pick status card + league rules — should complement, not compete with standings
- The mobile CTA above standings should feel integrated, not bolted on
- Current user's row highlighting (`.table-warning`) should use the new palette

### `templates/tournament_detail.html` — Tournament View
- Tournament header card: should feel like a proper event page, not a Bootstrap card
- Summary stat cards (Picks Submitted / Total Points / Top Earner): these are currently generic `.card.text-center` — make them visually interesting?
- Picks table (active/complete): this is the second most-viewed data surface
  - Desktop: clean table with good information hierarchy
  - Mobile: card list that's easy to scan for "who picked who" and "who's winning"
- Status indicators (active tournament warning, projected vs final earnings) should be clear without being noisy
- The breadcrumb nav should be lightweight

### `templates/make_pick.html` — Pick Submission
- **Critical UX requirement from Brad**: No popup/modal when submitting a pick. The current flow uses Tom Select dropdowns inline — keep this pattern, but make the dropdowns and submit button feel polished. Don't limit the number of golfers that appear in the dropdown, users like to see all available golfers.
- Tom Select styling needs to integrate with the new palette (override the Bootstrap 5 skin)
- Tournament info (dates, purse, deadline) should be clear but secondary to the pick form itself
- The sidebar rules reminder should be visually distinct but unobtrusive
- Mobile: the pick form must be the dominant element, not buried below tournament info

### `templates/my_picks.html` — Pick History
- Mobile cards already exist (dual-render pattern) — can improve their design
- Desktop table: season-long pick history should be scannable
- Status badges (Complete/Active/Locked/Open) should use consistent, palette-aware colors
- Earnings display should be visually prominent for completed tournaments
- The "no pick" state should be clear but not alarming

### `templates/schedule.html` — Tournament Calendar
- Currently likely a simple table or card list of tournaments
- Should feel like a season timeline — past/current/future states visually distinct
- Major championships should stand out
- Quick-scan: a member should be able to glance and know "what's next" and "is a tournament or what tournament is currently going on" and "what have I missed"

### `templates/login.html` and `templates/register.html`
- Simple, centered forms — but styled to match the new design language
- Should feel welcoming, not corporate

### Error pages (`templates/errors/404.html`, `500.html`)
- Brief polish pass — match the new palette and typography
- Keep them simple

### Admin templates (`templates/admin/`)
- Light-touch only — admin pages don't need the full design treatment
- At minimum: update card headers and table styles to use the new palette instead of raw Bootstrap colors
- Do not spend significant time and effort here

---

## Step 4: Mobile-Specific Directives

1. **Navigation**: The collapse/hamburger must work smoothly. When expanded on mobile, the nav should feel intentional, not a dropdown afterthought. Active page indication should be visible.

2. **Data tables on small screens**: The standings (index.html) and picks (tournament_detail.html) tables ideally should not require horizontal scrolling. The existing dual-render pattern (cards on mobile, tables on desktop) is probably the right approach — can improve the card designs, most likely don't revert to responsive tables.

3. **Pick submission on mobile**: The make_pick.html form must be the first thing a user interacts with on mobile. No modals, no popups. The Tom Select dropdowns should be large enough to tap comfortably. The submit button should be prominent and reachable with one thumb.

4. **Touch targets**: All interactive elements (buttons, links, dropdown triggers, nav items) must meet minimum 44px touch target guidelines on mobile.

5. **Spacing**: Mobile views should use generous vertical spacing between cards/sections — don't try to cram desktop density onto a phone.

---

## Step 5: Constraints

- [ ] **Ideally no new Python dependencies** — if any new, Brad needs to be well aware so he can test properly.
- [ ] **No JavaScript build step** — vanilla JS or CDN-loaded libraries only. Tom Select is already CDN-loaded and must remain so.
- [ ] **Bootstrap 5 CDN stays** — it's the layout foundation. Override and extend it as needed, but don't remove it.
- [ ] **Ideally all Jinja2 template logic is untouched** — every `{% if %}`, `{% for %}`, `{{ variable }}`, `{% block %}`, `url_for()` call, form action, and conditional should remain exactly as-is. You're changing the HTML structure and CSS classes AROUND the logic, not the logic itself unless a logic change is absolutely needed.
- [ ] **External fonts via Google Fonts CDN are allowed**
- [ ] **Tom Select**: The Tom Select Bootstrap 5 CSS skin is loaded via CDN. Custom overrides go in `style.css`, not by swapping the CDN link.

---

## Step 6: Suggested Implementation Workflow

After Brad approves the design direction, and with the `frontend-design` skill active and utilized in each phase:

### Phase A: Foundation
1. Build the new `style.css` with CSS custom properties, typography imports, and base component styles
2. Update `base.html` with font imports, redesigned nav, and footer
   → **Run `pyright-lsp`** on any `.py` files if touched
   → **Run `code-review`** on modified template files

### Phase B: Core Data Surfaces
3. Upgrade `index.html` (standings — the crown jewel)
4. Upgrade `tournament_detail.html` (tournament results view)
   → **Run `code-review`** after each template

### Phase C: Supporting Pages
5. Upgrade `make_pick.html` (pick submission flow + Tom Select integration)
6. Upgrade `my_picks.html` (pick history)
7. Upgrade `schedule.html` (tournament calendar)
   → **Run `code-review`** after this batch

### Phase D: Polish
8. Upgrade `login.html`, `register.html`, error pages
9. Light pass on admin templates (palette alignment only)
10. Cross-page consistency review — verify visual language is coherent
    → **Run `coderabbit`** for holistic multi-file analysis
    → **Run `code-simplifier`** on `style.css` to eliminate redundancy

### Phase E: Commit
→ **Run `commit-commands`**: message = `feat: complete UI/design upgrade — [aesthetic name]`

---

## Verification Criteria

The task is complete when:

- [ ] Design direction was named, defined, and approved by Brad before implementation
- [ ] `style.css` is cohesive, uses CSS custom properties, and contains no dead/leftover CSS
- [ ] Google Fonts are loaded and applied consistently
- [ ] Standings page (index.html) is the visual highlight of the site
- [ ] Tournament detail page data surfaces look polished on both desktop and mobile
- [ ] Pick submission (make_pick.html) works without popups/modals, with comfortable mobile touch targets
- [ ] All existing Jinja2 template logic (variables, conditionals, loops, url_for calls) remains 100% functional
- [ ] Nav, footer, flash messages, and error pages are styled consistently
- [ ] The site looks intentionally designed, not like a Bootstrap template with a green coat of paint

---

## Final Note

This is a creative task. The `frontend-design` skill exists specifically to push past safe, generic output. Use it. The league members who use this site are Brad's friends — he wants them to be impressed. Make changes count, and don't just change something for the sake of changing it, there should be reasoning and purpose.
