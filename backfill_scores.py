"""
Backfill score_to_par for Already-Finalized Tournaments
========================================================
One-time script to populate score_to_par on TournamentResult records
for tournaments that were finalized before the score_to_par feature existed.

This fetches the leaderboard endpoint for each finalized tournament and
updates the score_to_par field. Does NOT re-process picks or change earnings.

API Cost: 1 call per finalized tournament (e.g., 3 calls for 3 completed events)

Usage (on PythonAnywhere):
    cd ~/Golf_Pick_Em
    source ~/.virtualenvs/golfpickem/bin/activate
    source env_config.sh
    export FLASK_APP=app.py FLASK_ENV=production SYNC_MODE=free
    export DATABASE_URL="sqlite:///$(pwd)/golf_pickem.db"
    python backfill_scores.py

Or locally:
    python backfill_scores.py
"""

import os
import sys

# Ensure project is on path
PROJECT_HOME = os.path.dirname(os.path.abspath(__file__))
if PROJECT_HOME not in sys.path:
    sys.path.insert(0, PROJECT_HOME)

from app import app
from models import db, Tournament, TournamentResult, Player
from sync_api import SlashGolfAPI, parse_score_to_par


def backfill():
    api_key = os.environ.get('SLASHGOLF_API_KEY')
    if not api_key:
        print("ERROR: SLASHGOLF_API_KEY not set")
        sys.exit(1)

    api = SlashGolfAPI(api_key, sync_mode='free')

    with app.app_context():
        # Find finalized tournaments
        finalized = Tournament.query.filter(
            Tournament.results_finalized == True,
            Tournament.status == 'complete'
        ).order_by(Tournament.start_date).all()

        if not finalized:
            print("No finalized tournaments found.")
            return

        print(f"Found {len(finalized)} finalized tournament(s) to backfill:\n")

        total_updated = 0
        total_api_calls = 0

        for tournament in finalized:
            # Check if any results are missing score_to_par
            missing_count = TournamentResult.query.filter(
                TournamentResult.tournament_id == tournament.id,
                TournamentResult.score_to_par.is_(None)
            ).count()

            total_results = TournamentResult.query.filter_by(
                tournament_id=tournament.id
            ).count()

            print(f"📋 {tournament.name}")
            print(f"   Results: {total_results} total, {missing_count} missing score_to_par")

            if missing_count == 0:
                print(f"   ✅ Already complete - skipping (no API call)\n")
                continue

            # Fetch leaderboard from API
            print(f"   🔄 Fetching leaderboard...")
            total_api_calls += 1
            data = api.get_leaderboard(tournament.api_tourn_id, str(tournament.season_year))

            if not data or "leaderboardRows" not in data:
                print(f"   ❌ Failed to fetch leaderboard\n")
                continue

            # Build lookup by player API ID
            lb_lookup = {}
            for row in data["leaderboardRows"]:
                lb_lookup[row["playerId"]] = row

            updated = 0
            for result in TournamentResult.query.filter_by(tournament_id=tournament.id).all():
                player = Player.query.get(result.player_id)
                if not player:
                    continue

                lb_info = lb_lookup.get(player.api_player_id, {})
                score = parse_score_to_par(lb_info.get("total"))

                if score is not None and result.score_to_par != score:
                    result.score_to_par = score
                    updated += 1

            db.session.commit()
            total_updated += updated
            print(f"   ✅ Updated {updated} results with score_to_par\n")

        print("=" * 50)
        print(f"Backfill complete!")
        print(f"  API calls used: {total_api_calls}")
        print(f"  Results updated: {total_updated}")
        print("=" * 50)


if __name__ == "__main__":
    backfill()
