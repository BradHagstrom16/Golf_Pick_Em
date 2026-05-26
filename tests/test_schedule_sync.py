"""Tests for sync_schedule()'s event date handling. The SlashGolf schedule
endpoint migrated date.start from epoch-millis to ISO 8601 strings; the parser
must handle both so events aren't silently skipped (which left major purses
stuck at the season estimate)."""
from sync_api import TournamentSync


class FakeAPI:
    """Minimal stand-in exposing only get_schedule."""

    def __init__(self, schedule) -> None:
        """Store the canned schedule payload get_schedule will return."""
        self._schedule = schedule

    def get_schedule(self, _year) -> dict:
        """Return the canned schedule payload."""
        return self._schedule


def _event(tourn_id, start, purse, name="PGA Championship", fmt="stroke") -> dict:
    """Build a single schedule event with the given start date and purse."""
    return {
        "tournId": tourn_id,
        "name": name,
        "purse": purse,
        "format": fmt,
        "date": {"start": start, "end": start},
    }


def test_iso_date_event_updates_purse(make_tournament):
    """An ISO 8601 date.start is parsed so the event's purse is applied."""
    tourn = make_tournament(name="PGA Championship", api_tourn_id="033", purse=0)
    api = FakeAPI({"schedule": [_event("033", "2026-05-14T00:00:00", 20_500_000)]})
    sync = TournamentSync(api)

    updated = sync.sync_schedule(2026)

    assert updated == 1
    assert tourn.purse == 20_500_000


def test_epoch_ms_date_still_works(make_tournament):
    """The legacy epoch-millisecond date.start format still parses (regression guard)."""
    tourn = make_tournament(name="PGA Championship", api_tourn_id="033", purse=0)
    # 2026-05-14 in epoch milliseconds
    api = FakeAPI({"schedule": [_event("033", 1_778_716_800_000, 20_500_000)]})
    sync = TournamentSync(api)

    updated = sync.sync_schedule(2026)

    assert updated == 1
    assert tourn.purse == 20_500_000


def test_event_after_cutoff_is_skipped(make_tournament):
    """An event starting on/after SEASON_CUTOFF_DATE is skipped, not updated."""
    tourn = make_tournament(name="Late Event", api_tourn_id="099", purse=0)
    # Starts after SEASON_CUTOFF_DATE (2026-08-24)
    api = FakeAPI({"schedule": [_event("099", "2026-09-01T00:00:00", 15_000_000, name="Late Event")]})
    sync = TournamentSync(api)

    updated = sync.sync_schedule(2026)

    assert updated == 0
    assert (tourn.purse or 0) == 0
