# Golf Pick 'Em — Claude Code Environment Setup

## Context

The Golf Pick 'Em repo currently has `.claude/` and `CLAUDE.md` listed in `.gitignore`,
which means Claude Code has no committed project-level config, hooks, or skills. This task:

1. Unblocks `.claude/` and `CLAUDE.md` from `.gitignore` so they're tracked in version control
2. Creates `.claude/settings.json` with two automated safety hooks (`.env` protection + smoke test)
3. Creates a project-level skill for the pick-resolution logic audit pattern
4. Creates a `migration-reviewer` subagent for SQLite schema changes
5. Verifies all plugins listed in `CLAUDE.md` are reachable

**No Python files, models, routes, or templates are touched in this task.**

---

## Files Affected

| Action | File |
|--------|------|
| MODIFY | `.gitignore` |
| CREATE | `.claude/settings.json` |
| CREATE | `.claude/skills/pick-resolution-audit/SKILL.md` |
| CREATE | `.claude/agents/migration-reviewer.md` |

---

## Implementation Steps

### Step 1 — Fix `.gitignore`

Open `.gitignore`. Find these two lines near the top under `# Claude working directories`:

```
.claude/
CLAUDE.md
```

Replace them with:

```
# Claude local overrides only — project config and CLAUDE.md are committed
.claude/settings.local.json
```

This keeps any machine-specific overrides private while allowing hooks, skills, agents, and
`CLAUDE.md` to be committed and shared.

→ **Run `code-review`** on the `.gitignore` diff to confirm no other credentials are accidentally exposed.

---

### Step 2 — Verify `CLAUDE.md` is visible

After the `.gitignore` change, confirm Claude Code can see the file:

```bash
git check-ignore -v CLAUDE.md
# Should return nothing (not ignored)

git check-ignore -v .claude/settings.json
# Should return nothing (not ignored)

git check-ignore -v .claude/settings.local.json
# Should return: .gitignore:N:.claude/settings.local.json
```

---

### Step 3 — Create `.claude/settings.json`

Create `.claude/settings.json` with this exact content:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "if echo \"$CLAUDE_TOOL_INPUT\" | grep -qE 'email_config\\.py|env_config\\.sh|\\.env'; then echo 'BLOCKED: Credential file is protected. Never commit credentials.' && exit 1; fi"
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "if echo \"$CLAUDE_TOOL_INPUT\" | grep -qE '(app|models|sync_api)\\.py'; then cd \"$(git rev-parse --show-toplevel)\" && FLASK_ENV=testing python -c \"from app import app; app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'; from models import db; ctx = app.app_context(); ctx.push(); db.create_all(); print('Smoke test OK')\" 2>&1 | tail -5; fi"
          }
        ]
      }
    ]
  }
}
```

**What these hooks do:**
- **PreToolUse** — Blocks any edit to `email_config.py`, `env_config.sh`, or `.env` files
  before the write happens. Protects `SLASHGOLF_API_KEY`, `SECRET_KEY`, and Gmail credentials.
- **PostToolUse** — After any edit to `app.py`, `models.py`, or `sync_api.py`, automatically
  runs an in-memory SQLite smoke test. Catches circular imports and broken model definitions
  immediately without needing a running server.

→ **Run `code-review`** to verify hook JSON syntax and logic are correct.

---

### Step 4 — Create `.claude/skills/pick-resolution-audit/SKILL.md`

Create the directory `.claude/skills/pick-resolution-audit/` and the file `SKILL.md`:

```markdown
---
name: pick-resolution-audit
description: >
  Audit any change that touches pick resolution, WD/backup logic, or earnings calculation.
  Invoke before implementing and after completing any change to Pick.resolve_pick(),
  process_tournament_results(), or earnings multiplier logic.
invocation: user-only
---

# Pick Resolution Audit Skill

When invoked, trace through the pick resolution logic to verify correctness across
all edge cases. This skill exists because pick resolution errors break league fairness
and cannot be easily undone once results are processed.

## Checks (run in order)

### 1. Backup Activation Gate
Verify the WD/backup logic enforces:
- Backup activates ONLY if primary withdraws **before completing Round 2**
- "Completing Round 2" = player has a score recorded for hole 36 (or equivalent)
- If primary WDs **after R2**: primary stays active at $0, backup remains unused
- If primary WDs **before R2** and backup also WDs before R2: primary at $0, backup unused
- Only ONE golfer is marked `used=True` per week per member

Check `Pick.resolve_pick()` in `models.py` for these conditions.

### 2. Earnings Multiplier
Verify the 1.5× multiplier applies correctly:
- Applied to: Masters, PGA Championship, US Open, The Open Championship
- NOT applied to: all other events including Players Championship, signature events
- Check the tournament's `is_major` flag is being set correctly during sync
- Confirm `pick.earnings = raw_earnings * multiplier` and not applied twice

### 3. Zurich Classic
If the change touches team event handling:
- Picked player's earnings must be divided by 2
- Check the tournament's `is_team_event` flag is set
- Confirm the halving happens at earnings assignment, not at points display

### 4. Golfer Lock
After pick resolution runs:
- `Pick.golfer_used = True` must be set for the activated pick (primary or backup)
- No member should have the same golfer available again after activation
- Check that `used` status is keyed on `(user_id, golfer_name)` or equivalent

### 5. Edge Case Matrix
Trace through the proposed change for each scenario:

| Scenario | Primary status | Backup status | Expected outcome |
|----------|---------------|---------------|-----------------|
| Normal finish | Played | N/A | Primary earns prize money |
| WD before R2 | WD pre-R2 | Played | Backup earns, primary unused |
| WD before R2 | WD pre-R2 | Also WD pre-R2 | Primary at $0, backup unused |
| WD after R2 | WD post-R2 | Played | Primary at $0, backup unused |
| Cut | Missed cut | N/A | Primary earns $0 (still used) |
| No backup submitted | WD pre-R2 | None | Primary at $0 |

