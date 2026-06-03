"""Tests for the Burn List + remaining-% aggregation and routes.

Burn data is sourced from SeasonPlayerUsage — the same table that gates pick
availability — so burns exist only once a tournament is finalized. The seed
fixture in test_stats.py predates usage rows, so these tests build their own
small league: 4 registered users, of whom 3 have burned golfers.
"""
from datetime import datetime

import pytest

import stats
from models import db, SeasonPlayerUsage, TournamentField

SEASON = 2026


@pytest.fixture
def league(make_user, make_player, make_tournament, make_result, make_pick):
    """4 users: alice+bob burned scott, carol burned rory, dave never picked.

    Picks carry explicit resolved fields (active_player_id, points_earned), as
    in test_stats.py; usage rows mirror what resolve_pick() writes at
    finalization. Results exist so the Stats Hub's Field section renders.
    """
    alice = make_user(username='alice')
    bob = make_user(username='bob')
    carol = make_user(username='carol')
    dave = make_user(username='dave')          # registered, never picked

    scott = make_player(first_name='Scottie', last_name='Scheffler')
    rory = make_player(first_name='Rory', last_name='McIlroy')
    backup = make_player(first_name='Backup', last_name='Guy')

    t1 = make_tournament(name='Sony Open', start_date=datetime(2026, 1, 8))
    t2 = make_tournament(name='Genesis', start_date=datetime(2026, 2, 12))

    # Full-field results so field_form()['form_guide'] is non-empty (the
    # stats.html Field section is gated on it).
    make_result(t1, scott, earnings=2_000_000)
    make_result(t1, rory, final_position='T5', earnings=400_000)

    # Completed, resolved picks.
    make_pick(alice, t1, scott, backup, active_player_id=scott.id,
              points_earned=2_000_000)
    make_pick(bob, t2, scott, backup, active_player_id=scott.id,
              points_earned=1_200_000)
    make_pick(carol, t1, rory, backup, active_player_id=rory.id,
              points_earned=400_000)

    # Usage rows: what resolve_pick() writes at finalization.
    for user, player in ((alice, scott), (bob, scott), (carol, rory)):
        db.session.add(SeasonPlayerUsage(user_id=user.id, player_id=player.id,
                                         season_year=SEASON))
    db.session.flush()

    return {'users': {'alice': alice, 'bob': bob, 'carol': carol, 'dave': dave},
            'players': {'scott': scott, 'rory': rory, 'backup': backup},
            'tournaments': [t1, t2]}


# --------------------------------------------------------------------------
# burn_list
# --------------------------------------------------------------------------
def test_burn_list_counts_pct_and_return(league):
    rows = stats.burn_list(SEASON)
    by_name = {r['golfer']: r for r in rows}

    scott_row = by_name['Scottie Scheffler']
    assert scott_row['times_used'] == 2
    assert scott_row['pct_burned'] == 50           # 2 of 4 registered users
    assert scott_row['total_return'] == 3_200_000  # alice 2.0M + bob 1.2M

    rory_row = by_name['Rory McIlroy']
    assert rory_row['times_used'] == 1
    assert rory_row['pct_burned'] == 25
    assert rory_row['total_return'] == 400_000


def test_burn_list_orders_most_burned_first(league):
    rows = stats.burn_list(SEASON)
    assert [r['golfer'] for r in rows] == ['Scottie Scheffler', 'Rory McIlroy']


def test_burn_list_tie_breaks_by_return(league, make_player):
    """Equal burn % falls back to total return desc."""
    third = make_player(first_name='Justin', last_name='Thomas')
    for name in ('carol', 'dave'):
        db.session.add(SeasonPlayerUsage(user_id=league['users'][name].id,
                                         player_id=third.id,
                                         season_year=SEASON))
    db.session.flush()
    rows = stats.burn_list(SEASON)
    # scott (50%, $3.2M) before thomas (50%, $0), then rory (25%).
    assert [r['golfer'] for r in rows] == [
        'Scottie Scheffler', 'Justin Thomas', 'Rory McIlroy']


def test_burn_list_denominator_is_all_registered_users(league, make_user):
    """A pick-less account still dilutes the field: 2/4 = 50% -> 2/5 = 40%."""
    make_user(username='lurker')
    rows = stats.burn_list(SEASON)
    assert rows[0]['pct_burned'] == 40


def test_burn_list_pct_rounds_to_nearest_int(league, make_user):
    """7 registered users, 2 burns -> round(28.57) = 29."""
    for _ in range(3):
        make_user()
    rows = stats.burn_list(SEASON)
    assert rows[0]['pct_burned'] == 29


def test_burn_list_empty_season(db):
    assert stats.burn_list(SEASON) == []


def test_burn_list_ignores_in_flight_picks(league, make_tournament, make_pick):
    """An active-week pick is not burned: no usage row until finalization."""
    active = make_tournament(name='Live Event', status='active',
                             start_date=datetime(2026, 6, 1))
    make_pick(league['users']['carol'], active, league['players']['backup'],
              league['players']['scott'],
              active_player_id=league['players']['backup'].id)
    rows = stats.burn_list(SEASON)
    assert not any(r['golfer'] == 'Backup Guy' for r in rows)


def test_burn_list_usage_without_pick_returns_zero(league, make_player):
    """Admin-created usage with no matching completed pick still lists, $0."""
    ghost = make_player(first_name='Ghost', last_name='Entry')
    db.session.add(SeasonPlayerUsage(user_id=league['users']['dave'].id,
                                     player_id=ghost.id, season_year=SEASON))
    db.session.flush()
    ghost_row = next(r for r in stats.burn_list(SEASON)
                     if r['golfer'] == 'Ghost Entry')
    assert ghost_row['total_return'] == 0
    assert ghost_row['pct_burned'] == 25
