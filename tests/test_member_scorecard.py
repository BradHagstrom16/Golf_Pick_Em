"""
Tests: the Member Scorecard page (/member/<id>) — any member's season, week by
week, plus the admin-override tally.

Pick visibility follows the standings precedent (index, app.py): a pick is
shown only when its tournament is complete OR its deadline has passed — unless
the viewer IS that member. Hidden picks are stripped server-side, so a rival's
golfer name must never appear anywhere in the HTML before lock. The override
tally obeys the same lock rule so an override on a still-open week isn't
disclosed early.
"""
from datetime import datetime, timedelta

import stats
from models import PENALTY_PER_INCIDENT, TournamentField


SEASON = 2026


def _future_deadline():
    """A naive-CT deadline comfortably in the future."""
    return datetime.now() + timedelta(days=30)


def _past_deadline():
    """A naive-CT deadline comfortably in the past."""
    return datetime.now() - timedelta(days=2)


def _text_after(html, marker):
    """Return the element text immediately following the marker attribute."""
    i = html.index(marker)
    j = html.index('>', i) + 1
    return html[j:html.index('<', j)].strip()


def _tally_row(html, name):
    """Return the override-tally row slice for the given member name."""
    start = html.index(f'override-tally__name">{name}')
    return html[start:html.index('</li>', start)]


# ---------------------------------------------------------------------------
# Access + routing
# ---------------------------------------------------------------------------

def test_anonymous_can_view_member_page(db, client, make_user):
    cox = make_user(username='cox', display_name='Cox')
    resp = client.get(f'/member/{cox.id}')
    assert resp.status_code == 200
    assert 'Cox' in resp.get_data(as_text=True)


def test_unknown_member_404(db, client, make_user):
    make_user(username='cox')
    assert client.get('/member/99999').status_code == 404


def test_switcher_query_redirects_to_canonical_url(db, client, make_user):
    cox = make_user(username='cox')
    resp = client.get(f'/member?user_id={cox.id}')
    assert resp.status_code == 302
    assert resp.headers['Location'].endswith(f'/member/{cox.id}')


def test_bare_member_url_redirects_to_own_page_when_logged_in(
        db, client, make_user, login):
    make_user(username='abe')
    me = make_user(username='zed')
    login(me)
    resp = client.get('/member')
    assert resp.status_code == 302
    assert resp.headers['Location'].endswith(f'/member/{me.id}')


def test_bare_member_url_redirects_anonymous_to_first_member(db, client, make_user):
    make_user(username='zed')
    abe = make_user(username='Abe')  # case-insensitive alphabetical winner
    resp = client.get('/member')
    assert resp.status_code == 302
    assert resp.headers['Location'].endswith(f'/member/{abe.id}')


def test_bare_member_url_with_no_members_redirects_home(db, client):
    resp = client.get('/member')
    assert resp.status_code == 302
    assert resp.headers['Location'].endswith('/')


def test_switcher_query_with_non_decimal_digits_falls_through(db, client, make_user):
    """isdigit() accepts characters int() rejects (e.g. superscript two);
    the redirect branch must not 500 on them."""
    abe = make_user(username='abe')
    resp = client.get('/member?user_id=²')
    assert resp.status_code == 302
    assert resp.headers['Location'].endswith(f'/member/{abe.id}')


# ---------------------------------------------------------------------------
# Week-by-week picks
# ---------------------------------------------------------------------------

def test_picks_rendered_week_by_week(
        db, client, make_user, make_player, make_tournament, make_result, make_pick):
    cox = make_user(username='cox', display_name='Cox')
    scott = make_player(first_name='Scottie', last_name='Scheffler')
    rory = make_player(first_name='Rory', last_name='McIlroy')
    caddie = make_player(first_name='Carl', last_name='Spackler')
    t1 = make_tournament(name='Sony Open', start_date=datetime(2026, 1, 8))
    t2 = make_tournament(name='Genesis Invitational', start_date=datetime(2026, 2, 12))
    make_result(t1, scott, final_position='1', earnings=1_500_000)
    make_result(t2, rory, final_position='2', earnings=1_000_000)
    make_pick(cox, t1, scott, caddie, active_player_id=scott.id, points_earned=1_500_000)
    make_pick(cox, t2, rory, caddie, active_player_id=rory.id, points_earned=1_000_000)

    html = client.get(f'/member/{cox.id}').get_data(as_text=True)
    assert 'Sony Open' in html
    assert 'Genesis Invitational' in html
    assert 'Scottie Scheffler' in html
    assert 'Rory McIlroy' in html
    assert '1,500,000' in html
    assert '1,000,000' in html


