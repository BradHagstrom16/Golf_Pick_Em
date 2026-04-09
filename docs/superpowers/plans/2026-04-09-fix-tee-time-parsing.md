# Fix Tee Time Timestamp Parsing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix `_parse_tee_time_timestamp` to handle ISO 8601 strings from the API, so pick deadlines are set from the timezone-safe timestamp field instead of falling through to the ambiguous `teeTime` string path.

**Architecture:** The API's `teeTimeTimestamp` field changed from MongoDB-style millisecond integers to ISO 8601 strings (`"2026-04-09T13:19:00"`). These are UTC times. The fix adds ISO string detection to `_parse_tee_time_timestamp` so it parses them as UTC datetimes. A secondary defensive fix ensures `_parse_tee_time` (the string fallback) handles the case where no timezone is in the API response by cross-referencing the `teeTimeTimestamp` ISO string for timezone-safe parsing before falling back to the ambiguous `teeTime` time-only string.

**Tech Stack:** Python 3.13, pytz, datetime

**Root Cause (for context):**
1. API returned `teeTimeTimestamp: "2026-04-09T11:40:00"` (ISO string, UTC)
2. `_parse_tee_time_timestamp` only handled dicts and raw integers — tried `int("2026-04-09T11:40:00")` → failed
3. Fell through to `_parse_tee_time` which parsed `teeTime: "7:40am"` (local Eastern time)
4. No timezone field in API response → `_get_event_timezone` returned Central (LEAGUE_TZ)
5. 7:40 AM Eastern was treated as 7:40 AM Central → deadline 1 hour late

---

### Task 1: Add pytest and create test infrastructure

**Files:**
- Modify: `requirements.txt`
- Create: `tests/__init__.py`
- Create: `tests/test_tee_time_parsing.py`

- [ ] **Step 1: Add pytest to requirements.txt**

Add `pytest` to the end of `requirements.txt`:

```
pytest
```

- [ ] **Step 2: Install pytest**

Run: `pip install pytest`
Expected: Successfully installed pytest

- [ ] **Step 3: Create test directory and init file**

Create `tests/__init__.py` as an empty file.

- [ ] **Step 4: Create test file with imports**

Create `tests/test_tee_time_parsing.py`:

```python
"""Tests for TournamentSync tee time parsing methods."""
import pytz
from datetime import datetime
from sync_api import TournamentSync


class TestParseTeeTimeTimestamp:
    """Tests for _parse_tee_time_timestamp — the preferred, timezone-safe parser."""

    def test_returns_none_for_none(self):
        assert TournamentSync._parse_tee_time_timestamp(None) is None

    def test_returns_none_for_empty_string(self):
        assert TournamentSync._parse_tee_time_timestamp("") is None

    def test_parses_mongodb_date_numberlong(self):
        """Original format: {"$date": {"$numberLong": "1744199400000"}}"""
        ts = {"$date": {"$numberLong": "1744199400000"}}
        result = TournamentSync._parse_tee_time_timestamp(ts)
        assert result is not None
        assert result.tzinfo is not None
        # 1744199400000 ms = 2025-04-09 11:30:00 UTC
        assert result.year == 2025
        assert result.month == 4

    def test_parses_raw_millisecond_integer(self):
        """Raw integer milliseconds."""
        result = TournamentSync._parse_tee_time_timestamp(1744199400000)
        assert result is not None
        assert result.tzinfo is not None

    def test_parses_iso_string_as_utc(self):
        """New API format: plain ISO 8601 string, treated as UTC."""
        result = TournamentSync._parse_tee_time_timestamp("2026-04-09T11:40:00")
        assert result is not None
        assert result.tzinfo is not None
        assert result.hour == 11
        assert result.minute == 40
        # Must be UTC
        assert result.tzname() == "UTC"

    def test_parses_iso_string_with_z_suffix(self):
        result = TournamentSync._parse_tee_time_timestamp("2026-04-09T11:40:00Z")
        assert result is not None
        assert result.tzname() == "UTC"
        assert result.hour == 11

    def test_parses_iso_string_with_utc_offset(self):
        result = TournamentSync._parse_tee_time_timestamp("2026-04-09T11:40:00+00:00")
        assert result is not None
        assert result.hour == 11

    def test_iso_string_converts_to_correct_central_time(self):
        """The Masters bug: 11:40 UTC should be 6:40 AM Central (CDT, UTC-5)."""
        result = TournamentSync._parse_tee_time_timestamp("2026-04-09T11:40:00")
        ct = result.astimezone(pytz.timezone("America/Chicago"))
        assert ct.hour == 6
        assert ct.minute == 40
```

