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
    with flask_app.app_context():
        _db.create_all()
        yield flask_app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def db(app):
    yield _db
    _db.session.rollback()
    for table in reversed(_db.metadata.sorted_tables):
        _db.session.execute(table.delete())
    _db.session.commit()


@pytest.fixture
def session(db):
    return _db.session


@pytest.fixture
def make_user(db):
    counter = {'n': 0}

    def _make(username=None, **kwargs):
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
    counter = {'n': 0}

    def _make(first_name='First', last_name=None, **kwargs):
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
    counter = {'n': 0}

    def _make(name=None, is_major=False, **kwargs):
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
    def _make(tournament, player, status='complete', **kwargs):
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
    def _make(user, tournament, primary, backup, **kwargs):
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