def test_penalty_badge_renders_with_amount(
        db, client, make_user, make_player, make_tournament, make_result, make_pick):
    """Guards the penalty_per_incident context var — Jinja renders 'Penalty $'
    silently if the route forgets to pass it."""
    cox = make_user(username='cox')
    scott = make_player(first_name='Scottie', last_name='Scheffler')
    caddie = make_player(first_name='Carl', last_name='Spackler')
    masters = make_tournament(name='The Masters', is_major=True)
    make_result(masters, scott, status='cut', final_position='CUT', earnings=0)
    make_pick(cox, masters, scott, caddie,
              active_player_id=scott.id, points_earned=0, penalty_triggered=True)

    html = client.get(f'/member/{cox.id}').get_data(as_text=True)
    assert f'Penalty ${PENALTY_PER_INCIDENT}' in html


def test_empty_member_shows_no_pick_rows(db, client, make_user, make_tournament):
    cox = make_user(username='cox', display_name='Cox')
    make_tournament(name='Sony Open')
    html = client.get(f'/member/{cox.id}').get_data(as_text=True)
    assert 'Sony Open' in html
    assert 'No pick' in html


# ---------------------------------------------------------------------------
# Pre-deadline privacy — no leaks
# ---------------------------------------------------------------------------

def test_open_week_pick_hidden_from_anonymous_and_rivals(
        db, client, make_user, make_player, make_tournament, make_pick, login):
    cox = make_user(username='cox')
    rival = make_user(username='rival')
    primary = make_player(first_name='Secret', last_name='Weaponton')
    backup = make_player(first_name='Hidden', last_name='Backupsmith')
    t = make_tournament(
        name='Travelers Championship', status='upcoming',
        start_date=datetime.now() + timedelta(days=32),
        pick_deadline=_future_deadline())
    make_pick(cox, t, primary, backup)

    html = client.get(f'/member/{cox.id}').get_data(as_text=True)
    assert 'Weaponton' not in html
    assert 'Backupsmith' not in html
    assert 'Travelers Championship' in html  # the week still shows as a row

    login(rival)
    html = client.get(f'/member/{cox.id}').get_data(as_text=True)
    assert 'Weaponton' not in html
    assert 'Backupsmith' not in html


def test_own_open_week_pick_visible_to_self(
        db, client, make_user, make_player, make_tournament, make_pick, login):
    cox = make_user(username='cox')
    primary = make_player(first_name='Secret', last_name='Weaponton')
    backup = make_player(first_name='Hidden', last_name='Backupsmith')
    t = make_tournament(
        name='Travelers Championship', status='upcoming',
        start_date=datetime.now() + timedelta(days=32),
        pick_deadline=_future_deadline())
    make_pick(cox, t, primary, backup)

    login(cox)
    html = client.get(f'/member/{cox.id}').get_data(as_text=True)
    assert 'Weaponton' in html
    assert 'Backupsmith' in html


def test_locked_week_pick_visible_to_others_even_before_complete(
        db, client, make_user, make_player, make_tournament, make_pick):
    """Gating is deadline-based, not status-based."""
    cox = make_user(username='cox')
    primary = make_player(first_name='Locked', last_name='Golferson')
    backup = make_player(first_name='Carl', last_name='Spackler')
    t = make_tournament(
        name='RBC Heritage', status='active',
        start_date=datetime.now() - timedelta(days=1),
        pick_deadline=_past_deadline())
    make_pick(cox, t, primary, backup)

    html = client.get(f'/member/{cox.id}').get_data(as_text=True)
    assert 'Locked Golferson' in html


# ---------------------------------------------------------------------------
# Admin-override tally
# ---------------------------------------------------------------------------

