---
name: Golf Pick 'Em
description: The Greenside Ledger. A heritage-golf clubhouse system where earnings read with the gravity of a financial ledger.
colors:
  pinehurst-pine: "#006747"
  pine-shadow: "#005c3f"
  pine-deep: "#00432e"
  fairway-green: "#007a54"
  meadow-green: "#1a8a6a"
  sage: "#4da88a"
  mint-wash: "#e8f5ef"
  mint-tint: "#f0faf5"
  clubhouse-gold: "#b8993e"
  gold-deep: "#92722a"
  gold-light: "#c4a747"
  gold-soft: "#d4be6a"
  gold-wash: "#faf3e0"
  azalea-deep: "#9d3558"
  azalea: "#b34a6b"
  azalea-wash: "#fbeef2"
  azalea-tint: "#fdf5f8"
  cream: "#faf8f4"
  white: "#ffffff"
  ink: "#1a1f25"
  slate: "#4a5568"
  stone: "#8b95a2"
  paper-on-dark: "#f7f8f9"
  live-blue: "#2563eb"
  complete-gray: "#6b7280"
  danger-red: "#b91c1c"
  warning-amber: "#d97706"
typography:
  display:
    fontFamily: "DM Serif Display, Georgia, serif"
    fontSize: "5rem"
    fontWeight: 400
    lineHeight: 1
    letterSpacing: "-0.01em"
  headline:
    fontFamily: "DM Serif Display, Georgia, serif"
    fontSize: "1.75rem"
    fontWeight: 400
    lineHeight: 1.1
    letterSpacing: "-0.01em"
  title:
    fontFamily: "DM Serif Display, Georgia, serif"
    fontSize: "1.4rem"
    fontWeight: 400
    lineHeight: 1.15
    letterSpacing: "-0.01em"
  body:
    fontFamily: "Plus Jakarta Sans, system-ui, -apple-system, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "Plus Jakarta Sans, system-ui, sans-serif"
    fontSize: "0.8rem"
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: "0.05em"
rounded:
  sm: "6px"
  md: "10px"
  lg: "14px"
components:
  button-primary:
    backgroundColor: "{colors.pinehurst-pine}"
    textColor: "{colors.paper-on-dark}"
    rounded: "{rounded.sm}"
    typography: "{typography.label}"
  button-primary-hover:
    backgroundColor: "{colors.fairway-green}"
    textColor: "{colors.paper-on-dark}"
  button-outline:
    textColor: "{colors.pinehurst-pine}"
    rounded: "{rounded.sm}"
  button-gold:
    backgroundColor: "{colors.clubhouse-gold}"
    textColor: "{colors.pine-deep}"
    rounded: "{rounded.sm}"
  card:
    backgroundColor: "{colors.white}"
    rounded: "{rounded.md}"
  card-header-green:
    backgroundColor: "{colors.pinehurst-pine}"
    textColor: "{colors.paper-on-dark}"
  table-header:
    backgroundColor: "{colors.pine-shadow}"
    textColor: "{colors.paper-on-dark}"
    typography: "{typography.label}"
  badge-earnings:
    backgroundColor: "{colors.pinehurst-pine}"
    textColor: "{colors.paper-on-dark}"
    rounded: "{rounded.sm}"
  badge-earnings-projected:
    backgroundColor: "{colors.gold-light}"
    textColor: "{colors.pine-deep}"
    rounded: "{rounded.sm}"
  badge-major:
    backgroundColor: "{colors.azalea-wash}"
    textColor: "{colors.azalea-deep}"
    rounded: "{rounded.sm}"
  stat-card:
    backgroundColor: "{colors.white}"
    rounded: "{rounded.md}"
---

# Design System: Golf Pick 'Em

## 1. Overview

**Creative North Star: "The Greenside Ledger"**

This is a heritage-golf clubhouse rendered as software. Deep Augusta-adjacent greens carry the structure (nav, table headers, primary actions), warm gold marks the money and the rank (earnings, the leader, the points total), Augusta azalea marks the four majors, and everything sits on a soft cream paper. The serif display face gives section headings the weight of a printed scorecard, while a humanist sans keeps the dense earnings data legible at a glance on a phone. The defining tension: this is a money game, and the numbers are real dollars, so the system treats every earnings figure with the gravity of a financial ledger rather than the flash of a betting slate.

The mood is confident and a little ceremonial, never loud. Surfaces rest nearly flat, lifting only in response to a hover or a state change. Color is deployed by role, not for decoration: green is the institution, gold is the reward, azalea is the majors, and the blues and grays are reserved strictly for live and completed status. Restraint is the point. The data is the hero; the chrome stays out of its way.

