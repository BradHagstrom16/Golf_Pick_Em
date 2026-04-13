# Graph Report - .  (2026-04-13)

## Corpus Check
- Corpus is ~27,021 words - fits in a single context window. You may not need a graph.

## Summary
- 397 nodes · 920 edges · 39 communities detected
- Extraction: 50% EXTRACTED · 50% INFERRED · 0% AMBIGUOUS · INFERRED: 460 edges (avg confidence: 0.51)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Migration Safety & App Core|Migration Safety & App Core]]
- [[_COMMUNITY_API Sync Utilities|API Sync Utilities]]
- [[_COMMUNITY_Core Domain Models|Core Domain Models]]
- [[_COMMUNITY_Admin Routes & Auth|Admin Routes & Auth]]
- [[_COMMUNITY_Email Reminders|Email Reminders]]
- [[_COMMUNITY_Penalty Resolution Tests|Penalty Resolution Tests]]
- [[_COMMUNITY_User Model|User Model]]
- [[_COMMUNITY_SlashGolf API Client|SlashGolf API Client]]
- [[_COMMUNITY_Tournament Model|Tournament Model]]
- [[_COMMUNITY_Test Fixtures|Test Fixtures]]
- [[_COMMUNITY_App Configuration|App Configuration]]
- [[_COMMUNITY_Projected Earnings Tests|Projected Earnings Tests]]
- [[_COMMUNITY_Live Pick State Methods|Live Pick State Methods]]
- [[_COMMUNITY_Migration Engine Setup|Migration Engine Setup]]
- [[_COMMUNITY_Penalty User Method Tests|Penalty User Method Tests]]
- [[_COMMUNITY_Results Processing|Results Processing]]
- [[_COMMUNITY_Tournament Import Bootstrap|Tournament Import Bootstrap]]
- [[_COMMUNITY_Penalty Accounting Methods|Penalty Accounting Methods]]
- [[_COMMUNITY_Field Validation|Field Validation]]
- [[_COMMUNITY_Pick Validation Route|Pick Validation Route]]
- [[_COMMUNITY_Score Formatting|Score Formatting]]
- [[_COMMUNITY_Baseline Migration|Baseline Migration]]
- [[_COMMUNITY_Missed-Cut Penalty Migration|Missed-Cut Penalty Migration]]
- [[_COMMUNITY_Reminder Type Migration|Reminder Type Migration]]
- [[_COMMUNITY_Recap Email Migration|Recap Email Migration]]
- [[_COMMUNITY_WD Round 2 Check|WD Round 2 Check]]
- [[_COMMUNITY_Pick Resolution Core|Pick Resolution Core]]
- [[_COMMUNITY_League Timezone|League Timezone]]
- [[_COMMUNITY_Pick Entry Route|Pick Entry Route]]
- [[_COMMUNITY_Score Display|Score Display]]
- [[_COMMUNITY_Leaderboard Route|Leaderboard Route]]
- [[_COMMUNITY_Live Penalty Refresh CLI|Live Penalty Refresh CLI]]
- [[_COMMUNITY_Tournament State Refresh|Tournament State Refresh]]
- [[_COMMUNITY_Admin Auth Decorator|Admin Auth Decorator]]
- [[_COMMUNITY_Admin Password Reset|Admin Password Reset]]
- [[_COMMUNITY_Results Redirect|Results Redirect]]
- [[_COMMUNITY_Admin Pick Override|Admin Pick Override]]
- [[_COMMUNITY_Package Init|Package Init]]
- [[_COMMUNITY_Tournament Status FSM|Tournament Status FSM]]

## God Nodes (most connected - your core abstractions)
1. `Tournament` - 88 edges
2. `Pick` - 84 edges
3. `TournamentResult` - 82 edges
4. `TournamentField` - 79 edges
5. `User` - 58 edges
6. `Player` - 58 edges
7. `SeasonPlayerUsage` - 27 edges
8. `TournamentSync` - 27 edges
9. `SlashGolfAPI` - 15 edges
10. `main()` - 11 edges

## Surprising Connections (you probably didn't know these)
- `migration-reviewer Agent` --semantically_similar_to--> `Migration Reviewer Agent (migration-reviewer.md)`  [INFERRED] [semantically similar]
  CLAUDE.md → .claude/agents/migration-reviewer.md
- `Import 2026 Tournament Schedule ================================ One-time script` --uses--> `Tournament`  [INFERRED]
  import_tournaments.py → models.py
- `Import all 2026 tournaments into database.` --uses--> `Tournament`  [INFERRED]
  import_tournaments.py → models.py
- `List all tournaments in database.` --uses--> `Tournament`  [INFERRED]
  import_tournaments.py → models.py
