"""
Golf Pick 'Em League - Main Application
========================================
Flask application with routes for the golf pick 'em fantasy league.
"""

import os
from functools import wraps
from datetime import datetime, timezone
import logging

import pytz
from email_validator import EmailNotValidError, validate_email
from urllib.parse import urlparse
from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_wtf.csrf import CSRFProtect, generate_csrf
from sqlalchemy import func

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from config import config
from models import db, User, Player, Tournament, TournamentField, TournamentResult, Pick, SeasonPlayerUsage, get_current_time, LEAGUE_TZ, format_score_to_par

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(config[os.environ.get('FLASK_ENV', 'default')])

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize extensions
db.init_app(app)
csrf = CSRFProtect(app)
limiter = Limiter(get_remote_address, app=app, default_limits=["200 per hour"])
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'


@login_manager.user_loader
def load_user(user_id):
    """Load user by ID for Flask-Login."""
    return User.query.get(int(user_id))


@app.before_request
def refresh_tournament_states():
    """Ensure tournament statuses reflect current time without manual intervention."""
    if not request.endpoint or request.endpoint in {"static"}:
        return

    now = get_current_time()
    refresh_interval = app.config.get("STATUS_REFRESH_INTERVAL_SECONDS", 300)
    last_refresh = app.config.get("_LAST_STATUS_REFRESH")

    if last_refresh and (now - last_refresh).total_seconds() < refresh_interval:
        return

    tournaments = Tournament.query.filter(
        Tournament.season_year == app.config['SEASON_YEAR'],
        Tournament.status.in_(['upcoming', 'active'])
    ).all()
    updated = False
    for tournament in tournaments:
        previous = tournament.status
        if tournament.update_status_from_time(now) != previous:
            updated = True
            logger.info("Auto-updated tournament %s status: %s -> %s", tournament.name, previous, tournament.status)
    if updated:
        db.session.commit()
    app.config["_LAST_STATUS_REFRESH"] = now


# ============================================================================
# Helpers
# ============================================================================

def get_cumulative_scores(users, season_year):
    """Calculate cumulative score to par using a single efficient query."""
    from sqlalchemy import and_

    rows = (
        db.session.query(
            Pick.user_id,
            func.sum(TournamentResult.score_to_par)
        )
        .join(Tournament, Pick.tournament_id == Tournament.id)
        .join(
            TournamentResult,
            and_(
                TournamentResult.tournament_id == Pick.tournament_id,
                TournamentResult.player_id == Pick.active_player_id
            )
        )
        .filter(
            Tournament.status == 'complete',
            Tournament.season_year == season_year,
            Pick.active_player_id.isnot(None),
            TournamentResult.score_to_par.isnot(None)
        )
        .group_by(Pick.user_id)
        .all()
    )

    score_map = {user_id: total for user_id, total in rows}

    cumulative = {}
    for user in users:
        total = score_map.get(user.id, 0) or 0
        cumulative[user.id] = {
            'total': total,
            'display': format_score_to_par(total)
        }
    return cumulative


# ============================================================================
# Decorators
# ============================================================================