- [ ] **Step 5: Run tests — expect failures on ISO string tests**

Run: `python -m pytest tests/test_tee_time_parsing.py -v`
Expected: `test_parses_iso_string_as_utc`, `test_parses_iso_string_with_z_suffix`, `test_parses_iso_string_with_utc_offset`, and `test_iso_string_converts_to_correct_central_time` FAIL. The others PASS.

- [ ] **Step 6: Commit test infrastructure**

```bash
git add requirements.txt tests/__init__.py tests/test_tee_time_parsing.py
git commit -m "test: add pytest and tee time parsing tests

Cover existing MongoDB/integer formats and new ISO 8601 string format.
ISO tests fail — implementation follows next."
```

---

### Task 2: Fix `_parse_tee_time_timestamp` to handle ISO 8601 strings

**Files:**
- Modify: `sync_api.py:368-400`

- [ ] **Step 1: Update `_parse_tee_time_timestamp` to detect and parse ISO strings**

In `sync_api.py`, replace the `_parse_tee_time_timestamp` method (lines 368-400):

```python
    @staticmethod
    def _parse_tee_time_timestamp(tee_time_ts) -> Optional[datetime]:
        """
        Parse teeTimeTimestamp from API (preferred method - timezone-safe).

        Handles three formats:
        1. MongoDB dict: {"$date": {"$numberLong": "1768497660000"}}
        2. Raw integer: milliseconds since epoch
        3. ISO 8601 string: "2026-04-09T13:19:00" (treated as UTC)
        """
        if not tee_time_ts:
            return None

        try:
            # Handle MongoDB-style timestamp format
            if isinstance(tee_time_ts, dict):
                if '$date' in tee_time_ts:
                    date_val = tee_time_ts['$date']
                    if isinstance(date_val, dict) and '$numberLong' in date_val:
                        ts_ms = int(date_val['$numberLong'])
                    else:
                        ts_ms = int(date_val)
                elif '$numberLong' in tee_time_ts:
                    ts_ms = int(tee_time_ts['$numberLong'])
                else:
                    return None
                ts_sec = ts_ms / 1000
                return datetime.fromtimestamp(ts_sec, tz=pytz.UTC)

            # Handle ISO 8601 string (new API format)
            if isinstance(tee_time_ts, str) and "T" in tee_time_ts:
                dt = datetime.fromisoformat(tee_time_ts.replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = pytz.UTC.localize(dt)
                return dt

            # Handle raw millisecond integer
            ts_ms = int(tee_time_ts)
            ts_sec = ts_ms / 1000
            return datetime.fromtimestamp(ts_sec, tz=pytz.UTC)
        except Exception as e:
            logger.warning("Unable to parse tee time timestamp '%s': %s", tee_time_ts, e)
            return None
```

Key changes:
- Type hint broadened from `Optional[Dict]` to no restriction (it receives strings now)
- ISO 8601 string branch added before the `int()` fallback
- Naive ISO datetimes (no timezone suffix) are treated as UTC — this matches the API data where `"2026-04-09T13:19:00"` corresponds to `teeTime: "9:19am"` EDT (13:19 UTC = 9:19 EDT ✓)
- Dict branch now returns immediately instead of falling through to shared `ts_sec` logic

- [ ] **Step 2: Run the tests**

Run: `python -m pytest tests/test_tee_time_parsing.py -v`
Expected: ALL tests PASS

- [ ] **Step 3: Commit the fix**

```bash
git add sync_api.py
git commit -m "fix: handle ISO 8601 strings in tee time timestamp parser

The SlashGolf API changed teeTimeTimestamp from MongoDB-style millisecond
integers to ISO 8601 strings. The old parser tried int() on the string and
failed, causing all tee times to fall through to the ambiguous teeTime
string path, which set the Masters deadline 1 hour late (7:40 CT vs 6:40 CT)."
```

