"""
Tests for make_pick.html JS behavior (static analysis of rendered HTML).

The Flask test client cannot run JavaScript, so this test verifies the
rendered HTML source for the presence/absence of specific JS patterns.

Fix 1.5: same-player collision handled by live option exclusion (no alert/wipe).
Fix 1.8: punctuated-name search via normalizeSearch score factory.
"""
import pytest
from datetime import datetime, timedelta, timezone

from models import TournamentField


def _make_upcoming_tournament(make_tournament):
    """Return a tournament with no pick_deadline (deadline never passes)."""
    return make_tournament(
        name='Test Open',
        status='upcoming',
        # pick_deadline=None → is_deadline_passed() returns False → form renders
    )


def test_make_pick_has_no_destructive_alert(db, login, make_user, make_player,
                                            make_tournament):
    """
    The same-player guard must use live option exclusion, not alert()+clear().

    Before the fix: alert( appears in the rendered HTML → assert fails.
    After the fix:  excludeFrom + score are present, alert( is absent.
    """
    # --- Seed -----------------------------------------------------------------
    admin = make_user(username='picktest_admin', is_admin=True)

    # Two field players (non-amateur) so available_players is non-empty
    p1 = make_player(first_name='Tiger', last_name='Woods')
    p2 = make_player(first_name='Rory', last_name='McIlroy')

    # Tournament with no pick_deadline → is_deadline_passed() returns False
    t = _make_upcoming_tournament(make_tournament)

    # Add both players to the tournament field
    db.session.add(TournamentField(tournament_id=t.id, player_id=p1.id))
    db.session.add(TournamentField(tournament_id=t.id, player_id=p2.id))
    db.session.commit()

    # --- Request --------------------------------------------------------------
    client = login(admin)
    resp = client.get(f'/pick/{t.id}')
    assert resp.status_code == 200, (
        f'Expected 200 but got {resp.status_code}. '
        'Route may have redirected — check deadline or login state.'
    )

    html = resp.get_data(as_text=True)

    # Fix 1.5: no destructive alert
    assert 'alert(' not in html, (
        'same-player guard must not use a native alert() that wipes the field'
    )

    # Fix 1.5: live-filter helper must be present
    assert 'excludeFrom' in html, (
        'live option-exclusion helper excludeFrom() must be present in rendered HTML'
    )

    # Fix 1.8: normalized search score factory must be present
    assert 'score' in html, (
        'normalizeSearch score factory must be present in rendered HTML'
    )