def admin_required(f):
    """Decorator to require admin access."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Admin access required.', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function


# ============================================================================
# Context Processors
# ============================================================================

@app.context_processor
def inject_globals():
    """Inject global variables into all templates."""
    return {
        'current_time': get_current_time(),
        'season_year': app.config['SEASON_YEAR'],
        'csrf_token': generate_csrf
    }


# ============================================================================
# Public Routes
# ============================================================================

@app.route('/')
def index():
    """Home page with season standings."""
    # Get all users ordered by total points
    users = User.query.order_by(User.total_points.desc()).all()

    # Get tournament counts
    completed_tournaments = Tournament.query.filter_by(
        status='complete',
        season_year=app.config['SEASON_YEAR']
    ).count()

    total_tournaments = Tournament.query.filter_by(
        season_year=app.config['SEASON_YEAR']
    ).count()

    # Get next upcoming/active tournament
    next_tournament = Tournament.query.filter(
        Tournament.status.in_(['upcoming', 'active']),
        Tournament.season_year == app.config['SEASON_YEAR']
    ).order_by(Tournament.start_date).first()

    # Get most recent completed tournament
    last_completed = Tournament.query.filter_by(
        status='complete',
        season_year=app.config['SEASON_YEAR']
    ).order_by(Tournament.end_date.desc()).first()

    # Determine which tournament to feature
    featured_tournament = None
    upcoming_tournament = None

    if next_tournament:
        if next_tournament.status == 'active':
            featured_tournament = next_tournament
        else:
            field_count = TournamentField.query.filter_by(
                tournament_id=next_tournament.id
            ).count()

            if field_count > 0:
                featured_tournament = next_tournament
            else:
                featured_tournament = last_completed
                upcoming_tournament = next_tournament
    else:
        featured_tournament = last_completed

    # Determine if there's an active tournament (for showing season score vs active picks)
    has_active_tournament = (featured_tournament and featured_tournament.status == 'active')

    # Get picks for featured tournament (if deadline passed or complete)
    tournament_picks = {}
    show_picks = False
    if featured_tournament and (featured_tournament.status == 'complete' or featured_tournament.is_deadline_passed()):
        show_picks = True
        picks = Pick.query.filter_by(tournament_id=featured_tournament.id).all()
        for pick in picks:
            result = TournamentResult.query.filter_by(
                tournament_id=featured_tournament.id,
                player_id=pick.primary_player_id
            ).first()

            backup_activated = pick.is_backup_activated()

            backup_result = None
            if backup_activated and pick.backup_player_id:
                backup_result = TournamentResult.query.filter_by(
                    tournament_id=featured_tournament.id,
                    player_id=pick.backup_player_id
                ).first()

            if featured_tournament.status == 'active' and backup_activated and backup_result:
                earnings = backup_result.earnings or 0
            elif featured_tournament.status == 'active' and result:
                earnings = result.earnings or 0
            elif featured_tournament.status == 'complete' and pick.points_earned is not None:
                earnings = pick.points_earned
            else:
                earnings = result.earnings if result else 0

            # Determine displayed position and score: use backup's when activated
            if backup_activated and backup_result:
                display_position = backup_result.final_position
                display_score = format_score_to_par(backup_result.score_to_par)
            else:
                display_position = result.final_position if result else None
                display_score = format_score_to_par(result.score_to_par) if result else None

            tournament_picks[pick.user_id] = {
                'primary': pick.primary_player.full_name(),
                'position': display_position,
                'score': display_score,
                'primary_position': result.final_position if result else None,
                'earnings': earnings,
                'admin_override': pick.admin_override,
                'admin_override_note': pick.admin_override_note,
                'backup_activated': backup_activated,
                'backup_name': pick.backup_player.full_name() if pick.backup_player else None
            }

    # Get current user's pick for featured tournament (if logged in)
    user_pick = None
    if featured_tournament and current_user.is_authenticated:
        user_pick = Pick.query.filter_by(
            user_id=current_user.id,
            tournament_id=featured_tournament.id
        ).first()

    # Calculate cumulative scores (shown when no active tournament)
    cumulative_scores = {}
    if not has_active_tournament and completed_tournaments > 0:
        cumulative_scores = get_cumulative_scores(users, app.config['SEASON_YEAR'])

    return render_template('index.html',
                         users=users,
                         featured_tournament=featured_tournament,
                         upcoming_tournament=upcoming_tournament,
                         tournament_picks=tournament_picks,
                         show_picks=show_picks,
                         completed_tournaments=completed_tournaments,
                         total_tournaments=total_tournaments,
                         user_pick=user_pick,
                         has_active_tournament=has_active_tournament,
                         cumulative_scores=cumulative_scores)


@app.route('/leaderboard')
def leaderboard():
    """Redirect to home page (consolidated view)."""
    return redirect(url_for('index'))


@app.route('/schedule')
def schedule():
    """Tournament schedule for the season."""
    tournaments = Tournament.query.filter_by(
        season_year=app.config['SEASON_YEAR']
    ).order_by(Tournament.start_date).all()

    return render_template('schedule.html', tournaments=tournaments)


# ============================================================================
# Tournament Detail Route
# ============================================================================

@app.route('/tournament/<int:tournament_id>')
def tournament_detail(tournament_id):
    """
    Tournament detail page - shows different info based on tournament status:
    - Upcoming: Tournament info, deadline, field count
    - Active: Picks table with live position/score/earnings
    - Complete: Picks table with final results, conditionally showing backup column
    """
    tournament = Tournament.query.get_or_404(tournament_id)

    # Get all users (to show even those without picks)
    all_users = User.query.order_by(func.lower(User.username)).all()

    # Get picks for this tournament
    picks = Pick.query.filter_by(tournament_id=tournament_id).all()
    picks_by_user = {pick.user_id: pick for pick in picks}

    # Determine visibility flags
    show_picks = tournament.is_deadline_passed()

    # Get field count for upcoming tournaments
    field_count = TournamentField.query.filter_by(tournament_id=tournament_id).count()

    # Track if any backup was activated (to conditionally show backup column)
    any_backup_activated = False

    # Build results data for each user
    pick_results = []
    for user in all_users:
        pick = picks_by_user.get(user.id)

        if pick:
            # Get result for primary player
            primary_result = TournamentResult.query.filter_by(
                tournament_id=tournament_id,
                player_id=pick.primary_player_id
            ).first()

            # Get result for backup player
            backup_result = TournamentResult.query.filter_by(
                tournament_id=tournament_id,
                player_id=pick.backup_player_id
            ).first()

            # Determine backup activation
            backup_activated = False
            if tournament.status == 'complete' and pick.active_player_id:
                backup_activated = (pick.active_player_id == pick.backup_player_id)
            elif tournament.status == 'active' and primary_result:
                backup_activated = primary_result.wd_before_round_2_complete()

            if backup_activated:
                any_backup_activated = True

            # Determine display values based on tournament status
            if tournament.status == 'complete':
                points = pick.points_earned or 0
                # Get active player's result for position/score
                if pick.active_player_id:
                    active_result = TournamentResult.query.filter_by(
                        tournament_id=tournament_id,
                        player_id=pick.active_player_id
                    ).first()
                    position = active_result.final_position if active_result else None
                    score = format_score_to_par(active_result.score_to_par) if active_result else None
                else:
                    position = None
                    score = None
            else:
                # Active tournament - show primary's current status
                # (or backup's if backup activated)
                if backup_activated and backup_result:
                    points = backup_result.earnings or 0
                    position = backup_result.final_position
                    score = format_score_to_par(backup_result.score_to_par)
                else:
                    points = primary_result.earnings if primary_result else 0
                    position = primary_result.final_position if primary_result else None
                    score = format_score_to_par(primary_result.score_to_par) if primary_result else None

            pick_results.append({
                'user': user,
                'pick': pick,
                'primary_name': pick.primary_player.full_name(),
                'backup_name': pick.backup_player.full_name(),
                'primary_result': primary_result,
                'backup_result': backup_result,
                'position': position,
                'score': score,
                'points': points,
                'backup_activated': backup_activated,
                'has_pick': True,
                'admin_override': pick.admin_override,
                'admin_override_note': pick.admin_override_note
            })
        else:
            pick_results.append({
                'user': user,
                'pick': None,
                'primary_name': None,
                'backup_name': None,
                'primary_result': None,
                'backup_result': None,
                'position': None,
                'score': None,
                'points': 0,
                'backup_activated': False,
                'has_pick': False,
                'admin_override': False,
                'admin_override_note': None
            })

    # Sort results
    if tournament.status == 'complete' or show_picks:
        pick_results.sort(key=lambda x: (-x['points'], x['user'].get_display_name().lower()))
    else:
        pick_results.sort(key=lambda x: x['user'].get_display_name().lower())

    # Calculate summary stats
    total_picks = sum(1 for r in pick_results if r['has_pick'])
    total_points = sum(r['points'] for r in pick_results)
    max_points = max((r['points'] for r in pick_results), default=0)

    # Get current user's pick for this tournament
    user_pick = None
    if current_user.is_authenticated:
        user_pick = Pick.query.filter_by(
            user_id=current_user.id,
            tournament_id=tournament_id
        ).first()

    return render_template('tournament_detail.html',
                         tournament=tournament,
                         pick_results=pick_results,
                         show_picks=show_picks,
                         show_backup=any_backup_activated,
                         field_count=field_count,
                         total_picks=total_picks,
                         total_points=total_points,
                         max_points=max_points,
                         user_pick=user_pick)


# ============================================================================
# Also add a "Results" route that redirects to the most recent complete tournament
# ============================================================================

@app.route('/results')
def results():
    """Redirect to the most recently completed tournament."""
    tournament = Tournament.query.filter_by(
        status='complete',
        season_year=app.config['SEASON_YEAR']
    ).order_by(Tournament.end_date.desc()).first()

    if tournament:
        return redirect(url_for('tournament_detail', tournament_id=tournament.id))

    flash('No completed tournaments yet. Check back after the first tournament finishes!', 'info')
    return redirect(url_for('schedule'))



# ============================================================================
# Authentication Routes
# ============================================================================

@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def login():
    """User login."""
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        user = User.query.filter(func.lower(User.username) == username.lower()).first()

        if user and user.check_password(password):
            login_user(user, remember=True)
            flash(f'Welcome back, {user.get_display_name()}!', 'success')
            next_page = request.args.get('next')
            if next_page and urlparse(next_page).netloc:
                next_page = None  # Reject absolute URLs
            return redirect(next_page or url_for('index'))
        else:
            flash('Invalid username or password.', 'error')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    """User logout."""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration."""
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        display_name = request.form.get('display_name', '').strip() or None

        errors = []

        if len(username) < 3:
            errors.append('Username must be at least 3 characters.')

        if User.query.filter(func.lower(User.username) == username.lower()).first():
            errors.append('Username already taken.')

        try:
            validated_email = validate_email(email, check_deliverability=False).email
        except EmailNotValidError as exc:
            errors.append(str(exc))
            validated_email = None

        if validated_email and User.query.filter(func.lower(User.email) == validated_email.lower()).first():
            errors.append('Email already registered.')

        if len(password) < 6:
            errors.append('Password must be at least 6 characters.')

        if password != confirm_password:
            errors.append('Passwords do not match.')

        if errors:
            for error in errors:
                flash(error, 'error')
        else:
            user = User(
                username=username,
                email=validated_email or email.lower(),
                display_name=display_name
            )
            user.set_password(password)

            db.session.add(user)
            db.session.commit()

            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))

    return render_template('register.html')

