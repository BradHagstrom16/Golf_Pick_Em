"""Tests for stats.py — the Stats Hub aggregation layer.

These exercise the pure aggregation functions directly against a seeded DB.
Picks are populated with explicit resolved fields (points_earned, active_player_id,
backup_used, penalty_triggered) so the stats layer is tested independently of
resolve_pick() (which has its own suite).
"""
from datetime import datetime

import pytest

import stats


SEASON = 2026


@pytest.fixture
def seed(make_user, make_player, make_tournament, make_result, make_pick):
    """Build a small but representative completed season.

    Three members (alice, bob, carol), four completed events (one a major),
    plus a never-picked star to exercise untouched-stars / form-guide.
    """
    alice = make_user(username='alice', display_name='Alice')
    bob = make_user(username='bob', display_name='Bob')
    carol = make_user(username='carol', display_name='Carol')

    # Golfers
    scott = make_player(first_name='Scottie', last_name='Scheffler')
    rory = make_player(first_name='Rory', last_name='McIlroy')
    xander = make_player(first_name='Xander', last_name='Schauffele')
    backup = make_player(first_name='Backup', last_name='Guy')
    untouched = make_player(first_name='Ludvig', last_name='Aberg')  # never picked

    # Four completed events in chronological order; event 3 is a major.
    t1 = make_tournament(name='Sony Open', start_date=datetime(2026, 1, 8), purse=8_000_000)
    t2 = make_tournament(name='Genesis', start_date=datetime(2026, 2, 12), purse=20_000_000)
    t3 = make_tournament(name='The Masters', start_date=datetime(2026, 4, 9),
                         purse=20_000_000, is_major=True)
    t4 = make_tournament(name='Wells Fargo', start_date=datetime(2026, 5, 7), purse=9_000_000)

    tourneys = [t1, t2, t3, t4]

    # Full-field results (raw PGA prize money) for every golfer in each event.
    # earnings here is the RAW player prize, not league points.
    field_results = {
        # player: per-event (status, position, earnings)
        scott:     [('complete', '1', 2_000_000), ('complete', '2', 1_200_000),
                    ('complete', '1', 4_000_000), ('complete', 'T3', 600_000)],
        rory:      [('complete', 'T5', 400_000), ('complete', '1', 3_600_000),
                    ('cut', 'CUT', 0), ('complete', '2', 1_000_000)],
        xander:    [('complete', 'T10', 200_000), ('complete', 'T20', 90_000),
                    ('complete', 'T8', 300_000), ('complete', 'T15', 120_000)],
        backup:    [('complete', 'T30', 40_000), ('complete', 'T40', 25_000),
                    ('complete', 'T50', 18_000), ('complete', 'T45', 22_000)],
        untouched: [('complete', '2', 1_100_000), ('complete', 'T3', 700_000),
                    ('complete', 'T5', 500_000), ('complete', '1', 1_600_000)],
    }
    for player, rows in field_results.items():
        for tourn, (st, pos, earn) in zip(tourneys, rows):
            make_result(tourn, player, status=st, final_position=pos, earnings=earn)

    # Picks — explicit resolved fields. points_earned already includes any multiplier.
    # Alice: scott every week (the steady leader); event3 is a major so 4M*1.5 = 6M.
    make_pick(alice, t1, scott, backup, active_player_id=scott.id, points_earned=2_000_000)
    make_pick(alice, t2, scott, backup, active_player_id=scott.id, points_earned=1_200_000)
    make_pick(alice, t3, scott, backup, active_player_id=scott.id, points_earned=6_000_000)  # major 4M*1.5
    make_pick(alice, t4, scott, backup, active_player_id=scott.id, points_earned=600_000)

    # Bob: rory; event3 major rory was CUT -> 0 pts + penalty; event2 rory won 3.6M.
    make_pick(bob, t1, rory, backup, active_player_id=rory.id, points_earned=400_000)
    make_pick(bob, t2, rory, backup, active_player_id=rory.id, points_earned=3_600_000)
    make_pick(bob, t3, rory, xander, active_player_id=rory.id, points_earned=0,
              penalty_triggered=True)
    make_pick(bob, t4, rory, backup, active_player_id=rory.id, points_earned=1_000_000)

    # Carol: xander; in t2 her primary WD'd early so backup activated (backup_used).
    make_pick(carol, t1, xander, backup, active_player_id=xander.id, points_earned=200_000)
    make_pick(carol, t2, xander, backup, active_player_id=backup.id, points_earned=25_000,
              backup_used=True)
    make_pick(carol, t3, xander, backup, active_player_id=xander.id, points_earned=300_000)
    make_pick(carol, t4, xander, backup, active_player_id=xander.id, points_earned=120_000)

    return {
        'users': {'alice': alice, 'bob': bob, 'carol': carol},
        'players': {'scott': scott, 'rory': rory, 'xander': xander,
                    'backup': backup, 'untouched': untouched},
        'tournaments': tourneys,
    }


