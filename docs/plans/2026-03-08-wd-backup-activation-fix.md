# WD/Backup Activation & Admin Override Fix

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix backup activation for "not started" players and make admin overrides re-resolve completed picks.

**Architecture:** Three targeted fixes in models.py and app.py — expand WD detection to include "not started" status, add re-resolution logic to admin override route, and fix stale season usage cleanup.

**Tech Stack:** Flask, SQLAlchemy, SQLite

---

### Task 1: DB Correction — Fix Vbrown1217's Arnold Palmer Pick

**Context:** Pick #129 has stale resolved fields after admin override. Chris Kirk (88) earned $58,000 but active_player is still Jake Knapp (95) with 0 points.

**Step 1: Fix pick 129 resolved fields**

```sql
UPDATE pick SET active_player_id = 88, points_earned = 58000, primary_used = 1, backup_used = 0 WHERE id = 129;
```

**Step 2: Fix season_player_usage — remove orphaned Knapp, add Kirk**

```sql
DELETE FROM season_player_usage WHERE user_id = 7 AND player_id = 95 AND season_year = 2026;
INSERT INTO season_player_usage (user_id, player_id, season_year, created_at) VALUES (7, 88, 2026, datetime('now'));
```

**Step 3: Recalculate user 7 total_points**

```sql
UPDATE user SET total_points = (SELECT COALESCE(SUM(p.points_earned), 0) FROM pick p JOIN tournament t ON p.tournament_id = t.id WHERE p.user_id = 7 AND t.status = 'complete' AND p.points_earned IS NOT NULL) WHERE id = 7;
```

**Step 4: Verify**

Query pick 129, season_player_usage for user 7, and user 7 total_points.

---

### Task 2: Code Fix — resolve_pick() handles "not started" players

**Files:**
- Modify: `models.py:424-429` (primary_wd_early condition)

**Change:** Expand `primary_wd_early` to also match `status == 'not started'` with `rounds_completed < 2` (or == 0). A player who never started should activate the backup just like a pre-R2 WD.

Same logic applies to the backup_wd_early check on lines 434-437.

---

### Task 3: Code Fix — Admin override re-resolves completed picks

**Files:**
- Modify: `app.py:932-952` (admin_override_pick save block)

**Change:** After updating or creating the pick for a **completed** tournament:
1. Delete old season usage for the pick's old `active_player_id` (capture before overwrite)
2. Also delete usage for old primary/backup if different
3. Call `resolve_pick()` on the pick
4. Recalculate user total_points
5. Commit

---

### Task 4: Code Fix — process_tournament_results() cleans up old active player

**Files:**
- Modify: `app.py:984-988` (season usage cleanup)

**Change:** Also include `pick.active_player_id` in the set of player IDs to clean up, so stale usage from a prior resolution is removed.

---

### Task 5: Verify, Code Review, Commit & Push

Run code-review plugin, then commit all changes and push to main.
