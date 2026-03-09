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