# --------------------------------------------------------------------------
# season_progress
# --------------------------------------------------------------------------
def test_season_progress_counts(seed, make_tournament):
    make_tournament(name='Upcoming', status='upcoming', start_date=datetime(2026, 6, 1))
    prog = stats.season_progress(SEASON)
    assert prog['completed'] == 4
    assert prog['total'] == 5


def test_season_progress_empty(db):
    prog = stats.season_progress(SEASON)
    assert prog == {'completed': 0, 'total': 0}


# --------------------------------------------------------------------------
# season_race
# --------------------------------------------------------------------------
def test_season_race_cumulative_and_leader(seed):
    race = stats.season_race(SEASON)
    assert race['count'] == 4
    assert [t['name'] for t in race['tournaments']] == [
        'Sony Open', 'Genesis', 'The Masters', 'Wells Fargo']

    by_name = {s['name']: s for s in race['series']}
    # Alice cumulative: 2.0, 3.2, 9.2, 9.8 (millions)
    assert by_name['Alice']['cumulative'] == [2_000_000, 3_200_000, 9_200_000, 9_800_000]
    assert by_name['Alice']['final'] == 9_800_000
    # Bob: 0.4, 4.0, 4.0, 5.0
    assert by_name['Bob']['cumulative'] == [400_000, 4_000_000, 4_000_000, 5_000_000]
    # Carol: 0.2, 0.225, 0.525, 0.645
    assert by_name['Carol']['cumulative'][-1] == 645_000

    # Series sorted by final desc; Alice leads.
    assert race['series'][0]['name'] == 'Alice'
    assert race['series'][0]['is_leader'] is True
    assert race['series'][0]['rank'] == 1
    assert race['max_value'] == 9_800_000


def test_season_race_empty(db):
    race = stats.season_race(SEASON)
    assert race['count'] == 0
    assert race['series'] == []
    assert race['tournaments'] == []
    assert race['max_value'] == 0


def test_season_race_single_event(make_user, make_player, make_tournament, make_pick):
    u = make_user(username='solo', display_name='Solo')
    p = make_player()
    b = make_player()
    t = make_tournament(name='Opener', start_date=datetime(2026, 1, 8))
    make_pick(u, t, p, b, active_player_id=p.id, points_earned=500_000)
    race = stats.season_race(SEASON)
    assert race['count'] == 1
    assert race['series'][0]['cumulative'] == [500_000]
    assert race['series'][0]['final'] == 500_000


# --------------------------------------------------------------------------
# superlatives
# --------------------------------------------------------------------------
def test_superlatives_pick_of_season(seed):
    sup = stats.superlatives(SEASON)
    pos = sup['pick_of_season']
    assert pos['member'] == 'Alice'
    assert pos['amount'] == 6_000_000  # the major (multiplied) pick
    assert 'Scheffler' in pos['golfer']
    assert pos['event'] == 'The Masters'


def test_superlatives_most_cuts(seed):
    sup = stats.superlatives(SEASON)
    # Bob's active pick (rory) was CUT at the Masters -> 1 cut, the most.
    assert sup['most_cuts']['member'] == 'Bob'
    assert sup['most_cuts']['count'] == 1


def test_superlatives_wd_survivor(seed):
    sup = stats.superlatives(SEASON)
    assert sup['wd_survivor']['member'] == 'Carol'
    assert sup['wd_survivor']['count'] == 1


def test_superlatives_most_cashes(seed):
    sup = stats.superlatives(SEASON)
    # Alice and Carol both cashed all 4 weeks; Bob only 3 (one $0 week).
    assert sup['most_cashes']['cashes'] == 4
    assert sup['most_cashes']['member'] in ('Alice', 'Carol')


