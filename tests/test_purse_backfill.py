"""Tests for backfilling a completed tournament's official purse from the
schedule endpoint when it was never captured (majors announce purse week-of,
and the leaderboard/earnings endpoints carry no purse field)."""
from sync_api import TournamentSync


class FakeAPI:
    """Minimal stand-in exposing only get_schedule, tracking call count."""

    def __init__(self, schedule):
        self._schedule = schedule
        self.schedule_calls = 0

    def get_schedule(self, year):
        self.schedule_calls += 1
        return self._schedule


def _schedule_with(tourn_id, purse):
    return {"schedule": [{"tournId": tourn_id, "name": "PGA Championship", "purse": purse}]}


def test_backfill_writes_purse_when_missing(make_tournament):
    tourn = make_tournament(name="PGA Championship", api_tourn_id="033", purse=0)
    api = FakeAPI(_schedule_with("033", 20_500_000))
    sync = TournamentSync(api)

    written = sync._backfill_purse_from_schedule(tourn)

    assert written == 20_500_000
    assert tourn.purse == 20_500_000


def test_backfill_noop_when_schedule_purse_zero(make_tournament):
    tourn = make_tournament(name="PGA Championship", api_tourn_id="033", purse=0)
    api = FakeAPI(_schedule_with("033", 0))
    sync = TournamentSync(api)

    written = sync._backfill_purse_from_schedule(tourn)

    assert written is None
    assert (tourn.purse or 0) == 0


def test_backfill_noop_when_tourn_not_in_schedule(make_tournament):
    tourn = make_tournament(name="PGA Championship", api_tourn_id="033", purse=0)
    api = FakeAPI(_schedule_with("999", 20_500_000))
    sync = TournamentSync(api)

    written = sync._backfill_purse_from_schedule(tourn)

    assert written is None
    assert (tourn.purse or 0) == 0


def test_backfill_handles_mongo_number_format(make_tournament):
    tourn = make_tournament(name="PGA Championship", api_tourn_id="033", purse=0)
    api = FakeAPI(_schedule_with("033", {"$numberInt": "20500000"}))
    sync = TournamentSync(api)

    written = sync._backfill_purse_from_schedule(tourn)

    assert written == 20_500_000
    assert tourn.purse == 20_500_000
