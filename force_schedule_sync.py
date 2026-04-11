"""
Force Schedule Sync
===================
Runs sync_schedule() directly, bypassing the Monday-only gate in sync-run.
Use this to pick up a purse or other tournament data that was just announced
mid-week (e.g. Masters purse going live during tournament week).

Usage (on PythonAnywhere, venv active):
    python force_schedule_sync.py

Requirements:
    - SLASHGOLF_API_KEY must be set in env_config.sh (loaded by run_sync.sh)
      or exported in the environment before running.
    - Run from the project root: /home/GolfPickEm/Golf_Pick_Em
"""

import os
import sys
from app import app
from sync_api import TournamentSync, SlashGolfAPI
from models import Tournament

api_key = os.environ.get("SLASHGOLF_API_KEY")
if not api_key:
    print("ERROR: SLASHGOLF_API_KEY not set.")
    print("Source env_config.sh first, or run via run_sync.sh.")
    sys.exit(1)

SEASON_YEAR = 2026

with app.app_context():
    # Show current purse for all tournaments before sync
    print(f"--- Purses BEFORE sync ---")
    for t in Tournament.query.filter_by(season_year=SEASON_YEAR).order_by(Tournament.start_date).all():
        purse_str = f"${t.purse:>12,}" if t.purse else "         TBD"
        print(f"  {t.name:<55} {purse_str}")

    print()
    print("Running sync_schedule()...")
    api = SlashGolfAPI(api_key)
    sync = TournamentSync(api)
    updated = sync.sync_schedule(SEASON_YEAR)
    print(f"Done — {updated} tournaments updated.")

    # Show purses after sync so we can confirm any changes
    print()
    print(f"--- Purses AFTER sync ---")
    for t in Tournament.query.filter_by(season_year=SEASON_YEAR).order_by(Tournament.start_date).all():
        purse_str = f"${t.purse:>12,}" if t.purse else "         TBD"
        print(f"  {t.name:<55} {purse_str}")