# ============================================================================
# Password Management Routes
# ============================================================================

@app.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Allow logged-in users to change their password."""
    if request.method == 'POST':
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not current_user.check_password(current_password):
            flash('Current password is incorrect.', 'error')
            return redirect(url_for('change_password'))

        if len(new_password) < 6:
            flash('New password must be at least 6 characters.', 'error')
            return redirect(url_for('change_password'))

        if new_password != confirm_password:
            flash('New passwords do not match.', 'error')
            return redirect(url_for('change_password'))

        if current_password == new_password:
            flash('New password must be different from current password.', 'error')
            return redirect(url_for('change_password'))

        current_user.set_password(new_password)
        db.session.commit()

        flash('Password changed successfully!', 'success')
        return redirect(url_for('index'))

    return render_template('change_password.html')


@app.route('/admin/reset-password/<int:user_id>', methods=['POST'])
@admin_required
def admin_reset_password(user_id):
    """Admin can reset a user's password."""
    user = User.query.get_or_404(user_id)
    new_password = request.form.get('new_password', '').strip()

    if not new_password:
        flash('No password provided.', 'error')
        return redirect(url_for('admin_users'))

    if len(new_password) < 6:
        flash('Password must be at least 6 characters.', 'error')
        return redirect(url_for('admin_users'))

    user.set_password(new_password)
    db.session.commit()

    flash(f'Password successfully reset for {user.get_display_name()}.', 'success')
    return redirect(url_for('admin_users'))



