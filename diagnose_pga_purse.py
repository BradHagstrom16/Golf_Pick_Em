"""One-off diagnostic: what purse do the SlashGolf endpoints report for the
completed PGA Championship (tournId=033, 2026)? Read-only — no DB writes.

Run on PythonAnywhere:  python diagnose_pga_purse.py
"""
import os
from sync_api import SlashGolfAPI

TOURN_ID = "033"
YEAR = "2026"


def show(label, data):
    print(f"\n===== {label} =====")
    if not data:
        print("  (no data returned)")
        return
    if isinstance(data, dict):
        print("  top-level keys:", sorted(data.keys()))
        if "purse" in data:
            print("  >>> purse:", repr(data["purse"]))
        # schedule endpoint nests events under "schedule"
        events = data.get("schedule") or data.get("tournaments")
        if isinstance(events, list):
            for ev in events:
                if str(ev.get("tournId")) == TOURN_ID:
                    print("  >>> schedule event purse:", repr(ev.get("purse")),
                          "| name:", ev.get("name"))


def main():
    api_key = os.environ.get("SLASHGOLF_API_KEY")
    if not api_key:
        print("SLASHGOLF_API_KEY not set")
        return
    api = SlashGolfAPI(api_key, sync_mode=os.environ.get("SYNC_MODE", "standard"))

    show("schedule(2026)", api.get_schedule(YEAR))
    show("leaderboard(033, 2026)", api.get_leaderboard(TOURN_ID, YEAR))
    show("earnings(033, 2026)", api.get_earnings(TOURN_ID, YEAR))


if __name__ == "__main__":
    main()