---

### Task 3: Add defensive logging for timezone fallback

**Files:**
- Modify: `sync_api.py:358-366` (`_get_event_timezone`)
- Modify: `sync_api.py:598-599` (field sync method)
- Modify: `tests/test_tee_time_parsing.py`

This task doesn't change behavior — it adds a warning log when no timezone is found in the API response AND the code falls through to the `teeTime` string path. This makes the next occurrence of this class of bug immediately visible in logs.

- [ ] **Step 1: Add a test for the warning scenario**

Append to `tests/test_tee_time_parsing.py`:

```python
class TestGetEventTimezone:
    """Tests for _get_event_timezone fallback behavior."""

    def test_returns_league_tz_when_no_timezone_field(self):
        from models import LEAGUE_TZ
        result = TournamentSync._get_event_timezone({})
        assert result == LEAGUE_TZ

    def test_returns_event_tz_when_present(self):
        result = TournamentSync._get_event_timezone({"timeZone": "America/New_York"})
        assert result == pytz.timezone("America/New_York")

    def test_tries_multiple_key_names(self):
        result = TournamentSync._get_event_timezone({"tz": "US/Eastern"})
        assert result == pytz.timezone("US/Eastern")
```

- [ ] **Step 2: Run tests to verify they pass (existing behavior)**

Run: `python -m pytest tests/test_tee_time_parsing.py -v`
Expected: ALL PASS

- [ ] **Step 3: Add warning log to `_get_event_timezone`**

In `sync_api.py`, replace the `_get_event_timezone` method:

```python
    @staticmethod
    def _get_event_timezone(leaderboard_data: Dict) -> pytz.timezone:
        tz_name = leaderboard_data.get("timeZone") or leaderboard_data.get("timezone") or leaderboard_data.get("tz")
        if tz_name:
            try:
                return pytz.timezone(tz_name)
            except Exception:
                logger.warning("Unknown timezone '%s', falling back to league TZ", tz_name)
        else:
            logger.debug("No timezone field in API response, using league TZ")
        return LEAGUE_TZ
```

- [ ] **Step 4: Run tests again**

Run: `python -m pytest tests/test_tee_time_parsing.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add sync_api.py tests/test_tee_time_parsing.py
git commit -m "chore: add timezone fallback tests and debug logging

Adds tests for _get_event_timezone behavior and a debug log when no
timezone field is present in the API response."
```

---

### Task 4: Manual verification with real API data

**Files:** None modified — verification only.

- [ ] **Step 1: Update `test_api.py` on PythonAnywhere to verify the fix**

After deploying, run this on PA to confirm the ISO string now parses correctly:

```python
from sync_api import TournamentSync
import pytz

# Simulate the exact data from today's API response
result = TournamentSync._parse_tee_time_timestamp("2026-04-09T11:40:00")
ct = result.astimezone(pytz.timezone("America/Chicago"))
print(f"Parsed: {result} UTC")
print(f"Central: {ct}")
print(f"Expected deadline: 6:40 AM CT")
print(f"Actual deadline:   {ct.strftime('%-I:%M %p')} CT")
assert ct.hour == 6 and ct.minute == 40, f"WRONG: got {ct.hour}:{ct.minute:02d}"
print("PASS - deadline would be correct")
```

Expected output:
```
Parsed: 2026-04-09 11:40:00+00:00 UTC
Central: 2026-04-09 06:40:00-05:00
Expected deadline: 6:40 AM CT
Actual deadline:   6:40 AM CT
PASS - deadline would be correct
```

- [ ] **Step 2: Deploy and verify**

Push to GitHub, pull on PA, verify the fix is live. The next field sync will use the corrected parser.

---

## Notes

- `_update_pick_deadline_from_leaderboard` (line 427) is dead code — defined but never called. It has the same tee time parsing pattern. Task 2's fix to `_parse_tee_time_timestamp` covers it since it calls the same static method. If you want to clean up the dead method, that's a separate task.
- The `_parse_tee_time` string fallback (line 402) still has the timezone ambiguity issue when `_get_event_timezone` returns LEAGUE_TZ. With Task 2's fix, this path should almost never execute since `teeTimeTimestamp` will now parse successfully. The debug logging from Task 3 will flag if it ever does.
