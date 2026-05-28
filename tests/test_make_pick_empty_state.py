"""
Tests for the make_pick empty state.

When a tournament's field has not been synced (no TournamentField rows), the
route's ``available_players`` is empty. The template must not render a dead-end
form with empty dropdowns and a Submit button that can only fail; instead it
shows a "No golfers available yet" state with a way back.
"""
from models import TournamentField


def test_empty_field_shows_empty_state_not_form(db, login, make_user,
                                                make_tournament):
    """No field synced → empty-state message + Back action, and no pick form."""
    user = make_user(username='emptystate_user')

    # Upcoming tournament with no pick_deadline (is_deadline_passed() is False so
    # the route renders rather than redirecting) and NO field rows added.
    t = make_tournament(name='Unsynced Open', status='upcoming')

    client = login(user)
    resp = client.get(f'/pick/{t.id}')
    assert resp.status_code == 200, (
        f'Expected 200 but got {resp.status_code}; route may have redirected '
        '(check deadline/login).'
    )
    html = resp.get_data(as_text=True)

    # Empty state is shown, with context + a way back.
    assert 'No golfers available to pick yet' in html
    assert 'Back to My Picks' in html
    assert t.name in html  # tournament header preserved for context

    # The form must be suppressed: no player selects, no submit button.
    assert 'name="primary_player_id"' not in html
    assert 'name="backup_player_id"' not in html
    assert 'Submit Pick' not in html


def test_synced_field_renders_form_not_empty_state(db, login, make_user,
                                                   make_player, make_tournament):
    """Field present → the pick form renders and the empty state is absent."""
    user = make_user(username='synced_user')
    p1 = make_player(first_name='Tiger', last_name='Woods')
    p2 = make_player(first_name='Rory', last_name='McIlroy')

    t = make_tournament(name='Synced Open', status='upcoming')
    db.session.add(TournamentField(tournament_id=t.id, player_id=p1.id))
    db.session.add(TournamentField(tournament_id=t.id, player_id=p2.id))
    db.session.commit()

    client = login(user)
    resp = client.get(f'/pick/{t.id}')
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)

    assert 'name="primary_player_id"' in html
    assert 'name="backup_player_id"' in html
    assert 'No golfers available to pick yet' not in html
