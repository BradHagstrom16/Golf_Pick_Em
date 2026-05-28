"""Home page 'next pick during active play' thread (U2 P2).

During an active tournament the home route must still surface the *next* upcoming
tournament so a member always has a path to lock next week's golfer ("two equal
front doors", PRODUCT.md). The existing upcoming-pick CTA is suppressed during
active play because `index()` collapses the single next-tournament query onto the
active one, leaving `upcoming_tournament` None. These tests pin the additive
`next_pick_*` context the route must expose and the CTA the template must render.
"""
from datetime import datetime, timedelta, timezone

import pytest
from flask import template_rendered

from models import LEAGUE_TZ, TournamentField


def _now_ct() -> datetime:
    """Current league Central time as a naive datetime, the form the tournament
    date/deadline columns store (CLAUDE.md: deadlines are naive CT in SQLite).
    Mirrors the idiom in test_tournament_detail_ranking/penalty."""
    return datetime.now(timezone.utc).astimezone(LEAGUE_TZ).replace(tzinfo=None)


@pytest.fixture
def captured_templates(app):
    """Record (template, context) tuples rendered during a request."""
    recorded = []

    def record(sender, template, context, **extra):
        recorded.append((template, context))

    template_rendered.connect(record, app)
    try:
        yield recorded
    finally:
        template_rendered.disconnect(record, app)


def _ctx(captured, name='index.html'):
    """Return the render context for the named template from a capture list."""
    for template, context in captured:
        if template.name == name:
            return context
    raise AssertionError(f'{name} was not rendered')


def _seed_active(make_tournament):
    """An in-progress tournament: deadline passed, not yet ended."""
    now = _now_ct()
    return make_tournament(
        name='U.S. Open',
        status='active',
        is_major=True,
        start_date=now - timedelta(days=3),
        end_date=now + timedelta(days=2),
        pick_deadline=now - timedelta(days=2),
    )


def _seed_next_upcoming(make_tournament):
    """The next upcoming tournament after the active one (deadline in the future)."""
    now = _now_ct()
    return make_tournament(
        name='Travelers Championship',
        status='upcoming',
        is_major=False,
        start_date=now + timedelta(days=5),
        end_date=now + timedelta(days=8),
        pick_deadline=now + timedelta(days=5),
    )


def _field(db, tournament, make_player, n=3):
    """Seed n TournamentField rows so the tournament reads as field-synced."""
    for _ in range(n):
        p = make_player()
        db.session.add(TournamentField(tournament_id=tournament.id, player_id=p.id))
    db.session.flush()


def test_active_play_exposes_next_pick_context(
    db, client, make_tournament, make_player, captured_templates
):
    """With an active tournament + a field-synced upcoming one, the route exposes
    next_pick_tournament and its field count (which the old upcoming vars don't)."""
    _seed_active(make_tournament)
    nxt = _seed_next_upcoming(make_tournament)
    _field(db, nxt, make_player, n=4)
    db.session.commit()

    resp = client.get('/')
    assert resp.status_code == 200
    ctx = _ctx(captured_templates)
    assert ctx['next_pick_tournament'] is not None
    assert ctx['next_pick_tournament'].id == nxt.id
    assert ctx['next_pick_field_count'] == 4
    # The legacy upcoming CTA stays suppressed during active play.
    assert ctx['upcoming_tournament'] is None


def test_active_play_renders_next_pick_cta(
    db, login, make_user, make_tournament, make_player
):
    """An authenticated member with no pick sees a next-pick CTA naming the
    upcoming tournament and linking to make_pick."""
    user = make_user()
    _seed_active(make_tournament)
    nxt = _seed_next_upcoming(make_tournament)
    _field(db, nxt, make_player, n=4)
    db.session.commit()

    client = login(user)
    html = client.get('/').get_data(as_text=True)
    assert 'Next Pick' in html
    assert 'Travelers Championship' in html
    assert f'/pick/{nxt.id}' in html


def test_active_play_already_picked_shows_edit(
    db, login, make_user, make_tournament, make_player, make_pick, captured_templates
):
    """When the member already picked the next tournament, the route exposes the
    pick and the CTA shows an Edit affordance rather than a fresh-pick button."""
    user = make_user()
    _seed_active(make_tournament)
    nxt = _seed_next_upcoming(make_tournament)
    _field(db, nxt, make_player, n=4)
    primary = make_player(first_name='Scottie', last_name='Scheffler')
    backup = make_player(first_name='Rory', last_name='McIlroy')
    make_pick(user, nxt, primary, backup)
    db.session.commit()

    client = login(user)
    resp = client.get('/')
    ctx = _ctx(captured_templates)
    assert ctx['next_pick_user_pick'] is not None
    assert ctx['next_pick_user_pick'].primary_player_id == primary.id
    html = resp.get_data(as_text=True)
    assert 'Edit' in html
    assert 'Scheffler' in html


def test_next_pick_suppressed_when_field_unsynced(
    db, login, make_user, make_tournament, captured_templates
):
    """An upcoming tournament with no synced field exposes a zero count and renders
    no fresh-pick button (nothing to pick yet)."""
    user = make_user()
    _seed_active(make_tournament)
    _seed_next_upcoming(make_tournament)  # no field seeded
    db.session.commit()

    client = login(user)
    html = client.get('/').get_data(as_text=True)
    ctx = _ctx(captured_templates)
    assert ctx['next_pick_field_count'] == 0
    assert '/pick/' not in html


def test_no_next_pick_context_without_active_tournament(
    db, client, make_tournament, make_player, captured_templates
):
    """With no active tournament the next-pick thread is irrelevant; the route may
    still compute the var but the active-only CTA must not appear."""
    nxt = _seed_next_upcoming(make_tournament)
    _field(db, nxt, make_player, n=4)
    db.session.commit()

    client.get('/')
    ctx = _ctx(captured_templates)
    # Not an active-play scenario: the upcoming tournament is the ordinary CTA target.
    assert ctx['upcoming_tournament'] is not None
    assert ctx['upcoming_tournament'].id == nxt.id