# ============================================================================
# Pick Routes
# ============================================================================

@app.route('/my-picks')
@login_required
def my_picks():
    """View user's picks for the season."""
    tournaments = Tournament.query.filter_by(
        season_year=app.config['SEASON_YEAR']
    ).order_by(Tournament.start_date).all()

    # Get user's picks
    user_picks = {pick.tournament_id: pick for pick in current_user.picks}

    # Get used player IDs
    used_player_ids = current_user.get_used_player_ids()

    # Batch load all results for this user's picks
    all_player_ids = set()
    all_tournament_ids = set()
    for pick in user_picks.values():
        all_player_ids.update([pick.primary_player_id, pick.backup_player_id])
        all_tournament_ids.add(pick.tournament_id)

    results = TournamentResult.query.filter(
        TournamentResult.tournament_id.in_(all_tournament_ids),
        TournamentResult.player_id.in_(all_player_ids)
    ).all() if all_tournament_ids else []

    # Index by (tournament_id, player_id)
    result_lookup = {(r.tournament_id, r.player_id): r for r in results}

    pick_results = {}
    for tournament_id, pick in user_picks.items():
        pick_results[tournament_id] = {
            'primary_result': result_lookup.get((tournament_id, pick.primary_player_id)),
            'backup_result': result_lookup.get((tournament_id, pick.backup_player_id)),
        }

    return render_template('my_picks.html',
                         tournaments=tournaments,
                         user_picks=user_picks,
                         used_player_ids=used_player_ids,
                         pick_results=pick_results)


