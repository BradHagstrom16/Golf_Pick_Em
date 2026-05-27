"""Session B augment: make Charles Schwab (#20) a picks-open upcoming tournament.

- sets a realistic pick_deadline (Thu first tee) so make_pick is open + deadline shows
- seeds a ~60-player non-amateur field so the Tom Select dropdown populates
  (admin already has 18 used players → used-player lockout is exercised by exclusion)
"""
from datetime import datetime

from app import app, db
from models import Tournament, Player, TournamentField

T_ID = 20
FIELD_SIZE = 60

with app.app_context():
    t = db.session.get(Tournament, T_ID)
    assert t and t.status == 'upcoming', t
    t.pick_deadline = datetime(2026, 5, 28, 7, 0)  # Thu 7:00 AM CT (naive), future

    existing = {f.player_id for f in TournamentField.query.filter_by(tournament_id=T_ID)}
    players = (Player.query.filter_by(is_amateur=False)
               .order_by(Player.id).limit(FIELD_SIZE).all())
    added = 0
    for p in players:
        if p.id in existing:
            continue
        db.session.add(TournamentField(tournament_id=T_ID, player_id=p.id))
        added += 1
    db.session.commit()

    field_n = TournamentField.query.filter_by(tournament_id=T_ID).count()
    print("=== SESSION B AUGMENT ===")
    print(f"tournament {T_ID} '{t.name}' status={t.status} "
          f"deadline={t.pick_deadline} deadline_passed={t.is_deadline_passed()}")
    print(f"field players added={added}, total now={field_n}")
