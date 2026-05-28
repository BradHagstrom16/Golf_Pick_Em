"""Shared fixtures for DB-backed tests."""
import os
os.environ.setdefault('FLASK_ENV', 'testing')

from datetime import datetime, timedelta, timezone

import pytest

from app import app as flask_app
from models import (
    db as _db,
    User,
    Player,
    Tournament,
    TournamentField,
    TournamentResult,
    Pick,
)


@pytest.fixture(scope='session')
def app():
    """Session-wide Flask app with the schema created once (and dropped at teardown)."""
    with flask_app.app_context():
        _db.create_all()
        yield flask_app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture(autouse=True)
def _isolate_login(app):
    """Prevent Flask-Login's cached current_user from leaking between tests.

    Flask-Login caches the loaded user on ``g._login_user`` (flask_login 0.6.x).
    Because the ``app`` fixture holds a single session-scoped app context open for
    the whole run, every test_client request reuses that same ``g`` — so an
    authenticated request in one test would otherwise leave ``current_user`` set
    for the next test (making an anonymous-only route like /register redirect, or
    an admin route accept a stale user). Clear the cache around each test.
    """
    from flask import g
    g.pop('_login_user', None)
    yield
    g.pop('_login_user', None)


@pytest.fixture
def db(app):
    """Yield the SQLAlchemy db, wiping all table rows after each test for isolation."""
    yield _db
    _db.session.rollback()
    for table in reversed(_db.metadata.sorted_tables):
        _db.session.execute(table.delete())
    _db.session.commit()
    # The app fixture holds one session open for the whole run, so the identity
    # map survives across tests. Wiping rows reuses low SQLite PKs, so the next
    # test's flush can collide with a stale same-PK object still referenced in
    # the map (surfaces as an intermittent, GC-timing-dependent "Identity map
    # already had an identity..." SAWarning). Dispose the scoped session so each
    # test deterministically starts with a clean identity map.
    _db.session.remove()


@pytest.fixture
def session(db):
    """Convenience handle to the active SQLAlchemy session."""
    return _db.session


@pytest.fixture
def make_user(db):
    """Factory fixture returning a function that creates and flushes a User."""
    counter = {'n': 0}

    def _make(username=None, **kwargs):
        """Create a User with sensible defaults; extra kwargs pass through to the model."""
        counter['n'] += 1
        n = counter['n']
        user = User(
            username=username or f'user{n}',
            email=kwargs.pop('email', f'user{n}@example.test'),
            **kwargs,
        )
        user.set_password(kwargs.pop('password', 'pw'))
        db.session.add(user)
        db.session.flush()
        return user

    return _make


@pytest.fixture
def make_player(db):
    """Factory fixture returning a function that creates and flushes a Player."""
    counter = {'n': 0}

    def _make(first_name='First', last_name=None, **kwargs):
        """Create a Player with sensible defaults; extra kwargs pass through to the model."""
        counter['n'] += 1
        n = counter['n']
        player = Player(
            api_player_id=kwargs.pop('api_player_id', f'api{n}'),
            first_name=first_name,
            last_name=last_name or f'Player{n}',
            **kwargs,
        )
        db.session.add(player)
        db.session.flush()
        return player

    return _make


@pytest.fixture
def make_tournament(db):
    """Factory fixture returning a function that creates and flushes a Tournament."""
    counter = {'n': 0}

    def _make(name=None, is_major=False, **kwargs):
        """Create a Tournament with sensible defaults; extra kwargs pass through to the model."""
        counter['n'] += 1
        n = counter['n']
        start = kwargs.pop('start_date', datetime(2026, 4, 9))
        end = kwargs.pop('end_date', start + timedelta(days=3))
        tourn = Tournament(
            api_tourn_id=kwargs.pop('api_tourn_id', f'T{n}'),
            name=name or f'Tournament {n}',
            season_year=kwargs.pop('season_year', 2026),
            start_date=start,
            end_date=end,
            purse=kwargs.pop('purse', 10_000_000),
            is_major=is_major,
            status=kwargs.pop('status', 'complete'),
            **kwargs,
        )
        db.session.add(tourn)
        db.session.flush()
        return tourn

    return _make


@pytest.fixture
def make_result(db):
    """Factory fixture returning a function that creates and flushes a TournamentResult."""
    def _make(tournament, player, status='complete', **kwargs):
        """Create a TournamentResult with sensible defaults; extra kwargs pass through."""
        result = TournamentResult(
            tournament_id=tournament.id,
            player_id=player.id,
            status=status,
            final_position=kwargs.pop('final_position', '1'),
            earnings=kwargs.pop('earnings', 0),
            rounds_completed=kwargs.pop('rounds_completed', 4),
            score_to_par=kwargs.pop('score_to_par', 0),
            **kwargs,
        )
        db.session.add(result)
        db.session.flush()
        return result

    return _make


@pytest.fixture
def make_pick(db):
    """Factory fixture returning a function that creates and flushes a Pick."""
    def _make(user, tournament, primary, backup, **kwargs):
        """Create a Pick for the given user/tournament; extra kwargs pass through."""
        pick = Pick(
            user_id=user.id,
            tournament_id=tournament.id,
            primary_player_id=primary.id,
            backup_player_id=backup.id,
            **kwargs,
        )
        db.session.add(pick)
        db.session.flush()
        return pick

    return _make


@pytest.fixture
def client(app):
    """A Flask test client with CSRF disabled for form posts."""
    app.config['WTF_CSRF_ENABLED'] = False
    return app.test_client()


@pytest.fixture
def login(client):
    """Factory returning a function that logs the given user into the test client."""
    def _login(user):
        """Inject the user's id into the session and return the authenticated client."""
        with client.session_transaction() as sess:
            sess['_user_id'] = str(user.id)
        return client
    return _login