def test_override_tally_panel_and_member_figure(
        db, client, make_user, make_player, make_tournament, make_pick):
    alice = make_user(username='alice', display_name='Alice')
    bob = make_user(username='bob', display_name='Bob')
    carol = make_user(username='carol', display_name='Carol')
    scott = make_player(first_name='Scottie', last_name='Scheffler')
    caddie = make_player(first_name='Carl', last_name='Spackler')
    t1 = make_tournament(name='Sony Open', start_date=datetime(2026, 1, 8))
    t2 = make_tournament(name='Genesis', start_date=datetime(2026, 2, 12))

    make_pick(alice, t1, scott, caddie, admin_override=True,
              admin_override_note='Missed the deadline')
    make_pick(alice, t2, scott, caddie, admin_override=True)
    make_pick(bob, t1, scott, caddie, admin_override=True)
    make_pick(carol, t1, scott, caddie)

    html = client.get(f'/member/{alice.id}').get_data(as_text=True)
    assert _text_after(html, 'data-member-overrides') == '2'
    assert 'override-tally__count">2' in _tally_row(html, 'Alice')
    assert 'override-tally__count">1' in _tally_row(html, 'Bob')
    # Carol has no overrides: she gets no tally row
    assert 'override-tally__name">Carol' not in html

    html = client.get(f'/member/{carol.id}').get_data(as_text=True)
    assert _text_after(html, 'data-member-overrides') == '0'


def test_override_on_open_week_not_counted(
        db, client, make_user, make_player, make_tournament, make_pick):
    alice = make_user(username='alice', display_name='Alice')
    scott = make_player(first_name='Scottie', last_name='Scheffler')
    caddie = make_player(first_name='Carl', last_name='Spackler')
    t_open = make_tournament(
        name='Travelers Championship', status='upcoming',
        start_date=datetime.now() + timedelta(days=32),
        pick_deadline=_future_deadline())
    make_pick(alice, t_open, scott, caddie, admin_override=True)

    html = client.get(f'/member/{alice.id}').get_data(as_text=True)
    assert _text_after(html, 'data-member-overrides') == '0'
    assert 'No admin overrides' in html


def test_override_tally_helper_groups_sorts_and_scopes(
        db, make_user, make_player, make_tournament, make_pick):
    alice = make_user(username='alice', display_name='Alice')
    bob = make_user(username='bob', display_name='Bob')
    carol = make_user(username='carol', display_name='Carol')
    scott = make_player(first_name='Scottie', last_name='Scheffler')
    caddie = make_player(first_name='Carl', last_name='Spackler')
    t1 = make_tournament(name='Sony Open', start_date=datetime(2026, 1, 8))
    t2 = make_tournament(name='Genesis', start_date=datetime(2026, 2, 12))
    t_open = make_tournament(name='Travelers', status='upcoming',
                             pick_deadline=_future_deadline())
    t_last_year = make_tournament(name='Old Sony', season_year=2025)

    make_pick(alice, t1, scott, caddie, admin_override=True)
    make_pick(alice, t2, scott, caddie, admin_override=True)
    make_pick(bob, t1, scott, caddie, admin_override=True)
    make_pick(carol, t2, scott, caddie, admin_override=True)
    make_pick(alice, t_open, scott, caddie, admin_override=True)   # unlocked
    make_pick(alice, t_last_year, scott, caddie, admin_override=True)  # other season

    tally = stats.override_tally(SEASON, [t1.id, t2.id])
    assert tally == [
        {'user_id': alice.id, 'name': 'Alice', 'count': 2},
        {'user_id': bob.id, 'name': 'Bob', 'count': 1},
        {'user_id': carol.id, 'name': 'Carol', 'count': 1},
    ]


# ---------------------------------------------------------------------------
# Self-view pick management (merged in from My Picks)
# ---------------------------------------------------------------------------

def _add_to_field(db, tournament, *players):
    for p in players:
        db.session.add(TournamentField(tournament_id=tournament.id, player_id=p.id))
    db.session.flush()


