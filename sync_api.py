"""
Golf Pick 'Em League - API Sync Module
=======================================
Sync tournament data from SlashGolf API.

Data Flow:
1. sync_tournament_field() - Tuesday before tournament: Get players + tee times
2. sync_tournament_results() - Sunday after tournament: Get earnings + status
3. process_tournament_picks() - After results synced: Calculate points

API Endpoints Used:
- /leaderboards - Field, tee times, player status, rounds completed
- /earnings - Prize money per player
- /schedules - Season schedule (one-time import)
- /tournaments - Tournament details + full field
"""

import logging
import os
import random
import sys
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple

import click
import pytz
import requests

from models import db, Tournament, Player, TournamentField, TournamentResult, Pick, LEAGUE_TZ

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Dedicated API call logger for auditing RapidAPI usage
API_CALL_LOGGER = logging.getLogger("api_calls")
API_CALL_LOGGER.setLevel(logging.INFO)
if not API_CALL_LOGGER.handlers:
    log_dir = os.path.join(os.path.dirname(__file__), "logs")
    os.makedirs(log_dir, exist_ok=True)
    handler = logging.FileHandler(os.path.join(log_dir, "api_calls.log"))
    handler.setFormatter(logging.Formatter("%(asctime)s\t%(message)s"))
    API_CALL_LOGGER.addHandler(handler)

# Tournaments to EXCLUDE from the league
# (opposite-field events, playoffs finale, special events)
EXCLUDED_TOURNAMENTS = {
    'Puerto Rico Open',
    'ONEflight Myrtle Beach Classic',
    'ISCO Championship',
    'Corales Puntacana Championship',
    'TOUR Championship',
    'Presidents Cup',
}

# Baseline purse estimates (used when API returns $0)
# These will be overwritten when API provides authoritative non-zero values
# 2026 PGA Tour purse amounts (in dollars)
# Use None for TBD tournaments (majors typically announce week-of)
# Names must match exactly what API returns or what's in database
PURSE_ESTIMATES = {
    'Sony Open in Hawaii': 9_100_000,
    'The American Express': 9_200_000,
    'Farmers Insurance Open': 9_600_000,
    'WM Phoenix Open': 9_600_000,
    'AT&T Pebble Beach Pro-Am': 20_000_000,
    'The Genesis Invitational': 20_000_000,
    'Cognizant Classic': 9_600_000,
    'Arnold Palmer Invitational presented by Mastercard': 20_000_000,
    'THE PLAYERS Championship': 25_000_000,
    'Valspar Championship': 9_100_000,
    "Texas Children's Houston Open": 9_900_000,
    'Valero Texas Open': 9_800_000,
    'Masters Tournament': None,  # TBD - Major
    'RBC Heritage': 20_000_000,
    'Zurich Classic of New Orleans': 9_500_000,
    'Cadillac Championship': 20_000_000,
    'Truist Championship': 20_000_000,
    'PGA Championship': None,  # TBD - Major
    'THE CJ CUP Byron Nelson': 10_300_000,
    'Charles Schwab Challenge': 9_900_000,
    'the Memorial Tournament presented by Workday': 20_000_000,
    'RBC Canadian Open': 9_800_000,
    'U.S. Open': None,  # TBD - Major
    'Travelers Championship': 20_000_000,
    'John Deere Classic': 8_800_000,
    'Genesis Scottish Open': 9_000_000,
    'The Open Championship': None,  # TBD - Major
    '3M Open': 8_800_000,
    'Rocket Classic': 10_000_000,
    'Wyndham Championship': 8_500_000,
    'FedEx St. Jude Championship': 20_000_000,
    'BMW Championship': 20_000_000,
}
DEFAULT_PURSE = 10_000_000  # Fallback for tournaments not in estimates


