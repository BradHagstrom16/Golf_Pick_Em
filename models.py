"""
Golf Pick 'Em League - Database Models
======================================
SQLAlchemy models for the golf pick 'em fantasy league.

Core Concepts:
- Users pick one golfer (primary + backup) per tournament
- Points = actual prize money earned by their active pick
- Each golfer can only be used once per season
- Backup activates only if primary WDs before completing Round 2
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import pytz

db = SQLAlchemy()

# Timezone for the league (Central Time)
LEAGUE_TZ = pytz.timezone('America/Chicago')


class User(UserMixin, db.Model):
    """
    Contestant in the pick 'em league.
    """
    __tablename__ = 'user'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    display_name = db.Column(db.String(100), nullable=True)
    
    # Season standings
    total_points = db.Column(db.Integer, default=0)  # Sum of all earnings
    
    # Admin & payment tracking
    is_admin = db.Column(db.Boolean, default=False)
    has_paid = db.Column(db.Boolean, default=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    picks = db.relationship('Pick', backref='user', lazy='dynamic')
    
    def set_password(self, password):
        """Hash and store password."""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Verify password against hash."""
        return check_password_hash(self.password_hash, password)
    
    def get_display_name(self):
        """Return display name or username."""
        return self.display_name or self.username
    
    def get_used_player_ids(self):
        """
        Get list of player IDs this user has 'used' (locked) for the season.
        A player is used if they were the active pick in a completed tournament.
        """
        return [usage.player_id for usage in self.season_usages]
    
    def calculate_total_points(self):
        """Recalculate total points from all completed picks."""
        total = 0
        for pick in self.picks:
            if pick.tournament.status == 'complete' and pick.points_earned:
                total += pick.points_earned
        self.total_points = total
        return total
    
    def __repr__(self):
        return f'<User {self.username}>'