@app.route('/pick/<int:tournament_id>', methods=['GET', 'POST'])
@login_required
def make_pick(tournament_id):
    """Make or edit a pick for a tournament."""
    tournament = Tournament.query.get_or_404(tournament_id)

    if tournament.is_deadline_passed():
        flash('The deadline for this tournament has passed.', 'error')
        return redirect(url_for('my_picks'))

    existing_pick = Pick.query.filter_by(
        user_id=current_user.id,
        tournament_id=tournament_id
    ).first()

    used_player_ids = current_user.get_used_player_ids()
    if existing_pick:
        if existing_pick.primary_player_id in used_player_ids:
            used_player_ids.remove(existing_pick.primary_player_id)
        if existing_pick.backup_player_id in used_player_ids:
            used_player_ids.remove(existing_pick.backup_player_id)

    query = Player.query.join(TournamentField).filter(
        TournamentField.tournament_id == tournament_id,
        Player.is_amateur == False
    )
    if used_player_ids:
        query = query.filter(~Player.id.in_(used_player_ids))
    available_players = query.order_by(Player.last_name).all()

    if request.method == 'POST':
        primary_id = request.form.get('primary_player_id', type=int)
        backup_id = request.form.get('backup_player_id', type=int)

        errors = []

        if not primary_id or not backup_id:
            errors.append('You must select both a primary and backup player.')

        if primary_id == backup_id:
            errors.append('Primary and backup must be different players.')

        available_ids = [p.id for p in available_players]
        if primary_id not in available_ids:
            errors.append('Primary player is not available.')
        if backup_id not in available_ids:
            errors.append('Backup player is not available.')

        if errors:
            for error in errors:
                flash(error, 'error')
        else:
            if existing_pick:
                existing_pick.primary_player_id = primary_id
                existing_pick.backup_player_id = backup_id
                existing_pick.updated_at = datetime.now(timezone.utc)
                validation_errors = existing_pick.validate_availability(app.config['SEASON_YEAR'])
                if validation_errors:
                    for error in validation_errors:
                        flash(error, 'error')
                    db.session.rollback()
                else:
                    flash('Pick updated successfully!', 'success')
                    db.session.commit()
                    return redirect(url_for('my_picks'))
            else:
                pick = Pick(
                    user_id=current_user.id,
                    tournament_id=tournament_id,
                    primary_player_id=primary_id,
                    backup_player_id=backup_id
                )
                validation_errors = pick.validate_availability(app.config['SEASON_YEAR'])
                if validation_errors:
                    for error in validation_errors:
                        flash(error, 'error')
                    db.session.rollback()
                else:
                    db.session.add(pick)
                    db.session.commit()
                    flash('Pick submitted successfully!', 'success')
                    return redirect(url_for('my_picks'))

    return render_template('make_pick.html',
                         tournament=tournament,
                         available_players=available_players,
                         existing_pick=existing_pick)


