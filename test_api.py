"""Verify tee time timestamp parsing fix (2026-04-09 Masters deadline bug)."""
from sync_api import TournamentSync
import pytz

# Simulate the exact data from the Masters API response
result = TournamentSync._parse_tee_time_timestamp("2026-04-09T11:40:00")
ct = result.astimezone(pytz.timezone("America/Chicago"))
print(f"Parsed: {result} UTC")
print(f"Central: {ct}")
print(f"Expected deadline: 6:40 AM CT")
print(f"Actual deadline:   {ct.strftime('%-I:%M %p')} CT")
assert ct.hour == 6 and ct.minute == 40, f"WRONG: got {ct.hour}:{ct.minute:02d}"
print("PASS - deadline would be correct")
