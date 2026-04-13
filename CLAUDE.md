# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Golf Pick 'Em is a season-long PGA Tour fantasy league where users pick one golfer per tournament. Points equal actual prize money earned. Each golfer can only be used once per season. Deployed on PythonAnywhere with SQLite.

## Available Tools & Plugins

Two distinct mechanisms — use them correctly:

- **Plugins** are invoked by mentioning the plugin name in task instructions (e.g., "use `commit-commands`")
- **Skills** are invoked by skill name using the `Skill` tool (e.g., invoke `brainstorming`, `pick-resolution-audit`)

### Installed Plugins (13)

| Plugin | Purpose |
|--------|---------|
| `claude-code-setup` | Environment and project setup management |
| `claude-md-management` | Markdown file handling and organization |
| `code-review` | Automated code review and quality checks |
| `code-simplifier` | Code refactoring and simplification |
| `coderabbit` | AI-powered holistic code analysis |
| `commit-commands` | Git commit management and automation |
| `context7` | Upstream library/framework docs awareness (MCP-connected) |
| `feature-dev` | Feature development scaffolding workflows |
| `frontend-design` | Design-forward UI/UX implementation |
| `playwright` | Browser automation and testing (MCP-connected) |
| `pr-review-toolkit` | Pull request review utilities |
| `pyright-lsp` | Python type checking via language server |
| `superpowers` | Advanced multi-file analysis and development capabilities |

### Available Skills

**Project skills** (`.claude/skills` and `.claude/agents`):

| Skill | Purpose |
|-------|---------|
| `pick-resolution-audit` | Audit pick resolution, WD/backup logic, earnings multipliers — invoke before/after any change to `Pick.resolve_pick()` |
| `migration-reviewer` | Review SQLite migrations for safety before `flask db upgrade` — invoke on every new migration |

**`superpowers` plugin skills** (most commonly used):

| Skill | Purpose |
|-------|---------|
| `brainstorming` | Explore requirements and design before building anything |
| `writing-plans` | Draft implementation plans before executing |
| `executing-plans` | Work through a structured plan step-by-step |
| `systematic-debugging` | Methodical debugging across multiple files |
| `test-driven-development` | TDD workflow — write tests before implementation |
| `verification-before-completion` | Verify correctness before marking work done |
| `finishing-a-development-branch` | Complete and close out a development branch |

### Plugin Prescription Reference

| When to prescribe | Plugin or Skill |
|-------------------|----------------|
| Any new feature or non-trivial change — before writing code | `brainstorming` skill |
| Implementing any feature or bugfix | `test-driven-development` skill |
| Any change to `Pick.resolve_pick()`, `process_tournament_results()`, or earnings logic | `pick-resolution-audit` skill |
| Any new migration file before `flask db upgrade` | `migration-reviewer` agent |
| After implementing any route/model change | `coderabbit` review |
| After modifying `.py` files | `pyright-lsp` |
| After completing a feature — reduce complexity | `code-simplifier` |
| UI changes needing browser verification | `playwright` |
| Needs awareness of library/framework APIs | `context7` |
| End of each logical unit of work | `commit-commands` |
| Before merging any branch to main | `pr-review-toolkit` |
| Modifying templates or CSS | `frontend-design` skill |

## Commands

```bash
# Run development server
flask run                    # or: python app.py

# Database setup
flask init-db                # Create tables
flask create-admin           # Interactive admin user creation

# API sync — requires SLASHGOLF_API_KEY, only configured on PythonAnywhere.
# Run via ./run_sync.sh <mode> on PythonAnywhere, not locally.
flask sync-run --mode schedule    # Import season schedule (Mon only — gated by weekday check)
flask sync-run --mode field       # Sync tournament field + tee times (Tue/Wed)
flask sync-run --mode live        # Update leaderboard with projected earnings
flask sync-run --mode results     # Finalize results + process picks (Sun/Mon)
flask sync-run --mode earnings    # Retry earnings finalization for pending tournaments

# Force schedule sync any day (bypasses Monday gate — use mid-week for purse announcements)
python force_schedule_sync.py

# Process results manually (all completed tournaments)
flask process-results

# Import tournaments from hardcoded list (one-time bootstrap)
python import_tournaments.py
```