This system explicitly rejects the **generic SaaS dashboard** (cream-and-blue startup template, hero-metric tiles, identical icon-and-heading card grids, anything that reads as "an AI made this") and the **corporate enterprise tool** (cold, dense, gray admin-panel feel with no warmth). Even admin surfaces keep the clubhouse character. Sportsbook loudness (neon odds, flashing promos, gamble-y urgency) is kept out by reflex.

**Key Characteristics:**
- Augusta-inspired green structure, warm gold reward accents, cream paper ground
- Serif display headings (DM Serif Display) over humanist sans body (Plus Jakarta Sans)
- Flat at rest, soft green-tinted lift on hover
- Money and rank read in the gold register; majors read in azalea; status reads in blue/gray
- Glanceable on a phone, in sunlight, mid-banter

## 2. Colors

A warm, course-derived palette: institutional greens, celebratory golds, and a cream paper ground, with cool blue/gray reserved exclusively for tournament status.

### Primary
- **Pinehurst Pine** (#006747): The brand anchor. Primary buttons, links, table-header accents, earnings badges, the upcoming-status marker. The single color most associated with the app's identity.
- **Pine Shadow** (#005c3f): Deeper structural green for leaderboard table headers and secondary card headers.
- **Pine Deep** (#00432e): The darkest green. Footer ground, navbar gradient origin, and text laid on gold surfaces. Anchors the bottom of every shadow tint.
- **Fairway Green** (#007a54) and **Meadow Green** (#1a8a6a): Mid-greens for primary-button hover and brighter interactive states.
- **Sage** (#4da88a): The lightest functional green, used for input focus borders.
- **Mint Wash** (#e8f5ef) and **Mint Tint** (#f0faf5): Pale green fills for rank badges, open-status pills, zebra striping (Tint), table row hover (Wash), and sidebar panel grounds — the second neutral layer.

### Secondary
- **Clubhouse Gold** (#b8993e): The reward accent. Admin badge, gold buttons, the gold-button family. Reserved for things of value.
- **Gold Deep** (#92722a): Gold text on pale gold surfaces (withdrawal badges, locked status), and the locked-status marker.
- **Gold Light** (#c4a747): Projected (not-yet-final) earnings badges. The signal for "live money, not settled."
- **Gold Soft** (#d4be6a): The points figure in the navbar and footer links on dark green.
- **Gold Wash** (#faf3e0): Pale gold fill behind the current-user row highlight, the Pick of the Season feature, and locked-status pills.

### Azalea (the majors)
- **Azalea Deep** (#9d3558): Azalea text on the wash and on white (6.8:1 / 6.0:1, AA+). Major badges and the major stakes line.
- **Azalea** (#b34a6b): The fill grade; carries white text at 5.1:1 when a solid azalea surface is needed.
- **Azalea Wash** (#fbeef2) and **Azalea Tint** (#fdf5f8): Pale rose fills behind major badges and the masthead stakes band on major weeks.

### Neutral
- **Cream** (#faf8f4): The page ground. Every screen sits on this warm off-white, never pure white.
- **White** (#ffffff): Card and table surfaces, lifted one step above the cream ground.
- **Ink** (#1a1f25): Primary text. A near-black tinted warm, never pure #000.
- **Slate** (#4a5568): Secondary text, muted card headers.
- **Stone** (#8b95a2): Muted text, stat-card labels, legends, timestamps.
- **Paper on Dark** (#f7f8f9): Text and icons on green and gold surfaces.

### Status (cool, reserved)
- **Live Blue** (#2563eb): Active-tournament status only. Live/in-progress rows, info alerts, team-event badges. Never decorative.
- **Complete Gray** (#6b7280): Completed-tournament status.
- **Danger Red** (#b91c1c): Cut/DQ badges, missed-cut penalty markers, error alerts.
- **Warning Amber** (#d97706): Reserved warning semantic.

### Named Rules
**The Money-Is-Gold Rule.** Gold is reserved for money and rank: the leader, the user's own points total, projected and final earnings. It never appears as generic decoration. When you see gold, money or standing is involved.

**The Azalea-Is-Majors Rule.** Azalea (Augusta rose) belongs exclusively to the four major championships: major badges, the 1.5x/penalty stakes band, and major-week accents. It never marks anything else, and majors never borrow gold; the two stakes (money vs. the majors' multiplier-and-penalty week) stay visually distinct.

**The Status-Is-Cool Rule.** Blue and gray exist only to signal tournament state (live, complete). They are forbidden as accent or decoration. The warm green/gold palette owns everything else.

**The No-Pure-Black, No-Pure-White Rule.** Text is Ink (#1a1f25), grounds are Cream (#faf8f4) and White (#ffffff). Pure #000 and #fff are prohibited.

## 3. Typography

**Display Font:** DM Serif Display (with Georgia, serif fallback)
**Body Font:** Plus Jakarta Sans (with system-ui, -apple-system, sans-serif fallback)

**Character:** A high-contrast serif display paired with a clean humanist sans. The serif lends section headings and big numbers the formality of a printed scorecard or ledger; the sans keeps dense earnings tables and form fields effortlessly legible on a small screen. The pairing reads classic and trusted, never trendy.

### Hierarchy
- **Display** (DM Serif Display, 5rem, line-height 1): Reserved for error-page numerals and the largest ceremonial moments.
- **Headline** (DM Serif Display, 1.75rem, line-height ~1.1, letter-spacing -0.01em): Page titles (h2). The primary screen heading.
- **Title** (DM Serif Display, 1.4rem): Section headings (h3), stat-card values, the navbar brand. Also the voice of any single hero number.
- **Body** (Plus Jakarta Sans, 1rem, weight 400, line-height 1.5): All running text, table cells, form labels. Cap reading-column width at 65–75ch.
- **Label** (Plus Jakarta Sans, 0.8rem, weight 600, letter-spacing 0.05em, UPPERCASE): Table column headers, stat-card labels. The administrative caption voice.

### Named Rules
**The Serif-For-Gravity Rule.** Headings, the brand, and standalone hero numbers (stat-card values, big earnings) use DM Serif Display. It signals that the figure matters. Body and data tables stay in Plus Jakarta Sans for legibility. Never set a long table in the serif.

**The Uppercase-Label Rule.** Small uppercase labels (0.8rem, 0.05em tracking, weight 600) are the only place letter-spacing opens up. Body text never gets tracked.

## 4. Elevation

Flat by default, with a soft lift on interaction. Surfaces rest nearly flush against the cream ground and gain depth only as a response to state. Shadows are deliberately green-tinted (rgba(0, 67, 46, ...)) rather than neutral gray, so elevation feels like it belongs to the palette instead of floating above it. Depth is conveyed as much by the cream-to-white tonal step (page ground to card surface) and hairline green borders as by the shadows themselves.

### Shadow Vocabulary
- **Resting** (`box-shadow: 0 1px 3px rgba(0, 67, 46, 0.08)`): The default for cards and stat cards. Barely there; a whisper of separation from the ground.
- **Lifted** (`box-shadow: 0 4px 12px rgba(0, 67, 46, 0.10)`): Card hover state, dropdown menus, Tom Select dropdowns. The interactive response.
- **Floating** (`box-shadow: 0 8px 24px rgba(0, 67, 46, 0.12)`): The deepest step, reserved for prominent lifted surfaces.

### Named Rules
**The Lift-On-Response Rule.** Cards are flat at rest and rise to Lifted only on hover. Elevation is feedback, not decoration. A card that floats before you touch it is wrong.

**The Green-Tint Rule.** Every shadow is tinted with the brand green (rgba(0, 67, 46, ...)). Neutral gray drop shadows are prohibited; they read as generic SaaS chrome.

## 5. Components

The component feel is **refined and restrained**: quiet, precise, ledger-like. Components carry the structure and step back so the data leads.

### Buttons
- **Shape:** Gently rounded (6px radius, `--radius-sm`). Weight 600.
- **Primary (Greenside):** Pinehurst Pine (#006747) fill, Paper-on-Dark (#f7f8f9) text. The default commit action (submit a pick, save).
- **Hover / Focus:** Brightens to Fairway Green (#007a54) with a soft green glow (`0 2px 8px rgba(0, 103, 71, 0.25)`). Transition on background and shadow only, ~0.15s ease. Never animate layout.
- **Outline (Greenside):** Transparent with a 1.5px Pinehurst Pine border and green text; fills solid green on hover. The secondary action.
- **Gold:** Clubhouse Gold (#b8993e) fill with Pine Deep (#00432e) text. Reserved for special or celebratory actions, never a routine default.

### Cards / Containers
- **Corner Style:** 10px radius (`--radius-md`); the tournament header uses 14px (`--radius-lg`).
- **Background:** White (#ffffff) surface on the Cream (#faf8f4) page ground.
- **Border:** Hairline green, `1px solid rgba(0, 67, 46, 0.08)`.
- **Shadow Strategy:** Resting at rest, Lifted on hover (see Elevation).
- **Headers:** A family of colored header bars. Green (`card-header-green`, Pinehurst Pine) for primary cards, darker (`card-header-dark`, Pine Shadow), Gold (`card-header-gold`, pale gold wash with gold text), and Muted (`card-header-muted`, light gray) for de-emphasized sections. Header text is the serif display face.
- **Internal Padding:** Roughly 0.75rem–1.25rem; vary it for rhythm rather than padding everything identically.

### Tables (Leaderboard, signature surface)
- **Header row:** Pine Shadow (#005c3f) fill, Paper-on-Dark text, uppercase Label type (0.8rem, 0.05em tracking), 2px Pine Deep bottom border.
- **Body rows:** White with Mint Tint (#f0faf5) zebra striping; Mint Wash (#e8f5ef) on hover.
- **Current-user row:** Gold Wash (#faf3e0) fill, marked with a gold rule.
- **Leader row:** Deep mint fill (rgba(26, 138, 106, 0.14)), one step past zebra/hover so the front-runner reads at a glance.
- **State rows:** Active-tournament rows take a visible blue wash (rgba(37, 99, 235, 0.09)); complete rows drop to 85% opacity.

### Badges (the earnings and status vocabulary)
- **Earnings (final):** Pinehurst Pine fill, white text. Settled money.
- **Earnings (projected):** Gold Light (#c4a747) fill, Pine Deep text. Live, not-yet-final money. The gold says "still moving."
- **Major:** Azalea Wash fill, Azalea Deep text, weight 700. Marks a major championship (1.5x multiplier). Major mastheads also carry an azalea stakes band ("Majors pay 1.5x. A missed cut owes $15 to the pot.").
- **Status pills:** Active (Live Blue), Complete (Complete Gray), Upcoming (Pinehurst Pine), Locked (gold wash), Open (mint wash). Cut/DQ in Danger Red, WD in gold wash, Penalty in pale red with weight 700.
- **Rank badge:** A 26px circle, Mint Wash fill with green text; the leader's badge flips to gold wash with gold text.

### Inputs / Fields
- **Style:** Standard stroke with a faint green border (`rgba(0, 67, 46, 0.15)`), 6px radius.
- **Focus:** Border shifts to Sage (#4da88a) with a soft green focus ring (`0 0 0 0.2rem rgba(0, 103, 71, 0.15)`).
- **Tom Select (player picker):** The signature input. On mobile, controls grow to a 48px min-height with 1rem type for comfortable thumb use; the active dropdown option takes a Mint Wash highlight.

### Navigation
- **Style:** A green gradient bar (Pine Deep to Pine Shadow, 135deg) with a soft green shadow. The brand wordmark is the serif display face.
- **Links:** Paper-on-Dark at 80% opacity, brightening to full with a faint white wash on hover/active.
- **Points pill:** The user's season total rides in the nav as a Gold Soft (#d4be6a) figure on a translucent chip; admin gets a Clubhouse Gold badge.
- **Mobile:** Collapses to a toggler; nav links gain taller tap targets and faint dividers.

### Stat Cards (tournament summary)
- Centered, white, hairline green border, 10px radius, Resting shadow. An uppercase Stone (#8b95a2) Label over a serif Pinehurst Pine value (1.75rem). The compact way to show a single number with gravity.

## 6. Do's and Don'ts

### Do:
- **Do** ground every screen on Cream (#faf8f4); lift cards and tables to White (#ffffff).
- **Do** reserve gold for money and rank: the leader, the user's points, and earnings (projected gold, final green). Mark majors in azalea, never gold.
- **Do** set headings and standalone hero numbers in DM Serif Display; keep tables and body in Plus Jakarta Sans.
- **Do** tint every shadow with brand green (rgba(0, 67, 46, ...)) and keep surfaces flat until hover.
- **Do** keep status colors (Live Blue #2563eb, Complete Gray #6b7280) strictly for tournament state.
- **Do** make the one number that matters (rank, active pick, deadline) readable at a glance on a phone in sunlight; hold AA contrast and large tap targets.
- **Do** make pick state unambiguous: backup activation, withdrawals, major 1.5x, and missed-cut penalties must each be plainly legible.

### Don't:
- **Don't** drift into a **generic SaaS dashboard**: no cream-and-blue startup template, no hero-metric tiles, no identical icon-and-heading card grids, nothing that reads as "an AI made this."
- **Don't** drift into a **corporate enterprise tool**: no cold, dense, gray admin-panel feel. Admin surfaces keep the clubhouse warmth.
- **Don't** introduce sportsbook loudness: no neon, no flashing promos, no gamble-y urgency.
- **Don't** use neutral gray drop shadows; they read as generic chrome. Green-tinted only.
- **Don't** use pure #000 or pure #fff anywhere. Ink and Cream/White instead.
- **Don't** use a colored side-stripe (border-left greater than 1px) as a decorative accent; if a row or card needs marking, use a full hairline border or a background tint.
- **Don't** apply gold as a generic accent or blue/gray as decoration; both are role-locked.
- **Don't** set long data tables in the serif display face; legibility wins.
- **Don't** float cards before interaction; elevation is a response, not a resting state.
