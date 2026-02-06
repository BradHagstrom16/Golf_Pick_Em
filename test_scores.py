"""Quick test script to populate fake score_to_par values for local testing."""

from app import app, db
from models import TournamentResult

with app.app_context():
    results = TournamentResult.query.filter(
        TournamentResult.final_position.isnot(None),
        TournamentResult.status == 'complete'
    ).limit(10).all()

    if not results:
        print("No completed results found in database.")
    else:
        for i, r in enumerate(results):
            r.score_to_par = -(20 - i * 2)  # Fake scores: -20, -18, -16, etc.
            print(f"  Set player {r.player_id} to {r.score_to_par}")

        db.session.commit()
        print(f"\nDone - updated {len(results)} results. Run 'flask run' to check the site.")
