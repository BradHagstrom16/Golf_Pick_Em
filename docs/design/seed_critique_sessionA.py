"""Throwaway seed for the impeccable critique sweep (Session A).

Augments the existing rich 2026 dev DB:
- sets admin (Sun Day Regrets, id 1) password to the sweep credential
- repurposes U.S. Open (id 23) as an in-progress MAJOR this week
- seeds a live leaderboard (TournamentResult) + picks covering projected
  earnings, the 1.5x major flag, live missed-cut penalty (cut + dq), and a
  backup-activation (primary WD before R2).

Idempotent-ish: clears tournament 23's picks/results before reseeding.
"""
from datetime import datetime

from app import app, db
from models import User, Tournament, Player, TournamentResult, Pick

T_ID = 23  # U.S. Open

# (player_id, status, final_position, earnings, rounds_completed, score_to_par)
LEADERBOARD = [
    (1,  'active', 'T1',  2_800_000, 3, -10),
    (2,  'active', 'T2',  1_400_000, 3, -8),
    (3,  'active', 'T3',    900_000, 3, -7),
    (4,  'active', 'T4',    700_000, 3, -6),
    (5,  'active', 'T5',    560_000, 3, -5),
    (6,  'active', 'T6',    450_000, 3, -4),
    (7,  'active', 'T8',    360_000, 3, -3),
    (8,  'active', 'T10',   300_000, 3, -2),
    (9,  'active', 'T15',   200_000, 3, -1),
    (10, 'active', 'T20',   150_000, 3,  0),
    (15, 'active', 'T12',   250_000, 3, -1),  # backup earner for u3
    (11, 'cut',    'CUT',         0, 2,  2),
    (12, 'cut',    'CUT',         0, 2,  3),
    (13, 'cut',    'CUT',         0, 2,  4),
    (16, 'dq',     'DQ',          0, 2,  5),
    (14, 'wd',     'WD',          0, 1,  1),  # WD before R2 -> backup activates
]

# (user_id, primary_player_id, backup_player_id)
PICKS = [
    (1, 1,  2),    # admin: clean leader pick (projected ~2.8M, active major)
    (2, 11, 12),   # cut primary -> live penalty badge
    (3, 14, 15),   # primary WD R1 -> backup p15 activates (backup icon, T12)
    (4, 3,  20),   # active T3, 900k projected
    (5, 5,  6),    # active T5, 560k projected
    (6, 16, 17),   # dq primary -> live penalty badge (dq variant)
    (7, 8,  9),    # active T10, 300k projected
    (8, 2,  10),   # active T2, 1.4M projected
]

with app.app_context():
    # 1. Admin password
    admin = db.session.get(User, 1)
    assert admin and admin.username == 'Sun Day Regrets' and admin.is_admin, admin
    admin.set_password('CritiqueSweep!2026')

    # 2. Repurpose tournament 23 as in-progress major (this week)
    t = db.session.get(Tournament, T_ID)
    assert t and t.is_major, t
    t.status = 'active'
    t.results_finalized = False
    t.start_date = datetime(2026, 5, 21, 0, 0)     # naive CT
    t.end_date = datetime(2026, 5, 31, 23, 59)      # spans "now" (2026-05-26)
    t.pick_deadline = datetime(2026, 5, 21, 6, 30)  # passed -> show_picks True
    # purse stays 0 -> effective_purse uses PURSE_ESTIMATES ($21.5M, est. badge)

    # 3. Wipe + reseed tournament 23 picks/results
    Pick.query.filter_by(tournament_id=T_ID).delete()
    TournamentResult.query.filter_by(tournament_id=T_ID).delete()
    db.session.flush()

    for pid, status, pos, earn, rc, stp in LEADERBOARD:
        assert db.session.get(Player, pid), f"missing player {pid}"
        db.session.add(TournamentResult(
            tournament_id=T_ID, player_id=pid, status=status,
            final_position=pos, earnings=earn, rounds_completed=rc, score_to_par=stp,
        ))
    db.session.flush()

    for uid, prim, back in PICKS:
        assert db.session.get(User, uid), f"missing user {uid}"
        db.session.add(Pick(
            user_id=uid, tournament_id=T_ID,
            primary_player_id=prim, backup_player_id=back,
        ))
    db.session.flush()

    # 4. Authentic live-penalty refresh (mirrors sync_live_leaderboard)
    for p in Pick.query.filter_by(tournament_id=T_ID).all():
        p.refresh_live_penalty()

    db.session.commit()

    # Report
    print("=== SEEDED ===")
    print(f"admin user id=1 '{admin.username}' password set")
    print(f"tournament {T_ID} '{t.name}' status={t.status} major={t.is_major} "
          f"purse={t.purse} eff_purse={t.effective_purse} est={t.purse_is_estimate} "
          f"deadline_passed={t.is_deadline_passed()}")
    print(f"results seeded: {TournamentResult.query.filter_by(tournament_id=T_ID).count()}")
    print(f"picks seeded: {Pick.query.filter_by(tournament_id=T_ID).count()}")
    pens = Pick.query.filter_by(tournament_id=T_ID, penalty_triggered=True).all()
    print(f"live penalties: {[(p.user_id, p.primary_player_id) for p in pens]}")
