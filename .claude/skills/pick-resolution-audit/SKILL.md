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
Verify the 1.5x multiplier applies correctly:
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
