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


def test_field_form_untouched_stars(seed):
    form = stats.field_form(SEASON)
    names = [r['golfer'] for r in form['untouched_stars']]
    # Aberg was never picked (primary or backup) and earned well -> appears.
    assert any(n.endswith('Aberg') for n in names)
    # Scheffler was picked, so must NOT appear in untouched.
    assert not any(n.endswith('Scheffler') for n in names)


def test_field_form_untouched_ignores_upcoming_picks(seed, make_tournament, make_pick):
    """A golfer pencilled in only for a not-yet-played event stays "on the board".

    untouched-stars is a season retrospective (status='complete'); a pick in an
    upcoming tournament must not remove a golfer from the list.
    """
    aberg = seed['players']['untouched']
    assert any(r['golfer'].endswith('Aberg') for r in stats.field_form(SEASON)['untouched_stars'])

    upcoming = make_tournament(name='Next Week', status='upcoming',
                               start_date=datetime(2026, 7, 1))
    make_pick(seed['users']['alice'], upcoming, aberg, seed['players']['scott'])

    names = [r['golfer'] for r in stats.field_form(SEASON)['untouched_stars']]
    assert any(n.endswith('Aberg') for n in names)


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


def test_personal_scorecard_rank_is_season_scoped(make_user, make_player,
                                                  make_tournament, make_pick):
    """Rank/total reflect THIS season's points, not the app-wide User.total_points."""
    # A carries a big lifetime tally but a small this-season haul; B is the reverse.
    vet = make_user(username='vet', display_name='Vet', total_points=50_000_000)
    rook = make_user(username='rook', display_name='Rook', total_points=100)
    p1, p2, bk = make_player(), make_player(), make_player()
    t = make_tournament(name='Opener', start_date=datetime(2026, 1, 8))
    make_pick(vet, t, p1, bk, active_player_id=p1.id, points_earned=100)
    make_pick(rook, t, p2, bk, active_player_id=p2.id, points_earned=5_000_000)

    assert stats.personal_scorecard(rook, SEASON)['rank'] == 1
    vet_card = stats.personal_scorecard(vet, SEASON)
    assert vet_card['rank'] == 2
    assert vet_card['total'] == 100   # season points, not the 50M lifetime total


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


@pytest.mark.parametrize('value,axis_max', [
    (2_195_000, 2_500_000),   # raw step 548,750 -> snaps to a $500K grid
    (9_800_000, 10_000_000),  # snaps to a $2M grid topping out at $10M
    (500_000, 500_000),       # already round; top tick equals the data
    (0, 1),                   # empty season guard: a sane 0..1 axis
])
def test_nice_axis_max(value, axis_max):
    assert stats._nice_axis(value)[0] == axis_max


def test_nice_axis_step_divides_axis_evenly():
    axis_max, step = stats._nice_axis(2_195_000)
    assert step == 500_000
    assert axis_max % step == 0


def _fake_race(finals, shorts, names=None):
    """Minimal race payload for pure-geometry tests (no DB)."""
    count = len(shorts)
    series = [{
        'user_id': i + 1, 'name': names[i] if names else f'U{i}',
        'cumulative': [finals[i]] * count, 'final': finals[i],
        'is_leader': i == 0, 'rank': i + 1,
    } for i in range(len(finals))]
    return {
        'tournaments': [{'short': s, 'name': f'Event {j}'} for j, s in enumerate(shorts)],
        'series': series, 'max_value': max(finals), 'count': count,
    }


def test_race_chart_yticks_are_round_money():
    geo = stats.race_chart_geometry(_fake_race([2_195_000], ['Jan']))
    values = [t['value'] for t in geo['y_ticks']]
    assert values[0] == 0
    assert values[-1] >= 2_195_000               # top gridline clears the data
    assert values == [0, 500_000, 1_000_000, 1_500_000, 2_000_000, 2_500_000]
    # leader's final sits below the top gridline (headroom), not pinned to pad_top
    leader = geo['lines'][0]
    assert leader['end_y'] > geo['pad_top']


def test_race_chart_xticks_dedupe_consecutive_months():
    geo = stats.race_chart_geometry(_fake_race([3, 2], ['Mar', 'Mar', 'Apr']))
    labels = [t['label'] for t in geo['x_ticks']]
    assert labels == ['Mar', 'Apr']             # the second 'Mar' is collapsed


