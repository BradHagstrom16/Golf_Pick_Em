"""
Import 2026 Tournament Schedule
================================
One-time script to import the 32 tournaments from the CSV schedule.

Usage:
    python import_tournaments.py

This creates Tournament records with basic info. The API sync will
later populate fields, tee times, and results.
"""

import csv
from datetime import datetime, timedelta
from app import app, db
from models import Tournament

# Tournament data from the CSV
# Format: (date_str, name, is_team_event)
TOURNAMENTS_2026 = [
    ("1/15/2026", "Sony Open in Hawaii", False),
    ("1/22/2026", "The American Express", False),
    ("1/29/2026", "Farmers Insurance Open", False),
    ("2/5/2026", "WM Phoenix Open", False),
    ("2/12/2026", "AT&T Pebble Beach Pro-Am", False),
    ("2/19/2026", "The Genesis Invitational", False),
    ("2/26/2026", "Cognizant Classic", False),
    ("3/5/2026", "Arnold Palmer Invitational presented by Mastercard", False),
    ("3/12/2026", "THE PLAYERS Championship", False),
    ("3/19/2026", "Valspar Championship", False),
    ("3/26/2026", "Texas Children's Houston Open", False),
    ("4/2/2026", "Valero Texas Open", False),
    ("4/9/2026", "Masters Tournament", False),
    ("4/16/2026", "RBC Heritage", False),
    ("4/23/2026", "Zurich Classic of New Orleans", True),  # TEAM EVENT
    ("4/30/2026", "Cadillac Championship", False),
    ("5/7/2026", "Truist Championship", False),
    ("5/14/2026", "PGA Championship", False),
    ("5/21/2026", "THE CJ CUP Byron Nelson", False),
    ("5/28/2026", "Charles Schwab Challenge", False),
    ("6/4/2026", "the Memorial Tournament presented by Workday", False),
    ("6/11/2026", "RBC Canadian Open", False),
    ("6/18/2026", "U.S. Open", False),
    ("6/25/2026", "Travelers Championship", False),
    ("7/2/2026", "John Deere Classic", False),
    ("7/9/2026", "Genesis Scottish Open", False),
    ("7/16/2026", "The Open Championship", False),
    ("7/23/2026", "3M Open", False),
    ("7/30/2026", "Rocket Classic", False),
    ("8/6/2026", "Wyndham Championship", False),
    ("8/13/2026", "FedEx St. Jude Championship", False),
    ("8/20/2026", "BMW Championship", False),
]

# Approximate purse amounts (can be updated when API provides actual data)
PURSE_ESTIMATES = {
    'Sony Open in Hawaii': 9_100_000,
    'The American Express': 9_200_000,
    'Farmers Insurance Open': 9_600_000,
    'WM Phoenix Open': 9_600_000,
    'AT&T Pebble Beach Pro-Am': 20_000_000,
    'The Genesis Invitational': 20_000_000,
    'Cognizant Classic': 9_600_000,
    'Arnold Palmer Invitational presented by Mastercard': 20_000_000,
    'THE PLAYERS Championship': 25_000_000,
    'Valspar Championship': 9_100_000,
    "Texas Children's Houston Open": 9_900_000,
    'Valero Texas Open': 9_800_000,
    'Masters Tournament': None,  # TBD - Major
    'RBC Heritage': 20_000_000,
    'Zurich Classic of New Orleans': 9_500_000,
    'Cadillac Championship': 20_000_000,
    'Truist Championship': 20_000_000,
    'PGA Championship': None,  # TBD - Major
    'THE CJ CUP Byron Nelson': 10_300_000,
    'Charles Schwab Challenge': 9_900_000,
    'the Memorial Tournament presented by Workday': 20_000_000,
    'RBC Canadian Open': 9_800_000,
    'U.S. Open': None,  # TBD - Major
    'Travelers Championship': 20_000_000,
    'John Deere Classic': 8_800_000,
    'Genesis Scottish Open': 9_000_000,
    'The Open Championship': None,  # TBD - Major
    '3M Open': 8_800_000,
    'Rocket Classic': 10_000_000,
    'Wyndham Championship': 8_500_000,
    'FedEx St. Jude Championship': 20_000_000,
    'BMW Championship': 20_000_000,
}


def import_tournaments():
    """Import all 2026 tournaments into database."""

    with app.app_context():
        imported = 0
        updated = 0

        for week_num, (date_str, name, is_team) in enumerate(TOURNAMENTS_2026, start=1):
            # Parse start date
            start_date = datetime.strptime(date_str, "%m/%d/%Y")

            # End date is typically 3 days later (Thu-Sun)
            end_date = start_date + timedelta(days=3)

            # Get purse estimate
            purse = PURSE_ESTIMATES.get(name, 8_000_000)

            # Check if tournament already exists
            existing = Tournament.query.filter_by(
                name=name,
                season_year=2026
            ).first()

            if existing:
                # Update existing
                existing.start_date = start_date
                existing.end_date = end_date
                existing.purse = purse
                existing.is_team_event = is_team
                existing.week_number = week_num
                updated += 1
                print(f"  Updated: Week {week_num} - {name}")
            else:
                # Create new tournament
                tournament = Tournament(
                    api_tourn_id=f"2026_{week_num:02d}",  # Placeholder until API sync
                    name=name,
                    season_year=2026,
                    start_date=start_date,
                    end_date=end_date,
                    purse=purse,
                    is_team_event=is_team,
                    week_number=week_num,
                    status="upcoming"
                )
                db.session.add(tournament)
                imported += 1
                print(f"  Imported: Week {week_num} - {name}")

        db.session.commit()

        print(f"\n{'='*50}")
        print(f"Import Complete!")
        print(f"  New tournaments: {imported}")
        print(f"  Updated tournaments: {updated}")
        print(f"  Total: {len(TOURNAMENTS_2026)}")
        print(f"{'='*50}")

        # Show team event reminder
        print(f"\n⚠️  Remember: Zurich Classic (Week 15) is a team event!")
        print(f"   Earnings will be divided by 2 for picks in that tournament.")


def list_tournaments():
    """List all tournaments in database."""

    with app.app_context():
        tournaments = Tournament.query.filter_by(
            season_year=2026
        ).order_by(Tournament.week_number).all()

        print(f"\n2026 Tournament Schedule ({len(tournaments)} events)")
        print("=" * 70)

        for t in tournaments:
            team_flag = " [TEAM]" if t.is_team_event else ""
            print(f"Week {t.week_number:2d} | {t.start_date.strftime('%b %d')} | "
                  f"${t.purse:>12,} | {t.name}{team_flag}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "list":
        list_tournaments()
    else:
        print("Importing 2026 PGA Tour Schedule...")
        print("=" * 50)
        import_tournaments()
        print("\nTo view tournaments, run: python import_tournaments.py list")
