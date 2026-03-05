# Fix: Remove Tournament Name Overwrites + Rename Sponsored Tournaments

## Context

The `sync_schedule()` method in `sync_api.py` overwrites `tournament.name` with whatever the API returns every Monday. This is unnecessary — our 32-tournament schedule is locked for the season, and the API names include long sponsor strings (e.g., "Arnold Palmer Invitational presented by Mastercard") that cause horizontal scroll on the standings table.

Two changes:
1. Stop `sync_schedule()` from overwriting names on existing tournaments
2. Rename two tournaments in the database to drop sponsor suffixes

## Files Affected

- `sync_api.py` — Remove `existing.name = name` from `sync_schedule()`

## Implementation Steps

### Step 1: Remove the name overwrite in `sync_schedule()`

In `sync_api.py`, inside the `sync_schedule()` method of the `TournamentSync` class, find the block that updates existing tournament data:

```python
# Update existing tournament data
existing.name = name
api_purse = self._parse_api_number(event.get("purse", 0))
if api_purse > 0:
    existing.purse = api_purse
existing.is_team_event = event.get("format") == "team"
updated += 1
```

**Delete the line `existing.name = name`** so it becomes:

```python
# Update existing tournament data (name intentionally NOT overwritten —
# league names are locked and cleaned of sponsor suffixes)
api_purse = self._parse_api_number(event.get("purse", 0))
if api_purse > 0:
    existing.purse = api_purse
existing.is_team_event = event.get("format") == "team"
updated += 1
```

The comment is important — it explains *why* the name isn't updated so a future developer (or Claude) doesn't "fix" it by adding it back.

→ **Run `pyright-lsp`** to verify no type issues introduced
→ **Run `code-review`** on `sync_api.py`

### Step 2: Commit

→ **Run `commit-commands`**: message = `fix: stop sync_schedule from overwriting tournament names`

## Verification

- [ ] The line `existing.name = name` no longer exists in `sync_schedule()`
- [ ] A comment explains why the name is not updated
- [ ] No other logic in `sync_schedule()` is changed
- [ ] `PURSE_ESTIMATES` dict keys are NOT changed (they use API names for matching, which still works because purse lookup happens via the `name` variable from the API response, not from `existing.name`)

## Post-Deploy: Database Updates (Brad runs manually)

After deploying this code change, Brad will run two SQL UPDATE statements directly against the production SQLite database on PythonAnywhere to rename the tournaments. Those statements are provided separately outside this handoff.