def test_race_endlabels_separate_when_neck_and_neck():
    # You trail the leader by a sliver: the two name labels must not overlap.
    geo = stats.race_chart_geometry(
        _fake_race([10_000_000, 9_950_000], ['Jan', 'Feb']), current_user_id=2)
    leader = next(line for line in geo['lines'] if line['role'] == 'leader')
    you = next(line for line in geo['lines'] if line['role'] == 'you')
    assert you['label_y'] - leader['label_y'] >= stats.LABEL_MIN_SEP - 0.01
    for line in (leader, you):
        assert geo['pad_top'] <= line['label_y'] <= geo['baseline_y']


def test_race_endlabels_untouched_when_far_apart():
    # No collision, no nudge: labels keep the plain end-of-line offset.
    geo = stats.race_chart_geometry(
        _fake_race([10_000_000, 2_000_000], ['Jan', 'Feb']), current_user_id=2)
    for line in geo['lines']:
        assert line['label_y'] == pytest.approx(line['end_y'] + 3)


def test_race_endlabels_separated_even_when_tied_at_axis_top():
    # Dead heat at the axis ceiling: spreading would push the upper label above
    # the plot, so the pair shifts down together instead of re-overlapping.
    geo = stats.race_chart_geometry(
        _fake_race([10_000_000, 10_000_000], ['Jan', 'Feb']), current_user_id=2)
    ys = sorted(line['label_y'] for line in geo['lines']
                if line['role'] in ('leader', 'you'))
    assert ys[1] - ys[0] >= stats.LABEL_MIN_SEP - 0.01
    assert ys[0] >= geo['pad_top']


def test_race_yticks_zero_has_no_label():
    # $0 stays as a gridline but loses its text: the baseline + month row
    # already read as the floor, and an inside label would collide with lines.
    geo = stats.race_chart_geometry(_fake_race([2_195_000], ['Jan']))
    assert geo['y_ticks'][0]['value'] == 0
    assert geo['y_ticks'][0]['label'] == ''
    assert all(t['label'] for t in geo['y_ticks'][1:])


def test_race_pad_right_grows_for_long_names():
    # A long labeled name widens the right gutter so it can't hang off the card.
    geo = stats.race_chart_geometry(
        _fake_race([5, 3], ['Jan', 'Feb'], names=['Sux Day Regrets', 'Bo']),
        current_user_id=2)
    assert geo['pad_right'] > 78
    # the last event stop still lands exactly at the plot's right edge
    assert geo['replay']['events'][-1]['x'] == geo['width'] - geo['pad_right']


def test_race_pad_right_ignores_pack_names():
    # Only labeled lines (you/leader) reserve gutter space; pack lines have no
    # labels, so a long pack name must not widen the gutter vs short names.
    short = stats.race_chart_geometry(
        _fake_race([5, 3, 1], ['Jan', 'Feb'], names=['Bo', 'Al', 'Cy']),
        current_user_id=2)
    long_pack = stats.race_chart_geometry(
        _fake_race([5, 3, 1], ['Jan', 'Feb'], names=['Bo', 'Al', 'A Very Long Pack Name']),
        current_user_id=2)
    assert long_pack['pad_right'] == short['pad_right']


def test_race_pad_right_caps_for_extreme_names():
    # The gutter grows for long names but stops at 150 so one extreme display
    # name can't crush the plot to a sliver.
    geo = stats.race_chart_geometry(
        _fake_race([5, 3], ['Jan', 'Feb'], names=['A' * 30, 'Bo']),
        current_user_id=2)
    assert geo['pad_right'] == 150


def test_race_endlabel_no_nudge_for_single_labeled_line_logged_out():
    # Anonymous viewer: only the leader carries a label — the collision guard
    # has no pair to separate and must leave label_y at the plain offset.
    geo = stats.race_chart_geometry(_fake_race([10_000_000, 9_950_000], ['Jan', 'Feb']))
    roles = [line['role'] for line in geo['lines']]
    assert roles.count('leader') == 1 and 'you' not in roles
    for line in geo['lines']:
        assert line['label_y'] == pytest.approx(line['end_y'] + 3)


def test_race_endlabel_no_nudge_when_you_are_the_leader():
    # The leader's own view: their line is 'you' and no separate 'leader' line
    # exists, so there is exactly one labeled line and no nudge fires.
    geo = stats.race_chart_geometry(
        _fake_race([10_000_000, 9_950_000], ['Jan', 'Feb']), current_user_id=1)
    roles = [line['role'] for line in geo['lines']]
    assert roles.count('you') == 1 and 'leader' not in roles
    for line in geo['lines']:
        assert line['label_y'] == pytest.approx(line['end_y'] + 3)


