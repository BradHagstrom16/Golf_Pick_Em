# Withdrawal Sync & Active Tournament Query Fixes

## Context

Three bugs were identified during the Arnold Palmer Invitational (March 2026) that caused WD
status to never display mid-tournament and live/WD syncs to silently find no active tournaments
on Sunday evening. All three fixes are in `sync_api.py`. No model changes, no migrations, no
template changes required.

---

## Files Affected

- `sync_api.py` — three targeted changes, all within `register_sync_commands()`

---

## Background: What Went Wrong

1. **`free_tier_blocked` blocklist** — `withdrawals` mode was hardcoded into a blocklist that
   exits before any API call is made. This meant `./run_sync.sh withdrawals` was a no-op all
   season on the free tier.

2. **Missing `force=True`** — Even after removing the blocklist, the `withdrawals` branch calls
   `check_withdrawals(tournament)` without `force=True`, so the method's own internal free-tier
   guard would still bail. The `live-with-wd` branch already uses `force=True` correctly — the
   `withdrawals` branch needs to match it.

3. **`get_active_tournaments()` time window too narrow** — The function filters by
   `end_date >= now - timedelta(hours=6)`. Tournament `end_date` values are stored as midnight
   UTC on the final day (e.g., `2026-03-08 00:00:00`), not end-of-day. By Sunday evening the
   6-hour lookback window had already passed that midnight timestamp, so the Arnold Palmer was
   excluded from results despite having `status = 'active'` in the DB. `live-with-wd` and
   `withdrawals` both call this function, so both returned "No active tournaments."

   The proper fix is to query by `status = 'active'` directly — the `status` field is the
   authoritative source of truth, maintained by `update_status_from_time()`. No date math needed.

---

## Implementation Steps

### Step 1: Remove `withdrawals` from the free tier blocklist

In `sync_run_cmd`, find:

```python
free_tier_blocked = {'withdrawals'}  # 'live' now allowed for projected earnings
```

Replace with:

```python
free_tier_blocked = set()  # withdrawal sync now permitted on free tier
```

→ **Run `pyright-lsp`** to confirm no type errors after the change.

---

### Step 2: Add `force=True` to the `withdrawals` branch

Still in `sync_run_cmd`, find the `if mode in ('withdrawals', 'all'):` block:

```python
for tournament in active:
    withdrawals = sync.check_withdrawals(tournament)
```

Replace with:

```python
for tournament in active:
    withdrawals = sync.check_withdrawals(tournament, force=True)
```

---

### Step 3: Fix `get_active_tournaments()` to query by status

Find the `get_active_tournaments()` function (outside `register_sync_commands`, at module level
in `sync_api.py`). It currently looks like:

```python
def get_active_tournaments(include_upcoming_hours: int = 12) -> List[Tournament]:
    now = datetime.now(LEAGUE_TZ)
    window_start = now - timedelta(hours=6)
    window_end = now + timedelta(hours=include_upcoming_hours)
    tournaments = Tournament.query.filter(
        Tournament.start_date <= window_end,
        Tournament.end_date >= window_start,
        Tournament.status != "complete",
    ).order_by(Tournament.start_date).all()
    _refresh_statuses(tournaments)
    return tournaments
```

Replace entirely with:

```python
def get_active_tournaments() -> List[Tournament]:
    """
    Return all tournaments currently in 'active' status.
    Queries by status directly — the authoritative field maintained by
    update_status_from_time(). Avoids brittle end_date window math that
    breaks when end_date is stored as midnight UTC rather than end-of-day.
    """
    return Tournament.query.filter(
        Tournament.status == "active"
    ).order_by(Tournament.start_date).all()
```

Note: The `include_upcoming_hours` parameter and `_refresh_statuses()` call are intentionally
removed. `_refresh_statuses()` calls `update_status_from_time()` which never sets `complete`,
so there is no risk of re-activating a completed tournament. Status transitions to `complete`
only happen in `sync_tournament_results()`.

→ **Run `pyright-lsp`** to verify the signature change (removed parameter) has no call-site
impact. Search the codebase for any call passing `include_upcoming_hours=` — there should be
none, but confirm.

→ **Run `code-review`** on the full `sync_api.py` diff before proceeding.

---

### Step 4: Verify end-to-end

Manual test sequence on PythonAnywhere during an active tournament week:

```bash
# Should now find the active tournament and attempt WD check
./run_sync.sh withdrawals

# Should find active tournament all day Sunday, not just through midday
./run_sync.sh live-with-wd
```

Expected output for both: tournament name appears, not "No active tournaments."

Outside of tournament week, both will output "No active tournaments" — that is correct.

→ **Run `commit-commands`**: message = `fix: withdrawal sync free tier guard and active tournament query`

---

## Verification Checklist

- [ ] `./run_sync.sh withdrawals` no longer exits with "Free tier mode: 'withdrawals' sync disabled"
- [ ] `./run_sync.sh live-with-wd` finds the active tournament on Sunday evening (previously failed)
- [ ] `get_active_tournaments()` has no callers passing `include_upcoming_hours` argument
- [ ] No other callers of `get_active_tournaments()` are broken by the removed parameter
- [ ] `check_withdrawals()` is called with `force=True` in both `live-with-wd` and `withdrawals` branches

---