# ============================================================================
# Admin Routes
# ============================================================================

@app.route('/admin')
@admin_required
def admin_dashboard():
    """Admin dashboard."""
    tournaments = Tournament.query.filter_by(
        season_year=app.config['SEASON_YEAR']
    ).order_by(Tournament.start_date).all()

    total_users = User.query.count()
    paid_users = User.query.filter_by(has_paid=True).count()

    pending_finalization = Tournament.query.filter(
        Tournament.season_year == app.config['SEASON_YEAR'],
        Tournament.status == 'complete',
        Tournament.results_finalized == False
    ).order_by(Tournament.end_date.desc()).all()

    api_usage = parse_api_usage_logs()

    return render_template('admin/dashboard.html',
                         tournaments=tournaments,
                         total_users=total_users,
                         paid_users=paid_users,
                         entry_fee=app.config['ENTRY_FEE'],
                         pending_finalization=pending_finalization,
                         api_usage=api_usage)


@app.route('/admin/tournaments')
@admin_required
def admin_tournaments():
    """Manage tournaments."""
    tournaments = Tournament.query.filter_by(
        season_year=app.config['SEASON_YEAR']
    ).order_by(Tournament.start_date).all()

    return render_template('admin/tournaments.html', tournaments=tournaments)


@app.route('/admin/users')
@admin_required
def admin_users():
    """Manage users."""
    users = User.query.order_by(func.lower(User.username)).all()
    return render_template('admin/users.html', users=users)


@app.route('/admin/payments')
@admin_required
def admin_payments():
    """Track payments."""
    users = User.query.order_by(func.lower(User.username)).all()

    paid_count = sum(1 for u in users if u.has_paid)
    unpaid_count = len(users) - paid_count
    total_collected = paid_count * app.config['ENTRY_FEE']

    return render_template('admin/payments.html',
                         users=users,
                         paid_count=paid_count,
                         unpaid_count=unpaid_count,
                         total_collected=total_collected,
                         entry_fee=app.config['ENTRY_FEE'])


@app.route('/admin/update-payment/<int:user_id>', methods=['POST'])
@admin_required
def admin_update_payment(user_id):
    """Toggle user payment status (AJAX)."""
    user = User.query.get_or_404(user_id)
    data = request.get_json()

    user.has_paid = data.get('has_paid', False)
    db.session.commit()

    return jsonify({'success': True, 'has_paid': user.has_paid})


# ============================================================================
# Admin Override Pick Route
# ============================================================================