### 6. API Call Impact
If the change affects sync logic:
- Count the net new API calls per tournament
- Current budget: 250 calls/month, 20 scorecards/day
- Flag if change risks exceeding limits

## Output Format

```
PICK RESOLUTION AUDIT
Status: SAFE | REVIEW NEEDED | BLOCK

Findings:
- [PASS/WARN/BLOCK] Check name: detail

Edge cases verified: Y/N
Earnings multiplier verified: Y/N
API call delta: +N calls/tournament

Recommendation: <one sentence>
```

Output BLOCK if the change would cause incorrect earnings assignment or incorrect `used` status.
Output REVIEW NEEDED if an edge case is ambiguous or untested.
Output SAFE if all checks pass.
```

---

### Step 5 — Create `.claude/agents/migration-reviewer.md`

Create `.claude/agents/` and `migration-reviewer.md`:

```markdown
---
name: migration-reviewer
description: >
  Reviews SQLite schema changes for safety before flask db upgrade runs.
  Checks for destructive operations, missing downgrade paths, and convention violations.
  Invoke before any flask db upgrade on a new migration.
---

# Migration Reviewer

When given a migration file to review, perform these checks and report findings.

## Checks

1. **Destructive operations**
   - Flag any `DROP TABLE` or `DROP COLUMN` without a documented backup strategy
   - This is a live mid-season app — data loss is unrecoverable on SQLite free tier

2. **Reversibility**
   - Verify `downgrade()` properly reverses everything in `upgrade()`
   - Flag if `downgrade()` is empty or raises `NotImplementedError`

3. **Nullable constraint safety**
   - Flag any `nullable=False` column added to an existing table without a `server_default`
     or explicit data backfill step — will fail silently on SQLite if existing rows exist

4. **Raw SQL bypass**
   - Flag any `op.execute()` with raw DDL that could be done via `op.add_column()` etc.
   - CLAUDE.md rule: never use raw SQL for schema changes

5. **Pick/earnings table integrity**
   - Any change to `pick`, `tournament`, or `tournament_field` tables requires extra review
   - These tables drive live league scoring — structural changes mid-season are high risk
   - Flag if change affects columns used by `Pick.resolve_pick()` or `process_tournament_results()`

6. **Dependency chain**
   - Verify `down_revision` matches the current head (`flask db current`)
   - Flag if the migration appears to branch the history

## Output Format

```
MIGRATION REVIEW: <filename>
Status: SAFE | REVIEW NEEDED | BLOCK

Findings:
- [PASS/WARN/BLOCK] Check name: detail

Recommendation: <one sentence>
```

Output BLOCK if the migration would cause data loss or break pick resolution.
Output REVIEW NEEDED for anything requiring Brad to make a judgment call.
Output SAFE if all checks pass.
```

→ **Run `code-review`** on all created files.

---

### Step 6 — Verify Plugin Availability

Run this to confirm each plugin listed in `CLAUDE.md` is reachable:

```bash
# List installed MCP servers / plugins visible to Claude Code
claude mcp list
```

Expected plugins from `CLAUDE.md`:
- `claude-code-setup`
- `claude-md-management`
- `code-review`
- `code-simplifier`
- `coderabbit`
- `commit-commands`
- `context7`
- `feature-dev`
- `frontend-design`
- `playwright`
- `pr-review-toolkit`
- `pyright-lsp`
- `superpowers`

If any are missing, note them and do NOT update `CLAUDE.md` to remove them — flag for Brad
to reinstall before the next development session.

→ **Run `claude-md-management`** to confirm `CLAUDE.md` plugin list matches what's installed.

---

### Step 7 — Smoke Test

Run the smoke test manually to confirm it works before relying on the hook:

```bash
FLASK_ENV=testing python -c "
from app import app
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
from models import db
ctx = app.app_context()
ctx.push()
db.create_all()
with app.test_client() as c:
    r = c.get('/')
    print(f'Index response: {r.status_code}')
print('Smoke test OK')
"
```

---

### Step 8 — Commit

→ **Run `commit-commands`** with message:

```
chore: configure project-level Claude Code tooling

- Unblock .claude/ and CLAUDE.md from .gitignore
- Add .claude/settings.json with smoke test and credential protection hooks
- Add .claude/skills/pick-resolution-audit/SKILL.md for WD/backup logic auditing
- Add .claude/agents/migration-reviewer.md for Alembic safety checks

No app code changed.
```

---

## Verification Checklist

- [ ] `git check-ignore -v CLAUDE.md` returns nothing
- [ ] `git check-ignore -v .claude/settings.json` returns nothing
- [ ] `git check-ignore -v .claude/settings.local.json` returns a match
- [ ] `cat .claude/settings.json | python3 -m json.tool` prints clean JSON
- [ ] `ls .claude/skills/pick-resolution-audit/SKILL.md` exists
- [ ] `ls .claude/agents/migration-reviewer.md` exists
- [ ] Manual smoke test exits with `Smoke test OK`
- [ ] `claude mcp list` confirms all 13 plugins are present (note any missing)

---

## Notes

- This task does NOT touch `app.py`, `models.py`, `sync_api.py`, or any templates
- After this task completes, invoke `pick-resolution-audit` at the start of any session
  touching WD/backup logic or earnings calculation
- Invoke `migration-reviewer` before every `flask db upgrade`
- `context7` requires Node.js v18+ — if smoke test fails on import, check Node version first
