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

import requests
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
import pytz

from models import db, Tournament, Player, TournamentField, TournamentResult, Pick, LEAGUE_TZ


class SlashGolfAPI:
    """Client for SlashGolf API."""
    
    # RapidAPI configuration
    BASE_URL = "https://live-golf-data.p.rapidapi.com"
    
    def __init__(self, api_key: str, api_host: str = "live-golf-data.p.rapidapi.com"):
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
    
    def _make_request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """Make API request with error handling."""
        url = f"{self.BASE_URL}/{endpoint}"
        
        if params is None:
            params = {}
        params["orgId"] = self.org_id
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"API Error {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            print(f"Request failed: {e}")
            return None
    
    def get_schedule(self, year: str) -> Optional[Dict]:
        """Get full season schedule."""
        return self._make_request("schedule", {"year": year})
    
    def get_tournament(self, tourn_id: str, year: str) -> Optional[Dict]:
        """Get tournament details including field."""
        return self._make_request("tournaments", {"tournId": tourn_id, "year": year})
    
    def get_leaderboard(self, tourn_id: str, year: str) -> Optional[Dict]:
        """Get leaderboard with tee times, status, rounds."""
        return self._make_request("leaderboard", {"tournId": tourn_id, "year": year})
    
    def get_earnings(self, tourn_id: str, year: str) -> Optional[Dict]:
        """Get earnings/prize money for completed tournament."""
        return self._make_request("earnings", {"tournId": tourn_id, "year": year})


class TournamentSync:
    """Sync tournament data from API to database."""
    
    def __init__(self, api: SlashGolfAPI):
        self.api = api
    
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
                existing.purse = event.get("purse", 0)
                existing.is_team_event = is_team_event
            else:
                # Parse dates
                start_date = datetime.fromisoformat(event["date"]["start"].replace("Z", "+00:00"))
                end_date = datetime.fromisoformat(event["date"]["end"].replace("Z", "+00:00"))
                
                tournament = Tournament(
                    api_tourn_id=event["tournId"],
                    name=name,
                    season_year=year,
                    start_date=start_date,
                    end_date=end_date,
                    purse=event.get("purse", 0),
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
        
        if not data or "leaderboard" not in data:
            print(f"Failed to fetch leaderboard for {tournament.name}")
            return 0, None
        
        players_synced = 0
        first_tee_time = None
        
        for player_data in data["leaderboard"]:
            # Skip amateurs
            if player_data.get("isAmateur", False):
                continue
            
            # Get or create player
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
                db.session.flush()  # Get player.id
            
            # Add to tournament field if not already
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
            
            # Track earliest tee time
            tee_time_str = player_data.get("teeTimeTimestamp")
            if tee_time_str:
                tee_time = datetime.fromisoformat(tee_time_str.replace("Z", "+00:00"))
                if first_tee_time is None or tee_time < first_tee_time:
                    first_tee_time = tee_time
        
        # Set pick deadline to first tee time
        if first_tee_time:
            tournament.pick_deadline = first_tee_time
            print(f"Set deadline for {tournament.name}: {first_tee_time}")
        
        # Update tournament status
        tournament.status = "upcoming"
        
        db.session.commit()
        print(f"Synced {players_synced} players for {tournament.name}")
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
        # Get earnings data
        earnings_data = self.api.get_earnings(tournament.api_tourn_id, str(tournament.season_year))
        
        if not earnings_data or "leaderboard" not in earnings_data:
            print(f"Failed to fetch earnings for {tournament.name}")
            return 0
        
        # Get leaderboard for status/rounds info
        leaderboard_data = self.api.get_leaderboard(tournament.api_tourn_id, str(tournament.season_year))
        
        # Build lookup for leaderboard data
        leaderboard_lookup = {}
        if leaderboard_data and "leaderboard" in leaderboard_data:
            for p in leaderboard_data["leaderboard"]:
                leaderboard_lookup[p["playerId"]] = p
        
        results_synced = 0
        
        for player_data in earnings_data["leaderboard"]:
            player_id = player_data["playerId"]
            
            # Get player from our database
            player = Player.query.filter_by(api_player_id=player_id).first()
            if not player:
                continue
            
            # Get leaderboard info for this player
            lb_info = leaderboard_lookup.get(player_id, {})
            
            # Determine rounds completed
            rounds = lb_info.get("rounds", [])
            rounds_completed = len(rounds)
            
            # Get status
            status = lb_info.get("status", "complete")
            
            # Get or create result
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
            
            # Update result
            result.earnings = player_data.get("earnings", 0)
            result.status = status
            result.rounds_completed = rounds_completed
            result.final_position = lb_info.get("position", "")
            
            results_synced += 1
        
        # Mark tournament as complete
        tournament.status = "complete"
        
        db.session.commit()
        print(f"Synced {results_synced} results for {tournament.name}")
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
            print(f"Tournament {tournament.name} is not complete")
            return 0
        
        picks = Pick.query.filter_by(tournament_id=tournament.id).all()
        processed = 0
        
        for pick in picks:
            # Resolve which player was active and calculate points
            pick.resolve_pick()
            
            # Update user's total points
            pick.user.calculate_total_points()
            
            processed += 1
        
        db.session.commit()
        print(f"Processed {processed} picks for {tournament.name}")
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
        data = self.api.get_leaderboard(tournament.api_tourn_id, str(tournament.season_year))
        
        if not data or "leaderboard" not in data:
            return []
        
        withdrawals = []
        
        for player_data in data["leaderboard"]:
            if player_data.get("status") == "wd":
                rounds = player_data.get("rounds", [])
                withdrawals.append({
                    "player_id": player_data["playerId"],
                    "name": f"{player_data.get('firstName', '')} {player_data.get('lastName', '')}",
                    "rounds_completed": len(rounds),
                    "wd_before_r2": len(rounds) < 2
                })
        
        return withdrawals


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


# ============================================================================
# CLI Commands for manual sync
# ============================================================================

def register_sync_commands(app):
    """Register sync CLI commands with Flask app."""
    
    @app.cli.command('sync-schedule')
    def sync_schedule_cmd():
        """Import season schedule from API."""
        import os
        
        api_key = os.environ.get('SLASHGOLF_API_KEY')
        if not api_key:
            print("Error: SLASHGOLF_API_KEY not set")
            return
        
        api = SlashGolfAPI(api_key)
        sync = TournamentSync(api)
        
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
        
        api = SlashGolfAPI(api_key)
        sync = TournamentSync(api)
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
        
        api = SlashGolfAPI(api_key)
        sync = TournamentSync(api)
        
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
        
        api = SlashGolfAPI(api_key)
        sync = TournamentSync(api)
        
        withdrawals = sync.check_withdrawals(tournament)
        
        if withdrawals:
            print(f"\nWithdrawals in {tournament.name}:")
            for wd in withdrawals:
                status = "BEFORE R2" if wd["wd_before_r2"] else f"after R{wd['rounds_completed']}"
                print(f"  - {wd['name']}: WD {status}")
        else:
            print("No withdrawals")