@app.route('/admin/override-pick', methods=['GET', 'POST'])
@admin_required
def admin_override_pick():
    """Admin can create or modify picks after deadline has passed."""

    tournaments = Tournament.query.filter_by(
        season_year=app.config['SEASON_YEAR']
    ).order_by(Tournament.start_date.desc()).all()

    users = User.query.order_by(func.lower(User.username)).all()

    users_with_picks = set()

    selected_tournament = None
    selected_user = None
    field_players = None
    existing_pick = None
    used_player_ids = []

    recent_overrides = Pick.query.filter_by(admin_override=True).order_by(Pick.updated_at.desc()).limit(5).all()

    if request.method == 'POST':
        tournament_id = request.form.get('tournament_id', type=int)
        user_id = request.form.get('user_id', type=int)
        primary_id = request.form.get('primary_player_id', type=int)
        backup_id = request.form.get('backup_player_id', type=int)
        override_note = request.form.get('override_note', '').strip()[:200]
        load_field = request.form.get('load_field')

        if tournament_id:
            selected_tournament = Tournament.query.get(tournament_id)
            picks_for_tournament = Pick.query.filter_by(tournament_id=tournament_id).all()
            users_with_picks = {p.user_id for p in picks_for_tournament}

        if user_id:
            selected_user = User.query.get(user_id)
            if selected_user:
                used_player_ids = selected_user.get_used_player_ids()

        if selected_tournament and selected_user:
            field_players = Player.query.join(TournamentField).filter(
                TournamentField.tournament_id==selected_tournament.id,
                Player.is_amateur == False
            ).order_by(Player.last_name).all()

            existing_pick = Pick.query.filter_by(
                user_id=selected_user.id,
                tournament_id=selected_tournament.id
            ).first()

            if existing_pick:
                if existing_pick.primary_player_id in used_player_ids:
                    used_player_ids.remove(existing_pick.primary_player_id)
                if existing_pick.backup_player_id in used_player_ids:
                    used_player_ids.remove(existing_pick.backup_player_id)

        if primary_id and backup_id and not load_field:
            errors = []

            if primary_id == backup_id:
                errors.append('Primary and backup must be different players.')

            field_ids = [p.id for p in field_players] if field_players else []
            if primary_id not in field_ids:
                errors.append('Primary player is not in the tournament field.')
            if backup_id not in field_ids:
                errors.append('Backup player is not in the tournament field.')

            if primary_id in used_player_ids:
                errors.append('Primary player has already been used by this user this season.')
            if backup_id in used_player_ids:
                errors.append('Backup player has already been used by this user this season.')

            if errors:
                for error in errors:
                    flash(error, 'error')
            else:
                if existing_pick:
                    existing_pick.primary_player_id = primary_id
                    existing_pick.backup_player_id = backup_id
                    existing_pick.admin_override = True
                    existing_pick.admin_override_note = override_note or None
                    existing_pick.updated_at = datetime.now(timezone.utc)
                    flash(f'Override pick updated for {selected_user.get_display_name()}!', 'success')
                else:
                    new_pick = Pick(
                        user_id=selected_user.id,
                        tournament_id=selected_tournament.id,
                        primary_player_id=primary_id,
                        backup_player_id=backup_id,
                        admin_override=True,
                        admin_override_note=override_note or None
                    )
                    db.session.add(new_pick)
                    flash(f'Override pick created for {selected_user.get_display_name()}!', 'success')

                db.session.commit()

                recent_overrides = Pick.query.filter_by(admin_override=True).order_by(Pick.updated_at.desc()).limit(5).all()

                selected_tournament = None
                selected_user = None
                field_players = None
                existing_pick = None
                used_player_ids = []

    return render_template('admin/override_pick.html',
                         tournaments=tournaments,
                         users=users,
                         users_with_picks=users_with_picks,
                         selected_tournament=selected_tournament,
                         selected_user=selected_user,
                         field_players=field_players,
                         existing_pick=existing_pick,
                         used_player_ids=used_player_ids,
                         recent_overrides=recent_overrides)


def process_tournament_results(tournament: Tournament):
    """Idempotent processing of results and seasonal usage tracking."""
    picks = Pick.query.filter_by(tournament_id=tournament.id).all()

    processed = 0
    skipped = []

    for pick in picks:
        try:
            with db.session.begin_nested():
                SeasonPlayerUsage.query.filter(
                    SeasonPlayerUsage.user_id == pick.user_id,
                    SeasonPlayerUsage.season_year == tournament.season_year,
                    SeasonPlayerUsage.player_id.in_([pick.primary_player_id, pick.backup_player_id])
                ).delete(synchronize_session=False)

                resolved = pick.resolve_pick()
                if not resolved:
                    skipped.append(pick.id)
                    raise RuntimeError("Pick resolution incomplete")

                pick.user.calculate_total_points()
            processed += 1
        except Exception as exc:
            logger.warning(
                "Skipped pick %s for tournament %s: %s",
                pick.id,
                tournament.id,
                exc,
            )

    db.session.commit()
    return processed, skipped

# ============================================================================
# API Usage Monitoring
# ============================================================================