- `Earnings Multiplier Logic (1.5x Majors)` --semantically_similar_to--> `Earnings Multiplier Check`  [INFERRED] [semantically similar]
  CLAUDE.md → .claude/skills/pick-resolution-audit/SKILL.md

## Hyperedges (group relationships)
- **Pick Resolution Core Logic Triad** — claudemd_pick_resolve_pick, claudemd_backup_activation, claudemd_earnings_multiplier [EXTRACTED 0.95]
- **Missed-Cut Penalty Tracking Flow** — claudemd_missed_cut_penalty, claudemd_pick_penalty_triggered, claudemd_pick_refresh_live_penalty, claudemd_sync_live_leaderboard [EXTRACTED 0.92]
- **Migration Safety Verification Checks** — agent_migration_reviewer, agent_mr_destructive_ops, agent_mr_reversibility, agent_mr_pick_integrity [EXTRACTED 0.95]

## Communities

### Community 0 - "Migration Safety & App Core"
Cohesion: 0.05
Nodes (50): Migration Reviewer Agent (migration-reviewer.md), Destructive Operations Check, Nullable Constraint Safety Check, Pick/Earnings Table Integrity Check, Migration Reversibility Check, app.py (Routes & CLI), Backup Activation Logic, config.py (Environment Config) (+42 more)

### Community 1 - "API Sync Utilities"
Cohesion: 0.06
Nodes (26): calculate_projected_earnings(), _get_event_timezone(), get_recently_completed_tournaments(), get_upcoming_tournaments_window(), _parse_api_number(), parse_score_to_par(), _parse_tee_time(), _parse_tee_time_timestamp() (+18 more)

### Community 2 - "Core Domain Models"
Cohesion: 0.11
Nodes (37): Pick, Player, A PGA Tour golfer. Synced from SlashGolf API., Players in a tournament's field. Synced from API before tournament starts.     T, A player's result in a completed tournament. Synced from API after tournament., A user's pick for a specific tournament.      Key Logic:     - User selects prim, TournamentField, TournamentResult (+29 more)

### Community 3 - "Admin Routes & Auth"
Cohesion: 0.08
Nodes (26): admin_dashboard(), admin_update_payment(), change_password(), create_admin(), get_cumulative_scores(), index(), init_db(), inject_globals() (+18 more)

### Community 4 - "Email Reminders"
Cohesion: 0.18
Nodes (25): _app_context(), _build_recap_html(), _build_recap_plain_text(), build_reminder_email(), format_time_remaining(), get_active_reminder_window(), get_current_time(), get_field_count() (+17 more)

### Community 5 - "Penalty Resolution Tests"
Cohesion: 0.13
Nodes (12): Penalty flag resolution — tests the 9-branch matrix for Pick.resolve_pick()., Major + primary DQ → penalty triggered (duplicate coverage of DQ path)., Major + primary plays + CUT → penalty triggered., Major + primary plays + DQ → penalty triggered., Major + primary plays + made cut → no penalty., Non-major + primary CUT → no penalty., Major + primary WD before R2 + backup plays and CUTs → backup active, penalty tr, Major + primary WD before R2 + backup plays through → no penalty. (+4 more)

### Community 6 - "User Model"
Cohesion: 0.11
Nodes (13): Contestant in the pick 'em league., Hash and store password., Verify password against hash., Return display name or username., Get list of player IDs this user has 'used' (locked) for the season.         A p, Recalculate total points from all completed picks., User, Render a tournament info card with left accent border. (+5 more)

### Community 7 - "SlashGolf API Client"
Cohesion: 0.19
Nodes (8): Force Schedule Sync =================== Runs sync_schedule() directly, bypassing, Client for SlashGolf API., Record API call details for auditing., Make API request with exponential backoff, jitter, and structured logging., Get full season schedule., Get tournament details including field., Get earnings/prize money for completed tournament., SlashGolfAPI

### Community 8 - "Tournament Model"
Cohesion: 0.17
Nodes (8): A PGA Tour tournament. Synced from SlashGolf API., Check if pick deadline has passed., Derive tournament status based on start/end dates and deadlines., Return formatted deadline string., Tournament, Determine which reminder window (if any) is currently active., Return a clean, rounded time-remaining string based on the reminder window., Push app context only if not already in one (avoids nested session issues).

### Community 9 - "Test Fixtures"
Cohesion: 0.2
Nodes (1): Shared fixtures for DB-backed tests.

### Community 10 - "App Configuration"
Cohesion: 0.31
Nodes (8): Config, DevelopmentConfig, ProductionConfig, Golf Pick 'Em League - Configuration ===================================== Confi, Development configuration., Production configuration., Testing configuration., TestingConfig