def test_race_endlabels_shift_up_when_tied_at_the_baseline():
    # Dead heat at $0: spreading pushes the lower label below the plot floor,
    # so the pair shifts up together (the symmetric branch to the axis-top clamp).
    geo = stats.race_chart_geometry(_fake_race([0, 0], ['Jan', 'Feb']), current_user_id=2)
    ys = sorted(line['label_y'] for line in geo['lines']
                if line['role'] in ('leader', 'you'))
    assert ys[1] - ys[0] >= stats.LABEL_MIN_SEP - 0.01
    assert ys[1] <= geo['baseline_y'] - 4 + 0.01


def test_race_single_event_x_geometry():
    # Week 1 of the season: a single completed event collapses all x-coords to
    # the left edge of the plot.
    geo = stats.race_chart_geometry(_fake_race([500_000], ['Jan']))
    assert geo['lines'][0]['end_x'] == geo['pad_left']
    assert geo['x_ticks'][0]['x'] == geo['pad_left']


def test_race_chart_geometry_basic(seed):
    race = stats.season_race(SEASON)
    geo = stats.race_chart_geometry(race, current_user_id=seed['users']['alice'].id)
    # One line per series, each with a point per completed event.
    assert len(geo['lines']) == len(race['series'])
    alice_line = next(line for line in geo['lines'] if line['name'] == 'Alice')
    assert alice_line['role'] in ('you', 'leader')   # Alice is both you and leader here
    assert len(alice_line['points'].split()) == race['count']
    # y ticks exist and are within the drawing area.
    assert geo['y_ticks']
    assert all(geo['pad_top'] <= t['y'] <= geo['height'] - geo['pad_bottom'] + 0.01
               for t in geo['y_ticks'])


# --------------------------------------------------------------------------
# race_chart_geometry — replay payload (powers the client-side "Play the season")
# --------------------------------------------------------------------------
def test_race_chart_replay_payload(seed):
    race = stats.season_race(SEASON)
    geo = stats.race_chart_geometry(race, current_user_id=seed['users']['alice'].id)
    replay = geo['replay']
    assert replay is not None
    assert replay['count'] == 4

    # One event stop per completed event, in chronological order, each x in-bounds.
    assert [e['name'] for e in replay['events']] == [
        'Sony Open', 'Genesis', 'The Masters', 'Wells Fargo']
    assert [e['short'] for e in replay['events']] == ['Jan', 'Feb', 'Apr', 'May']
    assert replay['events'][0]['x'] == geo['pad_left']
    assert replay['events'][-1]['x'] == geo['width'] - geo['pad_right']

    # One line per member, with coords + cumulative aligned to the event count.
    assert len(replay['lines']) == len(race['series'])
    alice = next(line for line in replay['lines'] if line['name'] == 'Alice')
    assert len(alice['coords']) == 4
    assert alice['cumulative'] == [2_000_000, 3_200_000, 9_200_000, 9_800_000]
    assert alice['role'] in ('you', 'leader')

    # The replay coords must agree exactly with the SVG polyline points string
    # (single source of truth: the dots ride the same line the browser draws).
    geo_alice = next(line for line in geo['lines'] if line['name'] == 'Alice')
    parsed = [[float(x), float(y)]
              for x, y in (p.split(',') for p in geo_alice['points'].split())]
    assert parsed == [list(c) for c in alice['coords']]


def test_race_chart_replay_keeps_every_event_stop():
    # x_ticks dedupe consecutive months for the axis, but the replay timeline
    # must keep a stop for every event (two events in March = two stops).
    geo = stats.race_chart_geometry(_fake_race([3, 2], ['Mar', 'Mar', 'Apr']))
    assert [e['short'] for e in geo['replay']['events']] == ['Mar', 'Mar', 'Apr']


def test_race_chart_replay_none_for_single_event():
    # Nothing to scrub through with a single event — controls never appear.
    geo = stats.race_chart_geometry(_fake_race([500_000], ['Jan']))
    assert geo['replay'] is None


def test_stats_renders_with_completed_events_but_no_picks(
        client, make_user, make_player, make_tournament, make_result):
    """Completed events + zero resolved picks must not 500 (empty race.series)."""
    make_user()
    star = make_player(first_name='Solo', last_name='Star')
    make_result(make_tournament(name='Opener'), star, earnings=1_000_000)
    resp = client.get('/stats')
    assert resp.status_code == 200
    assert 'The race begins after the first event' in resp.get_data(as_text=True)