def parse_api_usage_logs(month=None, year=None):
    """
    Parse API call logs to track usage.
    """
    from collections import defaultdict

    now = datetime.now(LEAGUE_TZ)
    target_month = month or now.month
    target_year = year or now.year

    log_path = os.path.join(os.path.dirname(__file__), 'logs', 'api_calls.log')

    if not os.path.exists(log_path):
        return {
            'total_calls': 0,
            'by_endpoint': {},
            'by_mode': {},
            'last_call': None,
            'month': target_month,
            'year': target_year
        }

    total_calls = 0
    by_endpoint = defaultdict(int)
    by_mode = defaultdict(int)
    last_call = None

    try:
        with open(log_path, 'r') as f:
            for line in f:
                try:
                    parts = line.strip().split('\t')
                    if len(parts) < 2:
                        continue

                    timestamp_str = parts[0]
                    if ',' in timestamp_str:
                        timestamp_str = timestamp_str.split(',')[0]
                    log_time = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')

                    if log_time.month != target_month or log_time.year != target_year:
                        continue

                    details = {}
                    for part in parts[1:]:
                        if '=' in part:
                            key, value = part.split('=', 1)
                            details[key] = value

                    if details.get('status') == '200':
                        total_calls += 1
                        endpoint = details.get('endpoint', 'unknown')
                        mode = details.get('mode', 'unknown')

                        by_endpoint[endpoint] += 1
                        by_mode[mode] += 1

                        if last_call is None or log_time > last_call:
                            last_call = log_time

                except Exception as e:
                    continue

    except Exception as e:
        logger.error(f"Error parsing API logs: {e}")

    return {
        'total_calls': total_calls,
        'by_endpoint': dict(by_endpoint),
        'by_mode': dict(by_mode),
        'last_call': last_call,
        'month': target_month,
        'year': target_year,
        'limit': 250,
        'percentage': round((total_calls / 250) * 100, 1)
    }


@app.route('/admin/process-results/<int:tournament_id>', methods=['POST'])
@admin_required
def admin_process_results(tournament_id):
    """Process tournament results and calculate points."""
    tournament = Tournament.query.get_or_404(tournament_id)

    if tournament.status != 'complete':
        flash('Tournament must be complete before processing results.', 'error')
        return redirect(url_for('admin_tournaments'))

    processed, skipped = process_tournament_results(tournament)

    message = f'Processed results for {processed} picks.'
    if skipped:
        message += f" Skipped {len(skipped)} pick(s) awaiting missing results."
    flash(message, 'success' if not skipped else 'warning')
    return redirect(url_for('admin_tournaments'))


# ============================================================================
# Error Handlers
# ============================================================================

@app.errorhandler(404)
def not_found(e):
    return render_template('errors/404.html'), 404


@app.errorhandler(500)
def server_error(e):
    return render_template('errors/500.html'), 500


# ============================================================================
# CLI Commands
# ============================================================================

@app.cli.command('init-db')
def init_db():
    """Initialize the database."""
    db.create_all()
    print('Database initialized.')


@app.cli.command('create-admin')
def create_admin():
    """Create an admin user."""
    import getpass

    username = input('Admin username: ').strip()
    email = input('Admin email: ').strip()
    password = getpass.getpass('Admin password: ')

    if User.query.filter(func.lower(User.username) == username.lower()).first():
        print(f'User {username} already exists.')
        return

    user = User(
        username=username,
        email=email,
        is_admin=True
    )
    user.set_password(password)

    db.session.add(user)
    db.session.commit()

    print(f'Admin user {username} created.')


@app.cli.command('process-results')
def process_results_cli():
    """Process results for all completed tournaments in the current season."""
    tournaments = Tournament.query.filter_by(status='complete', season_year=app.config['SEASON_YEAR']).all()
    total_processed = 0
    total_skipped = 0
    for tournament in tournaments:
        processed, skipped = process_tournament_results(tournament)
        total_processed += processed
        total_skipped += len(skipped)
    print(f'Processed {total_processed} picks across {len(tournaments)} tournaments. Skipped {total_skipped}.')


# Register API sync commands
from sync_api import register_sync_commands
register_sync_commands(app)


# ============================================================================
# Run Application
# ============================================================================

if __name__ == '__main__':
    app.run(debug=True)