class Player(db.Model):
    """
    A PGA Tour golfer. Synced from SlashGolf API.
    """
    __tablename__ = 'player'
    
    id = db.Column(db.Integer, primary_key=True)
    api_player_id = db.Column(db.String(20), unique=True, nullable=False)  # SlashGolf player ID
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    is_amateur = db.Column(db.Boolean, default=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tournament_results = db.relationship('TournamentResult', backref='player', lazy='dynamic')
    
    def full_name(self):
        """Return full name."""
        return f"{self.first_name} {self.last_name}"
    
    def __repr__(self):
        return f'<Player {self.first_name} {self.last_name}>'


class Tournament(db.Model):
    """
    A PGA Tour tournament. Synced from SlashGolf API.
    """
    __tablename__ = 'tournament'
    
    id = db.Column(db.Integer, primary_key=True)
    api_tourn_id = db.Column(db.String(20), nullable=False)  # SlashGolf tournament ID
    name = db.Column(db.String(200), nullable=False)
    season_year = db.Column(db.Integer, nullable=False)  # e.g., 2026
    
    # Dates
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    pick_deadline = db.Column(db.DateTime, nullable=True)  # First tee time Thursday
    
    # Tournament details
    purse = db.Column(db.Integer, default=0)  # Total purse in dollars
    is_team_event = db.Column(db.Boolean, default=False)  # True for Zurich Classic
    
    # Status tracking
    status = db.Column(db.String(20), default='upcoming')  # upcoming, active, complete
    
    # Week number in our league (1-32)
    week_number = db.Column(db.Integer, nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    picks = db.relationship('Pick', backref='tournament', lazy='dynamic')
    results = db.relationship('TournamentResult', backref='tournament', lazy='dynamic')
    field = db.relationship('TournamentField', backref='tournament', lazy='dynamic')

    __table_args__ = (
        db.UniqueConstraint('api_tourn_id', 'season_year', name='unique_tournament_per_season'),
    )
    
    def is_deadline_passed(self):
        """Check if pick deadline has passed."""
        if not self.pick_deadline:
            return False
        now = datetime.now(LEAGUE_TZ)
        deadline = self.pick_deadline
        if deadline.tzinfo is None:
            deadline = LEAGUE_TZ.localize(deadline)
        return now > deadline

    def update_status_from_time(self, current_time: datetime = None):
        """Derive tournament status based on start/end dates and deadlines."""
        now = current_time or datetime.now(LEAGUE_TZ)
        if self.status != 'complete':
            deadline = self.pick_deadline or self.start_date
            deadline_localized = deadline if deadline.tzinfo else LEAGUE_TZ.localize(deadline)
            start_localized = self.start_date if self.start_date.tzinfo else LEAGUE_TZ.localize(self.start_date)
            end_localized = self.end_date if self.end_date.tzinfo else LEAGUE_TZ.localize(self.end_date)

            if now >= end_localized:
                self.status = 'complete'
            elif now >= start_localized:
                self.status = 'active'
            elif now >= deadline_localized:
                self.status = 'upcoming'
        return self.status
    
    def get_deadline_display(self):
        """Return formatted deadline string."""
        if not self.pick_deadline:
            return "TBD"
        deadline = self.pick_deadline
        if deadline.tzinfo is None:
            deadline = LEAGUE_TZ.localize(deadline)
        return deadline.strftime('%a %b %d, %I:%M %p CT')
    
    def __repr__(self):
        return f'<Tournament {self.name} ({self.season_year})>'


class TournamentField(db.Model):
    """
    Players in a tournament's field. Synced from API before tournament starts.
    This is separate from TournamentResult to track the pre-tournament field.
    """
    __tablename__ = 'tournament_field'
    
    id = db.Column(db.Integer, primary_key=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournament.id'), nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    
    # Field status
    is_alternate = db.Column(db.Boolean, default=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship to player
    player = db.relationship('Player', backref='field_entries')
    
    # Unique constraint: player can only be in field once per tournament
    __table_args__ = (
        db.UniqueConstraint('tournament_id', 'player_id', name='unique_player_tournament_field'),
    )
    
    def __repr__(self):
        return f'<TournamentField {self.tournament_id} - {self.player_id}>'


class SeasonPlayerUsage(db.Model):
    """Tracks whether a user has consumed a player for a given season."""

    __tablename__ = 'season_player_usage'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    season_year = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'player_id', 'season_year', name='unique_player_usage'),
    )

    user = db.relationship('User', backref='season_usages')
    player = db.relationship('Player')


class TournamentResult(db.Model):
    """
    A player's result in a completed tournament. Synced from API after tournament.
    """
    __tablename__ = 'tournament_result'
    
    id = db.Column(db.Integer, primary_key=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournament.id'), nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    
    # Result details
    status = db.Column(db.String(20), nullable=False)  # complete, cut, wd, dq
    final_position = db.Column(db.String(20), nullable=True)  # "1", "T5", "CUT", etc.
    earnings = db.Column(db.Integer, default=0)  # Prize money in dollars
    rounds_completed = db.Column(db.Integer, default=0)  # 0-4, key for WD timing
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Unique constraint: one result per player per tournament
    __table_args__ = (
        db.UniqueConstraint('tournament_id', 'player_id', name='unique_player_tournament_result'),
    )
    
    def wd_before_round_2_complete(self):
        """Check if this was a WD before completing round 2."""
        return self.status == 'wd' and self.rounds_completed < 2
    
    def __repr__(self):
        return f'<TournamentResult {self.tournament_id} - {self.player_id}: {self.earnings}>'


class Pick(db.Model):
    """
    A user's pick for a specific tournament.
    
    Key Logic:
    - User selects primary_player and backup_player before deadline
    - After tournament: we determine which was the "active" pick
    - active_player_id stores who actually counted for points
    - primary_used/backup_used track which player is now "locked" for season
    
    WD Rules:
    - Primary WDs BEFORE completing R2 → Backup activates, primary returns to pool
    - Primary WDs AFTER completing R2 → Primary counts (0 pts), backup unused
    - Both WD before R2 → Primary is used (0 pts), backup returns to pool
    """
    __tablename__ = 'pick'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournament.id'), nullable=False)
    
    # The picks
    primary_player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    backup_player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    
    # Resolved after tournament completes
    active_player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=True)
    points_earned = db.Column(db.Integer, nullable=True)  # Set after tournament completes
    
    # Which players are now "used" for the season
    primary_used = db.Column(db.Boolean, default=False)
    backup_used = db.Column(db.Boolean, default=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    primary_player = db.relationship('Player', foreign_keys=[primary_player_id], backref='primary_picks')
    backup_player = db.relationship('Player', foreign_keys=[backup_player_id], backref='backup_picks')
    active_player = db.relationship('Player', foreign_keys=[active_player_id], backref='active_picks')
    
    # Unique constraint: one pick per user per tournament
    __table_args__ = (
        db.UniqueConstraint('user_id', 'tournament_id', name='unique_user_tournament_pick'),
    )
    
    def validate_availability(self, season_year: int):
        """Validate pick adheres to field eligibility and season usage constraints."""
        errors = []

        # Ensure players are in field
        field_player_ids = [entry.player_id for entry in TournamentField.query.filter_by(tournament_id=self.tournament_id)]
        if self.primary_player_id not in field_player_ids:
            errors.append('Primary player is not in the tournament field.')
        if self.backup_player_id not in field_player_ids:
            errors.append('Backup player is not in the tournament field.')

        # Ensure players are not reused this season
        existing_usage = SeasonPlayerUsage.query.filter(
            SeasonPlayerUsage.user_id == self.user_id,
            SeasonPlayerUsage.season_year == season_year,
            SeasonPlayerUsage.player_id.in_([self.primary_player_id, self.backup_player_id])
        ).all()
        used_ids = {usage.player_id for usage in existing_usage}
        if self.primary_player_id in used_ids:
            errors.append('Primary player has already been used this season.')
        if self.backup_player_id in used_ids:
            errors.append('Backup player has already been used this season.')

        return errors

    def resolve_pick(self):
        """
        Determine which player was active and calculate points.
        Call this after tournament results are imported.
        
        Returns tuple: (points_earned, active_player_id, primary_used, backup_used)
        """
        # Get results for both players
        primary_result = TournamentResult.query.filter_by(
            tournament_id=self.tournament_id,
            player_id=self.primary_player_id
        ).first()
        
        backup_result = TournamentResult.query.filter_by(
            tournament_id=self.tournament_id,
            player_id=self.backup_player_id
        ).first()
        
        if not primary_result:
            raise ValueError('Missing tournament result for primary player')

        # Determine if primary WD'd before completing R2
        primary_wd_early = (
            primary_result and
            primary_result.status == 'wd' and
            primary_result.rounds_completed < 2
        )
        
        # Case 1: Primary WD before R2 - backup activates
        if primary_wd_early:
            # Check if backup also WD'd before R2
            backup_wd_early = (
                backup_result and 
                backup_result.status == 'wd' and 
                backup_result.rounds_completed < 2
            )
            
            if backup_wd_early:
                # Both WD early: Primary is used with 0 points, backup returns to pool
                self.active_player_id = self.primary_player_id
                self.points_earned = 0
                self.primary_used = True
                self.backup_used = False
            else:
                # Backup activates
                self.active_player_id = self.backup_player_id
                earnings = backup_result.earnings if backup_result else None
                if earnings is None:
                    raise ValueError('Backup player missing result when required')

                # Handle team event (Zurich) - divide by 2
                if self.tournament.is_team_event:
                    earnings = earnings // 2

                self.points_earned = earnings
                self.primary_used = False  # Returns to pool
                self.backup_used = True
        
        # Case 2: Primary did not WD early (or didn't WD at all)
        else:
            self.active_player_id = self.primary_player_id
            earnings = primary_result.earnings if primary_result else None
            if earnings is None:
                raise ValueError('Primary player missing result when required')

            # Handle team event (Zurich) - divide by 2
            if self.tournament.is_team_event:
                earnings = earnings // 2
            
            self.points_earned = earnings
            self.primary_used = True
            self.backup_used = False
        
        # Record season usage for active player
        usage = SeasonPlayerUsage(
            user_id=self.user_id,
            player_id=self.active_player_id,
            season_year=self.tournament.season_year,
        )
        db.session.add(usage)

        return (self.points_earned, self.active_player_id, self.primary_used, self.backup_used)
    
    def __repr__(self):
        return f'<Pick User:{self.user_id} Tournament:{self.tournament_id}>'


# Helper function to get current time in league timezone
def get_current_time():
    """Get current time in league timezone."""
    return datetime.now(LEAGUE_TZ)
