"""
Tests: the leader-row highlight on the tournament detail results table.

The top-scoring row carries row-leader EXCEPT when it is the signed-in
viewer's own row, where the gold row-current-user identity wins. The template
must use an elif (like index.html) so the classes are mutually exclusive; two
independent ifs double-class the leader's own row, and the mint row-leader
fill overrides their gold tint by source order (both rules are !important at
equal specificity in style.css).
"""
from datetime import datetime, timedelta, timezone

from models import LEAGUE_TZ


def _row_slice(html, css_class):
    """Return the <tr> ... </tr> slice whose class attribute is css_class."""
    start = html.index(f'<tr class="{css_class}">')
    return html[start:html.index('</tr>', start)]


def _make_past_deadline():
    """Naive Central-time timestamp 3h in the past.

    Tournament.is_deadline_passed() localizes a naive pick_deadline to LEAGUE_TZ,
    so the value must be built in Central wall-clock time (not the machine's local
    zone) to read as "passed" regardless of where the suite runs (e.g. UTC CI).
    """
    return datetime.now(timezone.utc).astimezone(LEAGUE_TZ).replace(tzinfo=None) - timedelta(hours=3)


def _seed_complete_tournament(db, make_user, make_player, make_tournament, make_pick):
    """Two users with resolved picks on a complete tournament; leader out-earns chaser."""
    leader = make_user(display_name='Lead Dog')
    chaser = make_user(display_name='Chaser')

    pa = make_player(first_name='Alpha', last_name='Primary')
    ba = make_player(first_name='Alpha', last_name='Backup')
    pb = make_player(first_name='Beta', last_name='Primary')
    bb = make_player(first_name='Beta', last_name='Backup')

    t = make_tournament(name='Leader Row Test', status='complete')
    t.pick_deadline = _make_past_deadline()

    make_pick(leader, t, pa, ba, points_earned=2_000_000, active_player_id=pa.id)
    make_pick(chaser, t, pb, bb, points_earned=1_000_000, active_player_id=pb.id)
    db.session.commit()
    return t, leader, chaser


def test_logged_out_top_scorer_row_is_leader(
        db, client, make_user, make_player, make_tournament, make_pick):
    t, leader, chaser = _seed_complete_tournament(
        db, make_user, make_player, make_tournament, make_pick)
    html = client.get(f'/tournament/{t.id}').get_data(as_text=True)
    assert html.count('row-leader') == 1
    assert 'row-current-user' not in html
    assert 'Lead Dog' in _row_slice(html, 'row-leader')


def test_logged_in_non_leader_gets_both_highlights_on_distinct_rows(
        db, client, make_user, make_player, make_tournament, make_pick, login):
    t, leader, chaser = _seed_complete_tournament(
        db, make_user, make_player, make_tournament, make_pick)
    login(chaser)
    html = client.get(f'/tournament/{t.id}').get_data(as_text=True)
    assert 'Lead Dog' in _row_slice(html, 'row-leader')
    assert 'Chaser' in _row_slice(html, 'row-current-user')


def test_logged_in_top_scorer_keeps_identity_gold_not_leader_mint(
        db, client, make_user, make_player, make_tournament, make_pick, login):
    t, leader, chaser = _seed_complete_tournament(
        db, make_user, make_player, make_tournament, make_pick)
    login(leader)
    html = client.get(f'/tournament/{t.id}').get_data(as_text=True)
    # self-identity wins: the leader's own row is gold, never double-classed mint
    assert 'row-leader' not in html
    assert 'Lead Dog' in _row_slice(html, 'row-current-user')