```bash
# Run tests
python -m pytest tests/ -v
```

No linter is configured.

## Database Migrations

This project uses Flask-Migrate (Alembic). Never use raw SQL to modify the schema.

```bash
# Generate a new migration after changing models
flask db migrate -m "description of change"

# Review the generated file in migrations/versions/ before applying

# Apply pending migrations
flask db upgrade

# Rollback one migration
flask db downgrade

# Show current migration version
flask db current

# Check for unapplied model changes
flask db check

# Stamp without running (for existing databases only)
flask db stamp head
```

**Workflow for any model change:** edit `models.py` → `flask db migrate -m "desc"` → review migration → `flask db upgrade` → commit migration file

**On PythonAnywhere:** After `git pull`, run `flask db upgrade` before reloading the web app.

**Worktree gotcha:** `config.py` uses `BASE_DIR = os.path.abspath(os.path.dirname(__file__))`, so `flask db` commands run from a worktree point to the worktree's (empty) DB. Always pass `DATABASE_URL="sqlite:////absolute/path/to/golf_pickem.db"` when running `flask db` commands from a worktree.

## Architecture

**Single-process Flask app** — no blueprints, no API layer, no background workers. All server code lives in four Python files:

- `app.py` — Routes, view logic, Flask CLI commands, `process_tournament_results()`. Entry point.
- `models.py` — All SQLAlchemy models, `format_score_to_par()` (module-level), `get_current_time()`, `LEAGUE_TZ`. The `Pick.resolve_pick()` method contains the core WD/backup activation logic and earnings multipliers.
- `sync_api.py` — `SlashGolfAPI` (RapidAPI client), `TournamentSync` (sync orchestration), CLI commands registered via `register_sync_commands(app)`. Handles schedule/field/leaderboard/results/withdrawal syncing.
- `config.py` — Environment-based config classes. `FLASK_ENV` selects config; key settings: `SEASON_YEAR`, `SYNC_MODE` (free/standard), `ENTRY_FEE`.

**Supporting files:**
- `send_reminders.py` — Email notifications (picks open, deadline reminders, admin alerts). Called from `sync_api.py` after field sync and also runs standalone via scheduled task.
- `email_config.py` — SMTP credentials (gitignored, never committed).
- `import_tournaments.py` — One-time bootstrap script with hardcoded 2026 schedule.
- `force_schedule_sync.py` — Forces `sync_schedule()` any day of the week, bypassing the Monday gate. Use when a major announces its purse mid-week.

**Frontend:** Jinja2 templates with Bootstrap 5. Tom Select for player dropdowns on `make_pick.html`. No build step.

## Critical Domain Logic

**Pick Resolution (`Pick.resolve_pick()` in models.py):**
- Primary WDs before completing Round 2 → backup activates, primary returns to pool
- Primary WDs after Round 2 → primary counts with 0 pts, backup stays unused
- Both WD before R2 → primary used (0 pts), backup returns to pool
- Team events (Zurich Classic): earnings // 2
- Majors: earnings * 1.5 (applied in both `resolve_pick()` for final earnings and `sync_live_leaderboard()` for projected earnings)