def test_self_view_open_week_without_pick_offers_pick_button(
        db, client, make_user, make_player, make_tournament, login):
    cox = make_user(username='cox')
    scott = make_player(first_name='Scottie', last_name='Scheffler')
    t = make_tournament(
        name='Travelers Championship', status='upcoming',
        start_date=datetime.now() + timedelta(days=32),
        pick_deadline=_future_deadline())
    _add_to_field(db, t, scott)

    login(cox)
    html = client.get(f'/member/{cox.id}').get_data(as_text=True)
    assert f'/pick/{t.id}' in html
    assert '<th>Action</th>' in html


def test_self_view_open_week_with_pick_offers_edit_button(
        db, client, make_user, make_player, make_tournament, make_pick, login):
    cox = make_user(username='cox')
    scott = make_player(first_name='Scottie', last_name='Scheffler')
    caddie = make_player(first_name='Carl', last_name='Spackler')
    t = make_tournament(
        name='Travelers Championship', status='upcoming',
        start_date=datetime.now() + timedelta(days=32),
        pick_deadline=_future_deadline())
    _add_to_field(db, t, scott, caddie)
    make_pick(cox, t, scott, caddie)

    login(cox)
    html = client.get(f'/member/{cox.id}').get_data(as_text=True)
    assert f'/pick/{t.id}' in html
    assert 'btn-gold' in html  # Edit renders in the gold register


def test_self_view_open_week_without_field_offers_view_not_pick(
        db, client, make_user, make_tournament, login):
    """No field synced yet → nothing to pick from; offer the detail page."""
    cox = make_user(username='cox')
    t = make_tournament(
        name='Travelers Championship', status='upcoming',
        start_date=datetime.now() + timedelta(days=32),
        pick_deadline=_future_deadline())

    login(cox)
    html = client.get(f'/member/{cox.id}').get_data(as_text=True)
    assert f'/pick/{t.id}' not in html
    assert f'/tournament/{t.id}' in html


def test_pick_buttons_never_render_for_rivals_or_anonymous(
        db, client, make_user, make_player, make_tournament, login):
    cox = make_user(username='cox')
    rival = make_user(username='rival')
    scott = make_player(first_name='Scottie', last_name='Scheffler')
    t = make_tournament(
        name='Travelers Championship', status='upcoming',
        start_date=datetime.now() + timedelta(days=32),
        pick_deadline=_future_deadline())
    _add_to_field(db, t, scott)

    html = client.get(f'/member/{cox.id}').get_data(as_text=True)
    assert '/pick/' not in html

    login(rival)
    html = client.get(f'/member/{cox.id}').get_data(as_text=True)
    assert '/pick/' not in html


def test_used_golfers_card_on_self_view_only(
        db, client, make_user, make_player, make_tournament, make_pick, login):
    cox = make_user(username='cox')
    rival = make_user(username='rival')
    scott = make_player(first_name='Scottie', last_name='Scheffler')
    caddie = make_player(first_name='Carl', last_name='Spackler')
    t = make_tournament(name='Sony Open')
    make_pick(cox, t, scott, caddie,
              active_player_id=scott.id, points_earned=500_000, primary_used=True)

    login(cox)
    html = client.get(f'/member/{cox.id}').get_data(as_text=True)
    assert 'Used Golfers' in html

    login(rival)
    html = client.get(f'/member/{cox.id}').get_data(as_text=True)
    assert 'Used Golfers' not in html


# ---------------------------------------------------------------------------
# Resolved weeks de-emphasize the golfer who didn't count
# ---------------------------------------------------------------------------

def test_resolved_week_mutes_unused_backup(
        db, client, make_user, make_player, make_tournament, make_pick):
    cox = make_user(username='cox')
    scott = make_player(first_name='Scottie', last_name='Scheffler')
    caddie = make_player(first_name='Carl', last_name='Spackler')
    t = make_tournament(name='Sony Open')  # status defaults to complete
    make_pick(cox, t, scott, caddie,
              active_player_id=scott.id, points_earned=500_000, primary_used=True)

    html = client.get(f'/member/{cox.id}').get_data(as_text=True)
    assert 'pick-name-idle">Carl Spackler' in html
    assert 'pick-name-idle">Scottie Scheffler' not in html