### Community 11 - "Projected Earnings Tests"
Cohesion: 0.22
Nodes (5): Tests for sync_api module functions., is_major defaults to False — existing callers unaffected., CUT earnings stay 0 regardless of major flag., Major tournaments apply 1.5x multiplier to projected earnings., TestCalculateProjectedEarnings

### Community 12 - "Live Pick State Methods"
Cohesion: 0.25
Nodes (4): Check if player actually withdrew before completing Round 2.          Use this d, Get current earnings for display purposes.         - Complete tournaments: retur, Check if backup was activated during or after tournament.         Returns True i, Set ``penalty_triggered`` based on current TournamentResult status.          Saf

### Community 13 - "Migration Engine Setup"
Cohesion: 0.39
Nodes (7): get_engine(), get_engine_url(), get_metadata(), Run migrations in 'offline' mode.      This configures the context with just a U, Run migrations in 'online' mode.      In this scenario we need to create an Engi, run_migrations_offline(), run_migrations_online()

### Community 14 - "Penalty User Method Tests"
Cohesion: 0.25
Nodes (2): Tests for User.penalty_owed() / penalty_outstanding()., TestPenaltyOwed

### Community 15 - "Results Processing"
Cohesion: 0.33
Nodes (6): admin_process_results(), process_results_cli(), process_tournament_results(), Idempotent processing of results and seasonal usage tracking., Process tournament results and calculate points., Process results for all completed tournaments in the current season.

### Community 16 - "Tournament Import Bootstrap"
Cohesion: 0.33
Nodes (5): import_tournaments(), list_tournaments(), Import 2026 Tournament Schedule ================================ One-time script, List all tournaments in database., Import all 2026 tournaments into database.

### Community 17 - "Penalty Accounting Methods"
Cohesion: 0.5
Nodes (2): Total $ owed from penalty-triggered picks for the given season., Penalty owed minus already-paid, clamped at zero.

### Community 18 - "Field Validation"
Cohesion: 0.5
Nodes (2): Get the number of players in the tournament field., Check if tournament has a sufficient field size for picks.

### Community 19 - "Pick Validation Route"
Cohesion: 0.33
Nodes (3): Tournament detail page - shows different info based on tournament status:     -, tournament_detail(), Validate pick adheres to field eligibility and season usage constraints.

### Community 20 - "Score Formatting"
Cohesion: 0.5
Nodes (3): format_score_to_par(), Golf Pick 'Em League - Database Models ====================================== SQ, Format integer score to par for display.

### Community 21 - "Baseline Migration"
Cohesion: 0.5
Nodes (1): baseline: capture existing schema  Revision ID: aba1c0314b71 Revises:  Create Da

### Community 22 - "Missed-Cut Penalty Migration"
Cohesion: 0.5
Nodes (1): add missed-cut major penalty tracking  Revision ID: c368002569a2 Revises: 79cce1

### Community 23 - "Reminder Type Migration"
Cohesion: 0.5
Nodes (1): add last_reminder_type to Tournament  Revision ID: 79cce13ad2fb Revises: 7f95f63

### Community 24 - "Recap Email Migration"
Cohesion: 0.5
Nodes (1): add recap_email_sent to tournament  Revision ID: 7f95f6308352 Revises: aba1c0314

### Community 25 - "WD Round 2 Check"
Cohesion: 1.0
Nodes (1): Check if this was a WD or never started before completing round 2.

### Community 26 - "Pick Resolution Core"
Cohesion: 1.0
Nodes (1): Determine which player was active and calculate points.         Call this after

### Community 27 - "League Timezone"
Cohesion: 1.0
Nodes (2): get_current_time(), Get current time in league timezone.

### Community 28 - "Pick Entry Route"
Cohesion: 1.0
Nodes (2): make_pick(), Make or edit a pick for a tournament.

### Community 29 - "Score Display"
Cohesion: 1.0
Nodes (1): Format score to par for display (e.g., '-22', '+3', 'E').

### Community 30 - "Leaderboard Route"
Cohesion: 1.0
Nodes (2): leaderboard(), Redirect to home page (consolidated view).

### Community 31 - "Live Penalty Refresh CLI"
Cohesion: 1.0
Nodes (2): Re-evaluate Pick.penalty_triggered for all active-major tournaments.      Useful, refresh_live_penalties_cli()

### Community 32 - "Tournament State Refresh"
Cohesion: 1.0
Nodes (2): Ensure tournament statuses reflect current time without manual intervention., refresh_tournament_states()

### Community 33 - "Admin Auth Decorator"
Cohesion: 1.0
Nodes (2): admin_required(), Decorator to require admin access.

### Community 34 - "Admin Password Reset"
Cohesion: 1.0
Nodes (2): admin_reset_password(), Admin can reset a user's password.

### Community 35 - "Results Redirect"
Cohesion: 1.0
Nodes (2): Redirect to the most recently completed tournament., results()