**Missed-Cut-At-Major Penalty:**
- If a user's **active** pick at a major (Masters, PGA, US Open, The Open) finishes with status `cut` or `dq`, `Pick.penalty_triggered` is set and the user owes `PENALTY_PER_INCIDENT` ($15) to the season pot. WDs never trigger — backup-activation logic handles them.
- Flag is written in two places: `Pick.resolve_pick()` at finalization (authoritative), and `Pick.refresh_live_penalty()` invoked from `sync_live_leaderboard()` during active majors so the UI shows penalties in real time.
- `User.penalty_owed(season_year)` and `User.penalty_outstanding(season_year)` derive totals from `Pick.penalty_triggered` counts minus `User.penalty_paid`. Never denormalize.
- Penalty does NOT affect `User.total_points` — it's a side-pot mechanic. Admin tracks collected cash via the Penalty column on `/admin/payments`.
- `flask refresh-live-penalties` is a one-shot CLI that re-evaluates the flag for every active-major pick. Useful after dropping in a fresh DB copy for local testing.

**Tournament Status:**
- Transitions: `upcoming` → `active` → `complete`
- `update_status_from_time()` auto-sets `upcoming`/`active` based on dates, but **never** auto-sets `complete`
- Only `sync_api.py` sets `complete` after verifying API status is "Complete"/"Official"
- `results_finalized` flag tracks whether actual earnings (vs projected) have been fetched

**Season Player Usage:** `SeasonPlayerUsage` table tracks which players are locked. Populated by `resolve_pick()`, cleaned and rebuilt by `process_tournament_results()` in app.py (uses `begin_nested()` savepoints).

## Key Conventions

- All timestamps use `datetime.now(timezone.utc)` (not deprecated `utcnow()`)
- League timezone is `America/Chicago` (Central Time), stored as `LEAGUE_TZ` in models.py
- Pick deadlines stored in CT as naive datetimes in SQLite (timezone stripped after conversion)
- API responses use MongoDB-style number format (`{"$numberInt": "123"}`) — helper `_parse_api_number()` handles this. Tee time timestamps may arrive as ISO 8601 strings (e.g., `"2026-04-09T13:19:00"` in UTC) — `_parse_tee_time_timestamp()` handles both formats.
- `format_score_to_par()` is a module-level function in models.py (also exists as instance method on TournamentResult that delegates to it)
- Flask-Limiter rate-limits login to 10/min
- CSRF via Flask-WTF on all forms; AJAX calls include `X-CSRFToken` header
- Open redirect prevention: login rejects absolute URLs in `next` param

## PythonAnywhere Deployment

- **Account:** GolfPickEm — https://golfpickem.pythonanywhere.com/
- **Project path:** `/home/GolfPickEm/Golf_Pick_Em`
- **Virtualenv:** `/home/GolfPickEm/Golf_Pick_Em/venv` (Python 3.13)
- **WSGI file:** `/var/www/golfpickem_pythonanywhere_com_wsgi.py`
- **Database:** `/home/GolfPickEm/Golf_Pick_Em/golf_pickem.db`

**Deploy after pushing to GitHub:**
1. Open PythonAnywhere Bash console (auto-activates venv, auto-cds to project)
2. `git pull`
3. `pip install -r requirements.txt` (if deps changed)
4. `flask db upgrade` (if migrations added)
5. Reload web app from the Web tab

## Environment Variables

```
FLASK_ENV=development|production    # Selects config class
SECRET_KEY=...                      # Flask session secret
DATABASE_URL=sqlite:///...          # DB path (default: golf_pickem.db)
SLASHGOLF_API_KEY=...               # RapidAPI key for SlashGolf
SYNC_MODE=free|standard             # API tier (free limits syncs to conserve calls)
FIXED_DEADLINE_HOUR_CT=7            # Fallback deadline hour when tee times unavailable
```

## graphify

This project has a graphify knowledge graph at graphify-out/.

Rules:
- Before answering architecture or codebase questions, read graphify-out/GRAPH_REPORT.md for god nodes and community structure
- If graphify-out/wiki/index.md exists, navigate it instead of reading raw files
- After modifying code files in this session, run `python3 -c "from graphify.watch import _rebuild_code; from pathlib import Path; _rebuild_code(Path('.'))"` to keep the graph current