class SlashGolfAPI:
    """Client for SlashGolf API."""

    # RapidAPI configuration
    BASE_URL = "https://live-golf-data.p.rapidapi.com"

    def __init__(self, api_key: str, api_host: str = "live-golf-data.p.rapidapi.com", sync_mode: str = "standard"):
        """
        Initialize API client.

        Args:
            api_key: Your RapidAPI key
            api_host: RapidAPI host (default for SlashGolf)
        """
        self.api_key = api_key
        self.headers = {
            "X-RapidAPI-Key": api_key,
            "X-RapidAPI-Host": api_host
        }
        self.org_id = "1"  # PGA Tour
        self.sync_mode = (sync_mode or "standard").lower()
        self._call_counter = 0

    def _log_api_call(self, endpoint: str, params: Dict, status: int, duration: float, attempt: int) -> None:
        """Record API call details for auditing."""
        self._call_counter += 1
        API_CALL_LOGGER.info(
            "count=%s\tmode=%s\tendpoint=%s\tstatus=%s\tattempt=%s\tduration=%.2fs\tparams=%s",
            self._call_counter,
            self.sync_mode,
            endpoint,
            status,
            attempt,
            duration,
            params,
        )

    def _make_request(self, endpoint: str, params: Dict = None, retries: int = 5) -> Optional[Dict]:
        """Make API request with exponential backoff, jitter, and structured logging."""
        url = f"{self.BASE_URL}/{endpoint}"

        if params is None:
            params = {}
        params["orgId"] = self.org_id

        backoff = 1.5
        for attempt in range(1, retries + 1):
            start_time = time.time()
            try:
                response = requests.get(url, headers=self.headers, params=params, timeout=15)

                duration = time.time() - start_time
                self._log_api_call(endpoint, params, response.status_code, duration, attempt)

                if response.status_code == 200:
                    return response.json()

                is_retryable = response.status_code in (429, 500, 502, 503, 504)
                logger.warning(
                    "API error %s on %s params=%s (attempt %s/%s, retryable=%s)",
                    response.status_code,
                    endpoint,
                    params,
                    attempt,
                    retries,
                    is_retryable,
                )

                if not is_retryable:
                    break

            except requests.RequestException as exc:
                logger.exception(
                    "Request failed for %s params=%s (attempt %s/%s)",
                    endpoint,
                    params,
                    attempt,
                    retries,
                )
                duration = time.time() - start_time
                self._log_api_call(endpoint, params, 0, duration, attempt)

            if attempt < retries:
                sleep_for = min(60, backoff * (2 ** (attempt - 1)))
                sleep_for = sleep_for * (1 + random.uniform(-0.25, 0.25))
                time.sleep(max(0.5, sleep_for))

        logger.error("Exhausted retries for endpoint %s params=%s", endpoint, params)
        return None

    def get_schedule(self, year: str) -> Optional[Dict]:
        """Get full season schedule."""
        return self._make_request("schedule", {"year": year})

    def get_tournament(self, tourn_id: str, year: str) -> Optional[Dict]:
        """Get tournament details including field."""
        return self._make_request("tournament", {"tournId": tourn_id, "year": year})

    def get_leaderboard(self, tourn_id: str, year: str) -> Optional[Dict]:
        """Get leaderboard with tee times, status, rounds."""
        return self._make_request("leaderboard", {"tournId": tourn_id, "year": year})

    def get_earnings(self, tourn_id: str, year: str) -> Optional[Dict]:
        """Get earnings/prize money for completed tournament."""
        return self._make_request("earnings", {"tournId": tourn_id, "year": year})