### Community 36 - "Admin Pick Override"
Cohesion: 1.0
Nodes (2): admin_override_pick(), Admin can create or modify picks after deadline has passed.

### Community 37 - "Package Init"
Cohesion: 1.0
Nodes (0): 

### Community 38 - "Tournament Status FSM"
Cohesion: 1.0
Nodes (1): Tournament Status FSM

## Knowledge Gaps
- **75 isolated node(s):** `Golf Pick 'Em League - Configuration ===================================== Confi`, `Development configuration.`, `Production configuration.`, `Testing configuration.`, `Golf Pick 'Em League - Database Models ====================================== SQ` (+70 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `WD Round 2 Check`** (2 nodes): `Check if this was a WD or never started before completing round 2.`, `.wd_before_round_2_complete()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Pick Resolution Core`** (2 nodes): `.resolve_pick()`, `Determine which player was active and calculate points.         Call this after`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `League Timezone`** (2 nodes): `get_current_time()`, `Get current time in league timezone.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Pick Entry Route`** (2 nodes): `make_pick()`, `Make or edit a pick for a tournament.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Score Display`** (2 nodes): `Format score to par for display (e.g., '-22', '+3', 'E').`, `.format_score_to_par()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Leaderboard Route`** (2 nodes): `leaderboard()`, `Redirect to home page (consolidated view).`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Live Penalty Refresh CLI`** (2 nodes): `Re-evaluate Pick.penalty_triggered for all active-major tournaments.      Useful`, `refresh_live_penalties_cli()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Tournament State Refresh`** (2 nodes): `Ensure tournament statuses reflect current time without manual intervention.`, `refresh_tournament_states()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Admin Auth Decorator`** (2 nodes): `admin_required()`, `Decorator to require admin access.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Admin Password Reset`** (2 nodes): `admin_reset_password()`, `Admin can reset a user's password.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Results Redirect`** (2 nodes): `Redirect to the most recently completed tournament.`, `results()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Admin Pick Override`** (2 nodes): `admin_override_pick()`, `Admin can create or modify picks after deadline has passed.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Package Init`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Tournament Status FSM`** (1 nodes): `Tournament Status FSM`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Tournament` connect `Tournament Model` to `API Sync Utilities`, `Core Domain Models`, `Admin Routes & Auth`, `Email Reminders`, `User Model`, `SlashGolf API Client`, `Test Fixtures`, `Results Processing`, `Tournament Import Bootstrap`, `Field Validation`, `Pick Validation Route`, `Score Formatting`, `Pick Entry Route`, `Leaderboard Route`, `Live Penalty Refresh CLI`, `Tournament State Refresh`, `Admin Auth Decorator`, `Admin Password Reset`, `Results Redirect`, `Admin Pick Override`?**
  _High betweenness centrality (0.114) - this node is a cross-community bridge._
- **Why does `TournamentSync` connect `API Sync Utilities` to `Tournament Model`, `Core Domain Models`, `SlashGolf API Client`?**
  _High betweenness centrality (0.098) - this node is a cross-community bridge._
- **Why does `Pick` connect `Core Domain Models` to `API Sync Utilities`, `Admin Routes & Auth`, `Email Reminders`, `User Model`, `SlashGolf API Client`, `Tournament Model`, `Test Fixtures`, `Live Pick State Methods`, `Results Processing`, `Pick Validation Route`, `Score Formatting`, `Pick Resolution Core`, `Pick Entry Route`, `Leaderboard Route`, `Live Penalty Refresh CLI`, `Tournament State Refresh`, `Admin Auth Decorator`, `Admin Password Reset`, `Results Redirect`, `Admin Pick Override`?**
  _High betweenness centrality (0.090) - this node is a cross-community bridge._
- **Are the 80 inferred relationships involving `Tournament` (e.g. with `Force Schedule Sync =================== Runs sync_schedule() directly, bypassing` and `SlashGolfAPI`) actually correct?**
  _`Tournament` has 80 INFERRED edges - model-reasoned connections that need verification._
- **Are the 76 inferred relationships involving `Pick` (e.g. with `SlashGolfAPI` and `TournamentSync`) actually correct?**
  _`Pick` has 76 INFERRED edges - model-reasoned connections that need verification._
- **Are the 76 inferred relationships involving `TournamentResult` (e.g. with `SlashGolfAPI` and `TournamentSync`) actually correct?**
  _`TournamentResult` has 76 INFERRED edges - model-reasoned connections that need verification._
- **Are the 76 inferred relationships involving `TournamentField` (e.g. with `SlashGolfAPI` and `TournamentSync`) actually correct?**
  _`TournamentField` has 76 INFERRED edges - model-reasoned connections that need verification._