def test_resolved_week_mutes_withdrawn_primary_when_backup_counted(
        db, client, make_user, make_player, make_tournament, make_pick):
    cox = make_user(username='cox')
    scott = make_player(first_name='Scottie', last_name='Scheffler')
    caddie = make_player(first_name='Carl', last_name='Spackler')
    t = make_tournament(name='Sony Open')
    make_pick(cox, t, scott, caddie,
              active_player_id=caddie.id, points_earned=250_000, backup_used=True)

    html = client.get(f'/member/{cox.id}').get_data(as_text=True)
    assert 'pick-name-idle">Scottie Scheffler' in html
    assert 'pick-name-idle">Carl Spackler' not in html


def test_open_week_does_not_mute_either_golfer(
        db, client, make_user, make_player, make_tournament, make_pick, login):
    """State can still flip until resolution — no muting before complete."""
    cox = make_user(username='cox')
    scott = make_player(first_name='Scottie', last_name='Scheffler')
    caddie = make_player(first_name='Carl', last_name='Spackler')
    t = make_tournament(
        name='Travelers Championship', status='upcoming',
        start_date=datetime.now() + timedelta(days=32),
        pick_deadline=_future_deadline())
    make_pick(cox, t, scott, caddie)

    login(cox)
    html = client.get(f'/member/{cox.id}').get_data(as_text=True)
    assert 'pick-name-idle">Scottie Scheffler' not in html
    assert 'pick-name-idle">Carl Spackler' not in html


# ---------------------------------------------------------------------------
# Penalty tile: settled state
# ---------------------------------------------------------------------------

def test_penalty_tile_shows_settled_when_paid_in_full(
        db, client, make_user, make_player, make_tournament, make_result, make_pick):
    cox = make_user(username='cox', penalty_paid=PENALTY_PER_INCIDENT)
    scott = make_player(first_name='Scottie', last_name='Scheffler')
    caddie = make_player(first_name='Carl', last_name='Spackler')
    masters = make_tournament(name='The Masters', is_major=True)
    make_result(masters, scott, status='cut', final_position='CUT', earnings=0)
    make_pick(cox, masters, scott, caddie,
              active_player_id=scott.id, points_earned=0, penalty_triggered=True)

    html = client.get(f'/member/{cox.id}').get_data(as_text=True)
    assert 'Settled' in html
    assert f'${PENALTY_PER_INCIDENT} paid' in html
    assert f'${PENALTY_PER_INCIDENT} to the pot' not in html


# ---------------------------------------------------------------------------
# Entry links + regression
# ---------------------------------------------------------------------------

def test_standings_member_names_link_to_scorecard(db, client, make_user):
    cox = make_user(username='cox', display_name='Cox')
    html = client.get('/').get_data(as_text=True)
    assert f'/member/{cox.id}' in html


def test_tournament_detail_member_names_link_to_scorecard(
        db, client, make_user, make_player, make_tournament, make_result, make_pick):
    cox = make_user(username='cox', display_name='Cox')
    scott = make_player(first_name='Scottie', last_name='Scheffler')
    caddie = make_player(first_name='Carl', last_name='Spackler')
    t = make_tournament(name='Sony Open', pick_deadline=_past_deadline())
    make_result(t, scott, final_position='1', earnings=1_500_000)
    make_pick(cox, t, scott, caddie, active_player_id=scott.id, points_earned=1_500_000)

    html = client.get(f'/tournament/{t.id}').get_data(as_text=True)
    assert f'/member/{cox.id}' in html


def test_my_picks_still_renders_for_current_user(
        db, client, make_user, make_player, make_tournament, make_pick, login):
    """Regression smoke for the shared-helper extraction from my_picks."""
    cox = make_user(username='cox')
    scott = make_player(first_name='Scottie', last_name='Scheffler')
    caddie = make_player(first_name='Carl', last_name='Spackler')
    make_tournament(name='Sony Open')
    t = make_tournament(name='Genesis')
    make_pick(cox, t, scott, caddie, active_player_id=scott.id, points_earned=500_000)

    login(cox)
    resp = client.get('/my-picks')
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert 'Sony Open' in html
    assert 'Scottie Scheffler' in html