def test_superlatives_empty(db):
    sup = stats.superlatives(SEASON)
    assert sup['pick_of_season'] is None
    assert sup['most_cuts'] is None


# --------------------------------------------------------------------------
# field_form
# --------------------------------------------------------------------------
def test_field_form_guide_orders_by_prize(seed):
    form = stats.field_form(SEASON)
    guide = form['form_guide']
    # Scheffler total raw prize = 2.0+1.2+4.0+0.6 = 7.8M, the top earner.
    assert guide[0]['golfer'].endswith('Scheffler')
    assert guide[0]['prize'] == 7_800_000
    assert guide[0]['events'] == 4
    assert guide[0]['cuts'] == 0
    assert guide[0]['best_finish'] == '1'
    # Rory had a CUT -> cuts == 1 somewhere in the guide.
    rory_row = next(r for r in guide if r['golfer'].endswith('McIlroy'))
    assert rory_row['cuts'] == 1


def test_field_form_most_picked_and_return(seed):
    form = stats.field_form(SEASON)
    mp = {r['golfer']: r for r in form['most_picked']}
    # Each of scott/rory/xander was the active pick 4 times.
    scott_row = next(r for g, r in mp.items() if g.endswith('Scheffler'))
    assert scott_row['times_picked'] == 4
    assert scott_row['total_return'] == 9_800_000  # Alice's season from scott


def test_field_form_untouched_stars(seed):
    form = stats.field_form(SEASON)
    names = [r['golfer'] for r in form['untouched_stars']]
    # Aberg was never picked (primary or backup) and earned well -> appears.
    assert any(n.endswith('Aberg') for n in names)
    # Scheffler was picked, so must NOT appear in untouched.
    assert not any(n.endswith('Scheffler') for n in names)


# --------------------------------------------------------------------------
# personal_scorecard
# --------------------------------------------------------------------------
def test_personal_scorecard(seed):
    bob = seed['users']['bob']
    # total_points isn't auto-summed in this seed; set it for rank realism.
    alice, carol = seed['users']['alice'], seed['users']['carol']
    alice.total_points = 9_800_000
    bob.total_points = 5_000_000
    carol.total_points = 645_000

    card = stats.personal_scorecard(bob, SEASON)
    assert card['rank'] == 2
    assert card['events_played'] == 4
    assert card['cashes'] == 3            # one $0 week (the major cut)
    assert card['cuts_at_majors'] == 1    # penalty_triggered once
    assert card['best_pick']['amount'] == 3_600_000
    assert card['best_pick']['golfer'].endswith('McIlroy')


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
@pytest.mark.parametrize('value,expected', [
    (0, '$0'),
    (950, '$950'),
    (25_000, '$25K'),
    (1_200_000, '$1.2M'),
    (9_800_000, '$9.8M'),
])
def test_format_money_compact(value, expected):
    assert stats.format_money_compact(value) == expected


# --------------------------------------------------------------------------
# /stats route
# --------------------------------------------------------------------------
def test_stats_route_guest(seed, client):
    resp = client.get('/stats')
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert 'The Record Room' in body
    assert 'The Season Race' in body
    assert 'Your Scorecard' not in body          # personal panel hidden for guests


def test_stats_route_authenticated_shows_scorecard(seed, login):
    authed = login(seed['users']['bob'])
    resp = authed.get('/stats')
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert 'Your Scorecard' in body


def test_stats_route_empty_season(db, client):
    resp = client.get('/stats')
    assert resp.status_code == 200
    assert 'The race begins after the first event' in resp.get_data(as_text=True)


def test_race_chart_geometry_basic(seed):
    race = stats.season_race(SEASON)
    geo = stats.race_chart_geometry(race, current_user_id=seed['users']['alice'].id)
    # One line per series, each with a point per completed event.
    assert len(geo['lines']) == len(race['series'])
    alice_line = next(l for l in geo['lines'] if l['name'] == 'Alice')
    assert alice_line['role'] in ('you', 'leader')   # Alice is both you and leader here
    assert len(alice_line['points'].split()) == race['count']
    # y ticks exist and are within the drawing area.
    assert geo['y_ticks']
    assert all(geo['pad_top'] <= t['y'] <= geo['height'] - geo['pad_bottom'] + 0.01
               for t in geo['y_ticks'])
