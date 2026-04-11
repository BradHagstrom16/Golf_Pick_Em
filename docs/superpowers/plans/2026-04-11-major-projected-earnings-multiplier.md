# Major Projected Earnings Multiplier Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Apply the 1.5x major multiplier to projected earnings during live leaderboard sync, so pick pages show the true expected points during Masters, PGA Championship, US Open, and The Open.

**Architecture:** `calculate_projected_earnings()` in `sync_api.py` currently returns raw PGA Tour payout amounts. We add an optional `is_major` parameter; when `True`, the returned value is multiplied by 1.5. The call site in `sync_live_leaderboard()` passes `tournament.is_major`. No other code changes needed — `Pick.resolve_pick()` already applies the multiplier to final earnings separately.

**Tech Stack:** Python, SQLite, Flask, pytest

---

### Task 1: Write failing tests for the multiplier in `calculate_projected_earnings`

**Files:**
- Modify: `tests/test_sync_api.py`

- [ ] **Step 1: Open the test file and find existing `calculate_projected_earnings` tests**

Run:
```bash
grep -n "calculate_projected_earnings" tests/test_sync_api.py
```

- [ ] **Step 2: Add failing tests for `is_major` parameter**

Add these tests after the existing `calculate_projected_earnings` tests:

```python
def test_calculate_projected_earnings_major_multiplier():
    """Major tournaments apply 1.5x multiplier to projected earnings."""
    all_positions = ["1", "2", "3"]
    purse = 22_500_000

    # Winner without major flag
    base = calculate_projected_earnings("1", purse, all_positions, is_major=False)
    # Winner with major flag — should be 1.5x
    major = calculate_projected_earnings("1", purse, all_positions, is_major=True)
    assert major == int(base * 1.5)


def test_calculate_projected_earnings_major_default_is_false():
    """is_major defaults to False — existing callers unaffected."""
    all_positions = ["1"]
    base = calculate_projected_earnings("1", 10_000_000, all_positions)
    explicit = calculate_projected_earnings("1", 10_000_000, all_positions, is_major=False)
    assert base == explicit


def test_calculate_projected_earnings_major_cut_zero():
    """CUT earnings stay 0 regardless of major flag."""
    result = calculate_projected_earnings("CUT", 22_500_000, ["CUT"], is_major=True)
    assert result == 0
```

- [ ] **Step 3: Run tests to confirm they fail**

```bash
python -m pytest tests/test_sync_api.py -k "major" -v
```

Expected: FAIL — `calculate_projected_earnings() got an unexpected keyword argument 'is_major'`

---

### Task 2: Add `is_major` parameter to `calculate_projected_earnings`

**Files:**
- Modify: `sync_api.py` (function signature and body, ~line 177)

- [ ] **Step 1: Update the function signature and apply multiplier**

Find this in `sync_api.py`:
```python
def calculate_projected_earnings(position_str: str, purse: int, all_positions: List[str]) -> int:
```

Replace with:
```python
def calculate_projected_earnings(position_str: str, purse: int, all_positions: List[str], is_major: bool = False) -> int:
```

Then find the `return` statement at the bottom of the function:
```python
    return int(purse * player_percentage)
```

Replace with:
```python
    earnings = int(purse * player_percentage)
    if is_major:
        earnings = int(earnings * 1.5)
    return earnings
```

- [ ] **Step 2: Run tests to confirm they pass**

```bash
python -m pytest tests/test_sync_api.py -k "major" -v
```

Expected: PASS (all 3 new tests green)

- [ ] **Step 3: Run full test suite to confirm no regressions**

```bash
python -m pytest tests/ -v
```

Expected: All previously passing tests still pass.

- [ ] **Step 4: Commit**

```bash
git add sync_api.py tests/test_sync_api.py
git commit -m "feat: apply 1.5x multiplier to projected earnings for majors"
```

---

### Task 3: Pass `is_major` at the call site in `sync_live_leaderboard`

**Files:**
- Modify: `sync_api.py` (~line 1006)

- [ ] **Step 1: Find the call to `calculate_projected_earnings` in `sync_live_leaderboard`**

```bash
grep -n "calculate_projected_earnings" sync_api.py
```

- [ ] **Step 2: Update the call site to pass `tournament.is_major`**

Find:
```python
                projected_earnings = calculate_projected_earnings(
                    position_str=position,
                    purse=purse,
                    all_positions=all_positions
                )
```

Replace with:
```python
                projected_earnings = calculate_projected_earnings(
                    position_str=position,
                    purse=purse,
                    all_positions=all_positions,
                    is_major=tournament.is_major
                )
```

- [ ] **Step 3: Run full test suite**

```bash
python -m pytest tests/ -v
```

Expected: All tests pass.

- [ ] **Step 4: Commit**

```bash
git add sync_api.py
git commit -m "feat: pass is_major flag through to projected earnings calculation"
```

---

### Task 4: Manual verification on PythonAnywhere

- [ ] **Step 1: Deploy**

```bash
git push origin main
# On PythonAnywhere:
git pull
```

- [ ] **Step 2: Confirm Masters `is_major` flag in DB**

```bash
sqlite3 golf_pickem.db "SELECT name, purse, is_major FROM tournament WHERE name LIKE '%Masters%';"
```

Expected: `Masters Tournament|22500000|1`

- [ ] **Step 3: Run live sync manually and check a pick page**

```bash
./run_sync.sh live
```

Open a pick page for a user who has a Masters pick. Projected earnings shown should reflect 1.5x. For example, if the player is sole leader on a $22.5M purse: raw = $4,050,000 (18%), projected shown = $6,075,000.

- [ ] **Step 4: Verify other non-major tournaments are unaffected**

Check a pick page for any non-major active or recently completed tournament — projected earnings should be unchanged.
