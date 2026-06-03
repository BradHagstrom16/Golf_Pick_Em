"""
Tests: the make_pick masthead "The Field" figure uses consistent denominators.

When EDITING an existing pick, the route re-offers the current pick's golfers
in available_players (app.py removes them from used_player_ids). The masthead's
"N used" must count from that same adjusted list — recomputing it from
current_user.get_used_player_ids() in the template double-counts the in-flight
pick's golfers as both available AND used.
"""
from models import Pick, SeasonPlayerUsage, TournamentField


SEASON_YEAR = 2026


def _add_to_field(db, tournament, *players):
    for p in players:
        db.session.add(TournamentField(tournament_id=tournament.id, player_id=p.id))


def _mark_used(db, user, *players):
    for p in players:
        db.session.add(SeasonPlayerUsage(
            user_id=user.id, player_id=p.id, season_year=SEASON_YEAR))


def _get_pick_page(db, login, user, tournament):
    db.session.commit()
    client = login(user)
    resp = client.get(f'/pick/{tournament.id}')
    assert resp.status_code == 200
    return resp.get_data(as_text=True)


def test_editing_pick_does_not_double_count_reoffered_golfers(
        db, login, make_user, make_player, make_tournament, make_pick):
    """
    Field = {A, B, D}; usage rows lock A, B (the in-flight pick) and C (a past
    week). Editing re-offers A and B, so the masthead must read
    "3 available · 1 used" — only C stays used. Before the fix the template
    recounted all usage rows and showed "3 used".
    """
    user = make_user()
    a = make_player(last_name='Alpha')
    b = make_player(last_name='Bravo')
    c = make_player(last_name='Charlie')
    d = make_player(last_name='Delta')
    t = make_tournament(status='upcoming')  # no pick_deadline → editable

    _add_to_field(db, t, a, b, d)
    _mark_used(db, user, a, b, c)
    make_pick(user, t, primary=a, backup=b)

    html = _get_pick_page(db, login, user, t)
    assert '3 available' in html
    assert '1 used' in html
    assert '3 used' not in html


def test_fresh_pick_counts_unchanged(
        db, login, make_user, make_player, make_tournament):
    """No existing pick: available and used count exactly as before."""
    user = make_user()
    c = make_player(last_name='Charlie')
    d = make_player(last_name='Delta')
    e = make_player(last_name='Echo')
    t = make_tournament(status='upcoming')

    _add_to_field(db, t, d, e)
    _mark_used(db, user, c)

    html = _get_pick_page(db, login, user, t)
    assert '2 available' in html
    assert '1 used' in html


def test_editing_with_all_used_players_reoffered_hides_used_subline(
        db, login, make_user, make_player, make_tournament, make_pick):
    """
    When every locked golfer belongs to the in-flight pick, the adjusted used
    count is 0 and the "· N used" sub-span must not render at all.
    """
    user = make_user()
    a = make_player(last_name='Alpha')
    b = make_player(last_name='Bravo')
    d = make_player(last_name='Delta')
    t = make_tournament(status='upcoming')

    _add_to_field(db, t, a, b, d)
    _mark_used(db, user, a, b)
    make_pick(user, t, primary=a, backup=b)

    html = _get_pick_page(db, login, user, t)
    assert '3 available' in html
    assert 'used</span>' not in html
