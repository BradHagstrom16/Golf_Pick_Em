"""
Tests: the major-stakes band ("Majors pay 1.5x. A missed cut owes $15 to the pot.")

The band is the only surface that communicates the 1.5x multiplier AND the $15
missed-cut penalty at decision time (the pick masthead) and on the tournament
detail masthead. Both renders gate on tournament.is_major; the negative case
(band absent on a regular event) is the most likely to rot, so it is pinned too.
"""

STAKES_TEXT = 'Majors pay 1.5'


def test_pick_page_shows_stakes_band_for_major(db, client, make_user, make_tournament, login):
    user = make_user()
    major = make_tournament(name='US Open', is_major=True, status='upcoming')
    login(user)
    html = client.get(f'/pick/{major.id}').get_data(as_text=True)
    assert 'major-stakes' in html
    assert STAKES_TEXT in html
    assert '$15' in html


def test_pick_page_hides_stakes_band_for_regular_event(db, client, make_user, make_tournament, login):
    user = make_user()
    regular = make_tournament(name='Travelers', is_major=False, status='upcoming')
    login(user)
    html = client.get(f'/pick/{regular.id}').get_data(as_text=True)
    assert 'major-stakes' not in html


def test_tournament_detail_shows_stakes_band_for_major(db, client, make_user, make_tournament, login):
    user = make_user()
    major = make_tournament(name='The Masters', is_major=True, status='upcoming')
    login(user)
    html = client.get(f'/tournament/{major.id}').get_data(as_text=True)
    assert 'major-stakes' in html
    assert STAKES_TEXT in html
    assert '$15' in html


def test_tournament_detail_hides_stakes_band_for_regular_event(db, client, make_user, make_tournament, login):
    user = make_user()
    regular = make_tournament(name='Travelers', is_major=False, status='upcoming')
    login(user)
    html = client.get(f'/tournament/{regular.id}').get_data(as_text=True)
    assert 'major-stakes' not in html
