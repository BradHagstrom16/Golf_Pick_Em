"""Tests for TournamentSync tee time parsing methods."""
import pytz
from datetime import datetime
from sync_api import TournamentSync


class TestParseTeeTimeTimestamp:
    """Tests for _parse_tee_time_timestamp — the preferred, timezone-safe parser."""

    def test_returns_none_for_none(self):
        assert TournamentSync._parse_tee_time_timestamp(None) is None

    def test_returns_none_for_empty_string(self):
        assert TournamentSync._parse_tee_time_timestamp("") is None

    def test_parses_mongodb_date_numberlong(self):
        """Original format: {"$date": {"$numberLong": "1744199400000"}}"""
        ts = {"$date": {"$numberLong": "1744199400000"}}
        result = TournamentSync._parse_tee_time_timestamp(ts)
        assert result is not None
        assert result.tzinfo is not None
        # 1744199400000 ms = 2025-04-09 11:30:00 UTC
        assert result.year == 2025
        assert result.month == 4

    def test_parses_raw_millisecond_integer(self):
        """Raw integer milliseconds."""
        result = TournamentSync._parse_tee_time_timestamp(1744199400000)
        assert result is not None
        assert result.tzinfo is not None

    def test_parses_iso_string_as_utc(self):
        """New API format: plain ISO 8601 string, treated as UTC."""
        result = TournamentSync._parse_tee_time_timestamp("2026-04-09T11:40:00")
        assert result is not None
        assert result.tzinfo is not None
        assert result.hour == 11
        assert result.minute == 40
        # Must be UTC
        assert result.tzname() == "UTC"

    def test_parses_iso_string_with_z_suffix(self):
        result = TournamentSync._parse_tee_time_timestamp("2026-04-09T11:40:00Z")
        assert result is not None
        assert result.tzname() == "UTC"
        assert result.hour == 11

    def test_parses_iso_string_with_utc_offset(self):
        result = TournamentSync._parse_tee_time_timestamp("2026-04-09T11:40:00+00:00")
        assert result is not None
        assert result.hour == 11

    def test_iso_string_converts_to_correct_central_time(self):
        """The Masters bug: 11:40 UTC should be 6:40 AM Central (CDT, UTC-5)."""
        result = TournamentSync._parse_tee_time_timestamp("2026-04-09T11:40:00")
        ct = result.astimezone(pytz.timezone("America/Chicago"))
        assert ct.hour == 6
        assert ct.minute == 40