class TournamentSync:
    """Sync tournament data from API to database."""

    def __init__(self, api: SlashGolfAPI, sync_mode: str = "standard", fallback_deadline_hour: int = 7):
        self.api = api
        self.sync_mode = (sync_mode or "standard").lower()
        self.fallback_deadline_hour = fallback_deadline_hour

    @property
    def is_free_mode(self) -> bool:
        return self.sync_mode == "free"

    @staticmethod
    def _get_event_timezone(leaderboard_data: Dict) -> pytz.timezone:
        tz_name = leaderboard_data.get("timeZone") or leaderboard_data.get("timezone") or leaderboard_data.get("tz")
        if tz_name:
            try:
                return pytz.timezone(tz_name)
            except Exception:
                logger.warning("Unknown timezone '%s', falling back to league TZ", tz_name)
        return LEAGUE_TZ

    @staticmethod
    def _parse_tee_time_timestamp(tee_time_ts: Optional[Dict]) -> Optional[datetime]:
        """
        Parse teeTimeTimestamp from API (preferred method - timezone-safe).

        The API provides timestamps in MongoDB format: {"$date": {"$numberLong": "1768497660000"}}
        These are Unix timestamps in milliseconds, representing the exact moment in time.
        """
        if not tee_time_ts:
            return None

        try:
            # Handle MongoDB-style timestamp format
            if isinstance(tee_time_ts, dict):
                if '$date' in tee_time_ts:
                    date_val = tee_time_ts['$date']
                    if isinstance(date_val, dict) and '$numberLong' in date_val:
                        ts_ms = int(date_val['$numberLong'])
                    else:
                        ts_ms = int(date_val)
                elif '$numberLong' in tee_time_ts:
                    ts_ms = int(tee_time_ts['$numberLong'])
                else:
                    return None
            else:
                ts_ms = int(tee_time_ts)

            # Convert milliseconds to seconds and create timezone-aware datetime
            ts_sec = ts_ms / 1000
            return datetime.fromtimestamp(ts_sec, tz=pytz.UTC)
        except Exception as e:
            logger.warning("Unable to parse tee time timestamp '%s': %s", tee_time_ts, e)
            return None

    @staticmethod
    def _parse_tee_time(tee_time_str: Optional[str], tournament_date: datetime, event_tz: pytz.timezone) -> Optional[datetime]:
        """
        Parse tee time from string (fallback method - requires timezone context).

        WARNING: This method is less reliable because tee time strings like "7:21am"
        don't include timezone info. Use _parse_tee_time_timestamp when available.
        """
        if not tee_time_str or tee_time_str == "N/A":
            return None

        try:
            if "T" in tee_time_str:
                dt = datetime.fromisoformat(tee_time_str.replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = event_tz.localize(dt)
                return dt

            tee_time_parsed = datetime.strptime(tee_time_str, "%I:%M%p")
            tee_datetime = datetime.combine(tournament_date.date(), tee_time_parsed.time())
            return event_tz.localize(tee_datetime)
        except Exception:
            logger.warning("Unable to parse tee time '%s'", tee_time_str)
            return None

    def _update_pick_deadline_from_leaderboard(self, tournament: Tournament, leaderboard_data: Dict) -> Optional[datetime]:
        event_tz = self._get_event_timezone(leaderboard_data)
        earliest = None

        for player_data in leaderboard_data.get("leaderboardRows", []):
            # Prefer timestamp (timezone-safe) over string (ambiguous)
            tee_time = self._parse_tee_time_timestamp(player_data.get("teeTimeTimestamp"))
            if not tee_time:
                # Fallback to string parsing if timestamp not available
                tee_time = (
                    self._parse_tee_time(player_data.get("teeTime"), tournament.start_date, event_tz)
                    or self._parse_tee_time(player_data.get("teeTimeLocal"), tournament.start_date, event_tz)
                )
            if tee_time and (earliest is None or tee_time < earliest):
                earliest = tee_time

        if earliest:
            tournament.pick_deadline = earliest
        return earliest

    def _derive_status(self, tournament: Tournament, leaderboard_data: Optional[Dict] = None) -> str:
        status_hint = (leaderboard_data or {}).get("tournamentStatus", "").lower()
        now = datetime.now(LEAGUE_TZ)
        start = tournament.start_date if tournament.start_date.tzinfo else LEAGUE_TZ.localize(tournament.start_date)
        end = tournament.end_date if tournament.end_date.tzinfo else LEAGUE_TZ.localize(tournament.end_date)

        if "complete" in status_hint:
            tournament.status = "complete"
        elif now >= end:
            tournament.status = "complete"
        elif "progress" in status_hint or "live" in status_hint:
            tournament.status = "active"
        elif now >= start:
            tournament.status = "active"
        else:
            tournament.status = "upcoming"
        return tournament.status

    def _apply_fixed_deadline(self, tournament: Tournament) -> datetime:
        """Set a deterministic pick deadline when tee times aren't available."""
        start_localized = tournament.start_date
        if start_localized.tzinfo is None:
            start_localized = LEAGUE_TZ.localize(start_localized)

        fixed_deadline = start_localized.replace(
            hour=self.fallback_deadline_hour,
            minute=0,
            second=0,
            microsecond=0,
        )
        tournament.pick_deadline = fixed_deadline
        return fixed_deadline

    @staticmethod
    def _parse_api_number(value):
        """Parse MongoDB-style number format from API."""
        if isinstance(value, dict):
            if '$numberInt' in value:
                return int(value['$numberInt'])
            if '$numberLong' in value:
                return int(value['$numberLong'])
        return int(value) if value else 0

    def sync_schedule(self, year: int, tournament_names: List[str] = None) -> int:
        """
        Import season schedule from API.

        Args:
            year: Season year (e.g., 2026)
            tournament_names: Optional list of tournament names to include.
                            If None, imports all non-opposite-field events.

        Returns:
            Number of tournaments imported
        """
        data = self.api.get_schedule(str(year))
        if not data or "schedule" not in data:
            print("Failed to fetch schedule")
            return 0

        imported = 0
        week_number = 1

        for event in data["schedule"]:
            name = event.get("name", "")

            # Skip if we have a filter and this tournament isn't in it
            if tournament_names and name not in tournament_names:
                continue

            # Skip excluded tournaments (opposite-field, playoffs finale, special events)
            if name in EXCLUDED_TOURNAMENTS:
                continue

            # Skip team events detection (Zurich) - we'll handle specially
            is_team_event = event.get("format") == "team"

            # Check if already exists
            existing = Tournament.query.filter_by(
                api_tourn_id=event["tournId"],
                season_year=year
            ).first()

            if existing:
                # Update existing
                existing.name = name
                # Only update purse if API provides non-zero value
                api_purse = self._parse_api_number(event.get("purse", 0))
                if api_purse > 0:
                    existing.purse = api_purse
                existing.is_team_event = is_team_event
            else:
                # Parse dates (MongoDB-style timestamp format)
                start_ts = int(event["date"]["start"]["$date"]["$numberLong"]) / 1000
                end_ts = int(event["date"]["end"]["$date"]["$numberLong"]) / 1000
                start_date = datetime.fromtimestamp(start_ts, tz=pytz.UTC)
                end_date = datetime.fromtimestamp(end_ts, tz=pytz.UTC)

                tournament = Tournament(
                    api_tourn_id=event["tournId"],
                    name=name,
                    season_year=year,
                    start_date=start_date,
                    end_date=end_date,
                    purse=self._parse_api_number(event.get("purse", 0)) or PURSE_ESTIMATES.get(name, DEFAULT_PURSE),
                    is_team_event=is_team_event,
                    week_number=week_number,
                    status="upcoming"
                )
                db.session.add(tournament)
                imported += 1
                week_number += 1

        db.session.commit()
        print(f"Imported {imported} tournaments for {year}")
        return imported

    def sync_tournament_field(self, tournament: Tournament) -> Tuple[int, Optional[datetime]]:
        """
        Sync tournament field and get first tee time.
        Call this Tuesday before the tournament.

        Args:
            tournament: Tournament object to sync

        Returns:
            Tuple of (players_synced, first_tee_time)
        """
        # Get leaderboard data (has field + tee times)
        data = self.api.get_leaderboard(tournament.api_tourn_id, str(tournament.season_year))

        if not data or "leaderboardRows" not in data:
            logger.error("Failed to fetch leaderboard for %s", tournament.name)
            return 0, None

        players_synced = 0
        first_tee_time = None
        event_tz = self._get_event_timezone(data)

        try:
            if True:  # removed db.session.begin() - Flask-SQLAlchemy manages transactions
                for player_data in data["leaderboardRows"]:
                    if player_data.get("isAmateur", False):
                        continue

                    player = Player.query.filter_by(
                        api_player_id=player_data["playerId"]
                    ).first()

                    if not player:
                        player = Player(
                            api_player_id=player_data["playerId"],
                            first_name=player_data.get("firstName", ""),
                            last_name=player_data.get("lastName", ""),
                            is_amateur=player_data.get("isAmateur", False)
                        )
                        db.session.add(player)
                        db.session.flush()

                    field_entry = TournamentField.query.filter_by(
                        tournament_id=tournament.id,
                        player_id=player.id
                    ).first()

                    if not field_entry:
                        field_entry = TournamentField(
                            tournament_id=tournament.id,
                            player_id=player.id
                        )
                        db.session.add(field_entry)
                        players_synced += 1

                    # Prefer timestamp (timezone-safe) over string (ambiguous)
                    tee_time = self._parse_tee_time_timestamp(player_data.get("teeTimeTimestamp"))
                    if not tee_time:
                        # Fallback to string parsing if timestamp not available
                        tee_time = (
                            self._parse_tee_time(player_data.get("teeTime"), tournament.start_date, event_tz)
                            or self._parse_tee_time(player_data.get("teeTimeLocal"), tournament.start_date, event_tz)
                        )
                    if tee_time and (first_tee_time is None or tee_time < first_tee_time):
                        first_tee_time = tee_time

                if first_tee_time:
                    tournament.pick_deadline = first_tee_time
                    logger.info("Set deadline for %s: %s", tournament.name, first_tee_time)

                self._derive_status(tournament, data)

                if not first_tee_time and self.is_free_mode:
                    fallback_deadline = self._apply_fixed_deadline(tournament)
                    logger.info(
                        "Free tier: using fixed pick deadline %s for %s (tee times unavailable)",
                        fallback_deadline,
                        tournament.name,
                    )
                elif not tournament.pick_deadline:
                    fallback_deadline = self._apply_fixed_deadline(tournament)
                    logger.info(
                        "Applied fallback pick deadline %s for %s",
                        fallback_deadline,
                        tournament.name,
                    )
                db.session.commit()
            logger.info("Synced %s players for %s", players_synced, tournament.name)
        except Exception:
            db.session.rollback()
            logger.exception("Failed syncing field for %s", tournament.name)
        return players_synced, first_tee_time

    def sync_tournament_results(self, tournament: Tournament) -> int:
        """
        Sync tournament results after completion.
        Call this Sunday night/Monday after tournament ends.

        Args:
            tournament: Tournament object to sync

        Returns:
            Number of results synced
        """
        earnings_data = self.api.get_earnings(tournament.api_tourn_id, str(tournament.season_year))

        if not earnings_data or "leaderboard" not in earnings_data:
            logger.error("Failed to fetch earnings for %s", tournament.name)
            return 0

        leaderboard_data = self.api.get_leaderboard(tournament.api_tourn_id, str(tournament.season_year))

        leaderboard_lookup = {}
        if leaderboard_data and "leaderboardRows" in leaderboard_data:
            for p in leaderboard_data["leaderboardRows"]:
                leaderboard_lookup[p["playerId"]] = p

        results_synced = 0

        try:
            for player_data in earnings_data["leaderboard"]:
                player_id = player_data["playerId"]

                player = Player.query.filter_by(api_player_id=player_id).first()
                if not player:
                    continue

                lb_info = leaderboard_lookup.get(player_id, {})
                rounds_completed = len(lb_info.get("rounds", []))
                status = lb_info.get("status", "complete")

                result = TournamentResult.query.filter_by(
                    tournament_id=tournament.id,
                    player_id=player.id
                ).first()

                if not result:
                    result = TournamentResult(
                        tournament_id=tournament.id,
                        player_id=player.id
                    )
                    db.session.add(result)

                earnings_raw = player_data.get("earnings", 0)
                if isinstance(earnings_raw, dict) and '$numberInt' in earnings_raw:
                    result.earnings = int(earnings_raw['$numberInt'])
                elif isinstance(earnings_raw, dict) and '$numberLong' in earnings_raw:
                    result.earnings = int(earnings_raw['$numberLong'])
                else:
                    result.earnings = int(earnings_raw) if earnings_raw else 0

                result.status = status
                result.rounds_completed = rounds_completed
                result.final_position = lb_info.get("position", "")

                results_synced += 1

            tournament.status = "complete"
            db.session.commit()

            logger.info("Synced %s results for %s", results_synced, tournament.name)
        except Exception:
            db.session.rollback()
            logger.exception("Failed syncing results for %s", tournament.name)
            return 0
        return results_synced

    def process_tournament_picks(self, tournament: Tournament) -> int:
        """
        Process all picks for a completed tournament.
        Calculates points and updates user totals.

        Args:
            tournament: Completed tournament to process

        Returns:
            Number of picks processed
        """
        if tournament.status != "complete":
            logger.warning("Tournament %s is not complete", tournament.name)
            return 0

        picks = Pick.query.filter_by(tournament_id=tournament.id).all()
        processed = 0
        skipped = 0

        for pick in picks:
            try:
                resolved = pick.resolve_pick()
                if not resolved:
                    skipped += 1
                    continue

                pick.user.calculate_total_points()
                processed += 1
            except Exception as exc:  # noqa: BLE001 - continue to next pick
                logger.warning(
                    "Skipped pick %s for %s: %s",
                    pick.id,
                    tournament.id,
                    exc,
                )

        db.session.commit()

        logger.info(
            "Processed %s picks for %s (skipped %s)",
            processed,
            tournament.name,
            skipped,
        )

        return processed

    def check_withdrawals(self, tournament: Tournament) -> List[Dict]:
        """
        Check for withdrawals during a tournament.
        Useful for monitoring mid-tournament.

        Args:
            tournament: Active tournament to check

        Returns:
            List of withdrawal info dicts
        """
        if self.is_free_mode:
            logger.info("Free tier: skipping withdrawal check for %s", tournament.name)
            return []

        data = self.api.get_leaderboard(tournament.api_tourn_id, str(tournament.season_year))

        if not data or "leaderboardRows" not in data:
            return []

        withdrawals = []

        try:
            for player_data in data["leaderboardRows"]:
                if player_data.get("status") != "wd":
                    continue

                rounds = player_data.get("rounds", [])
                rounds_completed = len(rounds)

                player = Player.query.filter_by(api_player_id=player_data["playerId"]).first()
                if not player:
                    continue

                result = TournamentResult.query.filter_by(
                    tournament_id=tournament.id,
                    player_id=player.id
                ).first()

                if not result:
                    result = TournamentResult(
                        tournament_id=tournament.id,
                        player_id=player.id
                    )
                    db.session.add(result)

                result.status = "wd"
                result.rounds_completed = rounds_completed
                result.final_position = player_data.get("position", "")

                withdrawals.append({
                    "player_id": player_data["playerId"],
                    "name": f"{player_data.get('firstName', '')} {player_data.get('lastName', '')}",
                    "rounds_completed": rounds_completed,
                    "wd_before_r2": rounds_completed < 2
                })

            db.session.commit()
        except Exception:
            db.session.rollback()
            logger.exception("Failed checking withdrawals for %s", tournament.name)

        return withdrawals

    def sync_live_leaderboard(self, tournament: Tournament) -> int:
        """Update live leaderboard data for an active tournament."""
        if self.is_free_mode:
            logger.info("Free tier: skipping live leaderboard sync for %s", tournament.name)
            return 0

        data = self.api.get_leaderboard(tournament.api_tourn_id, str(tournament.season_year))
        if not data or "leaderboardRows" not in data:
            logger.error("Failed to fetch leaderboard for %s", tournament.name)
            return 0

        updated = 0

        try:
            self._update_pick_deadline_from_leaderboard(tournament, data)
            self._derive_status(tournament, data)

            for player_data in data.get("leaderboardRows", []):
                player = Player.query.filter_by(api_player_id=player_data.get("playerId")).first()
                if not player:
                    continue

                result = TournamentResult.query.filter_by(
                    tournament_id=tournament.id,
                    player_id=player.id
                ).first()

                if not result:
                    result = TournamentResult(
                        tournament_id=tournament.id,
                        player_id=player.id
                    )
                    db.session.add(result)

                result.status = player_data.get("status", result.status or "in_progress")
                result.rounds_completed = len(player_data.get("rounds", []))
                result.final_position = player_data.get("position", result.final_position)

                updated += 1

            db.session.commit()
            logger.info("Updated live leaderboard for %s (%s entries)", tournament.name, updated)
        except Exception:
            db.session.rollback()
            logger.exception("Failed updating live leaderboard for %s", tournament.name)
            return 0

        return updated


def get_upcoming_tournament(days_ahead: int = 7) -> Optional[Tournament]:
    """Get the next upcoming tournament within specified days."""
    now = datetime.now(LEAGUE_TZ)
    cutoff = now + timedelta(days=days_ahead)

    return Tournament.query.filter(
        Tournament.status == "upcoming",
        Tournament.start_date <= cutoff,
        Tournament.start_date >= now
    ).order_by(Tournament.start_date).first()


def get_just_completed_tournament() -> Optional[Tournament]:
    """Get tournament that just completed (ended within last 24 hours)."""
    now = datetime.now(LEAGUE_TZ)
    yesterday = now - timedelta(days=1)

    return Tournament.query.filter(
        Tournament.status == "active",
        Tournament.end_date <= now,
        Tournament.end_date >= yesterday
    ).first()


def _refresh_statuses(tournaments):
    now = datetime.now(LEAGUE_TZ)
    changed = False
    for tournament in tournaments:
        previous = tournament.status
        tournament.update_status_from_time(now)
        if tournament.status != previous:
            changed = True
    if changed:
        db.session.commit()


def get_upcoming_tournaments_window(days_ahead: int = 10) -> List[Tournament]:
    now = datetime.now(LEAGUE_TZ)
    cutoff = now + timedelta(days=days_ahead)
    tournaments = Tournament.query.filter(
        Tournament.start_date <= cutoff,
        Tournament.end_date >= now,
        Tournament.status != "complete",
    ).order_by(Tournament.start_date).all()
    _refresh_statuses(tournaments)
    return tournaments


def get_active_tournaments(include_upcoming_hours: int = 12) -> List[Tournament]:
    now = datetime.now(LEAGUE_TZ)
    window_start = now - timedelta(hours=6)
    window_end = now + timedelta(hours=include_upcoming_hours)
    tournaments = Tournament.query.filter(
        Tournament.start_date <= window_end,
        Tournament.end_date >= window_start,
        Tournament.status != "complete",
    ).order_by(Tournament.start_date).all()
    _refresh_statuses(tournaments)
    return tournaments


def get_recently_completed_tournaments(days_back: int = 2) -> List[Tournament]:
    now = datetime.now(LEAGUE_TZ)
    since = now - timedelta(days=days_back)
    tournaments = Tournament.query.filter(
        Tournament.end_date >= since,
        Tournament.end_date <= now + timedelta(hours=12),
    ).order_by(Tournament.end_date.desc()).all()
    _refresh_statuses(tournaments)
    return tournaments


# ============================================================================
# CLI Commands for manual sync
# ============================================================================

def register_sync_commands(app):
    """Register sync CLI commands with Flask app."""

    sync_mode = app.config.get('SYNC_MODE', 'standard').lower()
    fallback_deadline_hour = app.config.get('FIXED_DEADLINE_HOUR_CT', 7)

    @app.cli.command('sync-schedule')
    def sync_schedule_cmd():
        """Import season schedule from API."""
        import os

        api_key = os.environ.get('SLASHGOLF_API_KEY')
        if not api_key:
            print("Error: SLASHGOLF_API_KEY not set")
            return

        api = SlashGolfAPI(api_key, sync_mode=sync_mode)
        sync = TournamentSync(api, sync_mode=sync_mode, fallback_deadline_hour=fallback_deadline_hour)

        year = app.config.get('SEASON_YEAR', 2026)
        sync.sync_schedule(year)

    @app.cli.command('sync-field')
    def sync_field_cmd():
        """Sync field for upcoming tournament."""
        import os

        api_key = os.environ.get('SLASHGOLF_API_KEY')
        if not api_key:
            print("Error: SLASHGOLF_API_KEY not set")
            return

        tournament = get_upcoming_tournament()
        if not tournament:
            print("No upcoming tournament found")
            return

        api = SlashGolfAPI(api_key, sync_mode=sync_mode)
        sync = TournamentSync(api, sync_mode=sync_mode, fallback_deadline_hour=fallback_deadline_hour)
        sync.sync_tournament_field(tournament)

    @app.cli.command('sync-results')
    def sync_results_cmd():
        """Sync results for just-completed tournament."""
        import os

        api_key = os.environ.get('SLASHGOLF_API_KEY')
        if not api_key:
            print("Error: SLASHGOLF_API_KEY not set")
            return

        # Find tournament to process
        tournament = Tournament.query.filter_by(status="active").first()
        if not tournament:
            print("No active tournament to process")
            return

        api = SlashGolfAPI(api_key, sync_mode=sync_mode)
        sync = TournamentSync(api, sync_mode=sync_mode, fallback_deadline_hour=fallback_deadline_hour)

        # Sync results
        sync.sync_tournament_results(tournament)

        # Process picks
        sync.process_tournament_picks(tournament)

    @app.cli.command('check-wd')
    def check_wd_cmd():
        """Check for withdrawals in active tournament."""
        import os

        api_key = os.environ.get('SLASHGOLF_API_KEY')
        if not api_key:
            print("Error: SLASHGOLF_API_KEY not set")
            return

        tournament = Tournament.query.filter_by(status="active").first()
        if not tournament:
            print("No active tournament")
            return

        api = SlashGolfAPI(api_key, sync_mode=sync_mode)
        sync = TournamentSync(api, sync_mode=sync_mode, fallback_deadline_hour=fallback_deadline_hour)

        withdrawals = sync.check_withdrawals(tournament)

        if withdrawals:
            print(f"\nWithdrawals in {tournament.name}:")
            for wd in withdrawals:
                status = "BEFORE R2" if wd["wd_before_r2"] else f"after R{wd['rounds_completed']}"
                print(f"  - {wd['name']}: WD {status}")
        else:
            print("No withdrawals")

    @app.cli.command('sync-run')
    @click.option('--mode', type=click.Choice(['schedule', 'field', 'live', 'withdrawals', 'results', 'all']), required=True)
    def sync_run_cmd(mode):
        """Unified automation entrypoint for scheduled tasks."""
        api_key = os.environ.get('SLASHGOLF_API_KEY')
        if not api_key:
            click.echo("Error: SLASHGOLF_API_KEY not set")
            sys.exit(1)

        api = SlashGolfAPI(api_key, sync_mode=sync_mode)
        sync = TournamentSync(api, sync_mode=sync_mode, fallback_deadline_hour=fallback_deadline_hour)
        exit_code = 0
        year = app.config.get('SEASON_YEAR', datetime.now().year)

        free_tier_blocked = {'live', 'withdrawals'}
        if sync_mode == 'free' and mode in free_tier_blocked:
            click.echo(f"Free tier mode: '{mode}' sync disabled to stay within RapidAPI limits")
            sys.exit(0)

        try:
            if mode in ('schedule', 'all'):
                imported = sync.sync_schedule(year)
                click.echo(f"Schedule sync complete ({imported} imported/updated)")

            if mode in ('field', 'all'):
                if sync_mode == 'free' and datetime.now(LEAGUE_TZ).weekday() not in (1, 2):
                    click.echo("Free tier: field sync limited to Tue/Wed to control API usage")
                else:
                    upcoming = get_upcoming_tournaments_window()
                    if not upcoming:
                        click.echo("No upcoming tournaments to sync field for")
                    for tournament in upcoming:
                        sync.sync_tournament_field(tournament)

            if mode in ('live', 'all'):
                if sync_mode == 'free':
                    click.echo("Free tier: skipping live leaderboard refresh")
                else:
                    active = get_active_tournaments()
                    if not active:
                        click.echo("No active tournaments for live sync")
                    for tournament in active:
                        sync.sync_live_leaderboard(tournament)

            if mode in ('withdrawals', 'all'):
                if sync_mode == 'free':
                    click.echo("Free tier: skipping withdrawal monitoring (handled during results sync)")
                else:
                    active = get_active_tournaments()
                    if not active:
                        click.echo("No active tournaments for withdrawal checks")
                    for tournament in active:
                        withdrawals = sync.check_withdrawals(tournament)
                        if withdrawals:
                            click.echo(f"Withdrawals detected for {tournament.name}: {len(withdrawals)}")

            if mode in ('results', 'all'):
                if sync_mode == 'free' and datetime.now(LEAGUE_TZ).weekday() not in (0, 6):
                    click.echo("Free tier: results sync runs Sunday night or Monday morning only")
                else:
                    recent = get_recently_completed_tournaments()
                    if not recent:
                        click.echo("No recently completed tournaments to process")
                    for tournament in recent:
                        results_count = sync.sync_tournament_results(tournament)
                        if results_count:
                            sync.process_tournament_picks(tournament)

        except Exception:
            logger.exception("sync-run failed")
            exit_code = 1

        sys.exit(exit_code)
