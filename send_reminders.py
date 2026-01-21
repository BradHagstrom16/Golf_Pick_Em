"""
Golf Pick 'Em - Tournament Reminder & Notification Script
==========================================================

Handles two types of emails:
1. "Picks Are Open" - Sent when field is synced (called from sync_api.py)
2. Deadline Reminders - Sent at 24h, 12h, 1h before deadline

Reminder Schedule:
  • 24 hours before deadline
  • 12 hours before deadline
  • 1 hour before deadline (FINAL)

IMPORTANT: Reminders are ONLY sent if the field is synced (≥50 players).
           If field is not ready, no reminders go out.

Setup:
  1. Create email_config.py from email_config_template.py
  2. Schedule this script to run hourly on PythonAnywhere
     Recommended: Every hour at :00 (e.g., 8:00, 9:00, 10:00...)

PythonAnywhere Scheduled Task:
  cd /home/GolfPickEm/Golf_Pick_Em && ./run_reminders.sh
"""

import os
import sys
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import pytz

# Add project path for PythonAnywhere
PROJECT_HOME = '/home/GolfPickEm/Golf_Pick_Em'
if PROJECT_HOME not in sys.path:
    sys.path.insert(0, PROJECT_HOME)

# Set environment
os.environ.setdefault('FLASK_ENV', 'production')

from app import app
from models import db, User, Tournament, TournamentField, Pick

# Import email configuration
try:
    from email_config import (
        EMAIL_ADDRESS, 
        EMAIL_PASSWORD, 
        SMTP_SERVER, 
        SMTP_PORT, 
        SITE_URL,
        COMMISSIONER_NAME
    )
    CONFIG_LOADED = True
except ImportError:
    print("=" * 60)
    print("ERROR: email_config.py not found!")
    print("Copy email_config_template.py to email_config.py and configure it.")
    print("=" * 60)
    CONFIG_LOADED = False
    EMAIL_ADDRESS = ""
    EMAIL_PASSWORD = ""
    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587
    SITE_URL = "https://golfpickem.pythonanywhere.com"
    COMMISSIONER_NAME = "The Commissioner"

# Timezone
CENTRAL_TZ = pytz.timezone("America/Chicago")

# Minimum field size required for notifications
MIN_FIELD_SIZE = 50

# Admin contact for alerts
ADMIN_EMAIL = "bhagstrom0@gmail.com"
ADMIN_NAME = "Sun Day Regrets"

# Reminder windows (hours before deadline)
# Updated: 24h, 12h, 1h (removed 48h, added 12h)
REMINDER_WINDOWS = [
    {'hours': 24, 'type': 'warning', 'emoji': '⚠️'},
    {'hours': 12, 'type': 'reminder', 'emoji': '⏰'},
    {'hours': 1, 'type': 'final', 'emoji': '🚨'},
]

# Tolerance window (minutes) - send reminder if within this window of the target time
TOLERANCE_MINUTES = 30


def get_current_time():
    """Get current time in Central timezone."""
    return datetime.now(CENTRAL_TZ)


def get_field_count(tournament_id):
    """Get the number of players in a tournament's field."""
    return TournamentField.query.filter_by(tournament_id=tournament_id).count()


def is_field_ready(tournament_id, minimum=MIN_FIELD_SIZE):
    """Check if tournament field has enough players for picks to be open."""
    return get_field_count(tournament_id) >= minimum


def get_upcoming_tournament():
    """
    Find the next tournament that:
    - Has status 'upcoming'
    - Has a deadline in the future
    - Has a deadline within the next 24 hours (for reminders)
    - Has a synced field (≥50 players)
    """
    with app.app_context():
        now = get_current_time()
        max_future = now + timedelta(hours=24, minutes=TOLERANCE_MINUTES)
        
        tournament = Tournament.query.filter(
            Tournament.status == 'upcoming',
            Tournament.pick_deadline.isnot(None)
        ).order_by(Tournament.start_date).first()
        
        if not tournament:
            return None
        
        # Make deadline timezone-aware if needed
        deadline = tournament.pick_deadline
        if deadline.tzinfo is None:
            deadline = CENTRAL_TZ.localize(deadline)
        
        # Check if deadline is in the future and within our reminder window
        if deadline <= now:
            return None  # Deadline already passed
        
        if deadline > max_future:
            return None  # Too far in the future for reminders
        
        # Check if field is ready
        if not is_field_ready(tournament.id):
            print(f"⚠️ Field not ready for {tournament.name} ({get_field_count(tournament.id)} players)")
            print(f"   Reminders will not be sent until field has ≥{MIN_FIELD_SIZE} players")
            return None
        
        # Attach the aware deadline
        tournament._aware_deadline = deadline
        return tournament


def get_users_without_picks(tournament):
    """Get users who haven't made a pick for this tournament."""
    with app.app_context():
        all_users = User.query.all()
        picked_user_ids = {
            p.user_id for p in Pick.query.filter_by(tournament_id=tournament.id)
        }
        return [u for u in all_users if u.id not in picked_user_ids]


def get_all_users():
    """Get all registered users."""
    with app.app_context():
        return User.query.all()


def should_send_reminder(deadline, window_hours):
    """
    Check if we should send a reminder for this window.
    Returns True if current time is within TOLERANCE_MINUTES of the window.
    """
    now = get_current_time()
    target_time = deadline - timedelta(hours=window_hours)
    
    # Check if we're within the tolerance window
    window_start = target_time - timedelta(minutes=TOLERANCE_MINUTES)
    window_end = target_time + timedelta(minutes=TOLERANCE_MINUTES)
    
    return window_start <= now <= window_end


def get_active_reminder_window(deadline):
    """
    Determine which reminder window (if any) is currently active.
    Returns the window dict or None.
    """
    now = get_current_time()
    
    # Also check if deadline hasn't passed
    if deadline <= now:
        return None
    
    for window in REMINDER_WINDOWS:
        if should_send_reminder(deadline, window['hours']):
            return window
    
    return None


def format_time_remaining(deadline):
    """Format the time remaining until deadline."""
    now = get_current_time()
    delta = deadline - now
    
    total_hours = int(delta.total_seconds() // 3600)
    minutes = int((delta.total_seconds() % 3600) // 60)
    
    if total_hours >= 24:
        days = total_hours // 24
        hours = total_hours % 24
        return f"{days} day{'s' if days != 1 else ''}, {hours} hour{'s' if hours != 1 else ''}"
    elif total_hours >= 1:
        return f"{total_hours} hour{'s' if total_hours != 1 else ''}, {minutes} minute{'s' if minutes != 1 else ''}"
    else:
        return f"{minutes} minute{'s' if minutes != 1 else ''}"


def send_email(to_addr: str, subject: str, body: str) -> bool:
    """Send a plain-text email."""
    if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
        print(f"  ❌ Cannot send to {to_addr}: Email credentials not configured")
        return False
    
    msg = MIMEMultipart()
    msg["From"] = f"{COMMISSIONER_NAME} <{EMAIL_ADDRESS}>"
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))
    
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg)
        print(f"  ✅ Email sent to {to_addr}")
        return True
    except Exception as e:
        print(f"  ❌ Failed to send to {to_addr}: {e}")
        return False


def build_reminder_email(user, tournament, deadline, window):
    """Build the email subject and body for a deadline reminder."""
    time_remaining = format_time_remaining(deadline)
    pick_url = f"{SITE_URL}/pick/{tournament.id}"
    
    # Subject line based on urgency
    if window['type'] == 'final':
        subject = f"🚨 FINAL REMINDER: {tournament.name} pick due in ~1 hour!"
    elif window['type'] == 'reminder':
        subject = f"⏰ Reminder: {tournament.name} pick due in ~12 hours"
    else:
        subject = f"⚠️ Reminder: {tournament.name} pick due in ~24 hours"
    
    # Email body
    body = f"""Hi {user.get_display_name()},

You haven't made your pick for {tournament.name} yet!

Tournament: {tournament.name}
Purse: ${tournament.purse:,}
Deadline: {deadline.strftime('%A, %B %d at %I:%M %p %Z')}
Time Remaining: {time_remaining}

Make your pick now: {pick_url}

Your Season Stats:
• Total Points: ${user.total_points:,}
• Golfers Used: {len(user.get_used_player_ids())}

"""
    
    # Add urgency message based on window type
    if window['type'] == 'final':
        body += """⚠️ THIS IS YOUR FINAL REMINDER!
The deadline is less than 1 hour away. Make your pick NOW to avoid missing out!

"""
    elif window['type'] == 'reminder':
        body += """You have about 12 hours left. You'll receive one more reminder 
1 hour before the deadline.

"""
    else:
        body += """You have about 24 hours left. You'll receive additional reminders 
at 12 hours and 1 hour before the deadline.

"""
    
    body += f"""Good luck!
{COMMISSIONER_NAME}

---
Golf Pick 'Em {tournament.season_year}
{SITE_URL}
"""
    
    return subject, body


# =============================================================================
# PICKS OPEN NOTIFICATION (Called from sync_api.py after field sync)
# =============================================================================

def send_picks_open_email(tournament) -> int:
    """
    Send "Picks Are Open" notification to all users.
    Called from sync_api.py after successful field sync.
    
    Args:
        tournament: Tournament object with field synced
    
    Returns:
        Number of emails successfully sent
    """
    print(f"\n📬 Sending 'Picks Are Open' notifications for {tournament.name}")
    
    if not CONFIG_LOADED:
        print("  ❌ Cannot send: Email configuration not loaded")
        return 0
    
    # Get deadline for display
    deadline = tournament.pick_deadline
    if deadline and deadline.tzinfo is None:
        deadline = CENTRAL_TZ.localize(deadline)
    
    deadline_str = deadline.strftime('%A, %B %d at %I:%M %p CT') if deadline else "TBD"
    
    # Get field count
    field_count = get_field_count(tournament.id)
    
    # Build email
    pick_url = f"{SITE_URL}/pick/{tournament.id}"
    
    subject = f"🏌️ Picks Are Open: {tournament.name}"
    
    body_template = """Hi {display_name},

Great news! The field for {tournament_name} is now available, and picks are open!

🏆 Tournament: {tournament_name}
💰 Purse: ${purse:,}
👥 Field Size: {field_count} players
⏰ Pick Deadline: {deadline}

Make your pick now: {pick_url}

Remember:
• Pick a primary golfer and a backup
• Each golfer can only be used once this season
• Points = actual prize money earned

Your Season Stats:
• Total Points: ${total_points:,}
• Golfers Used: {golfers_used}

Good luck this week!
{commissioner}

---
Golf Pick 'Em {season_year}
{site_url}
"""
    
    # Send to all users
    with app.app_context():
        users = get_all_users()
        success_count = 0
        
        for user in users:
            body = body_template.format(
                display_name=user.get_display_name(),
                tournament_name=tournament.name,
                purse=tournament.purse,
                field_count=field_count,
                deadline=deadline_str,
                pick_url=pick_url,
                total_points=user.total_points,
                golfers_used=len(user.get_used_player_ids()),
                commissioner=COMMISSIONER_NAME,
                season_year=tournament.season_year,
                site_url=SITE_URL
            )
            
            if send_email(user.email, subject, body):
                success_count += 1
        
        print(f"\n📊 Picks Open Summary: {success_count}/{len(users)} emails sent")
        return success_count


# =============================================================================
# ADMIN ALERT (Called from sync_api.py on Wednesday if field not ready)
# =============================================================================

def send_admin_field_alert(tournament, field_count: int) -> bool:
    """
    Send alert to admin when field sync fails on Wednesday.
    
    Args:
        tournament: Tournament object
        field_count: Current number of players in field
    
    Returns:
        True if email sent successfully
    """
    print(f"\n🚨 Sending admin alert for {tournament.name}")
    
    if not CONFIG_LOADED:
        print("  ❌ Cannot send: Email configuration not loaded")
        return False
    
    # Get deadline for display
    deadline = tournament.pick_deadline
    if deadline and deadline.tzinfo is None:
        deadline = CENTRAL_TZ.localize(deadline)
    
    deadline_str = deadline.strftime('%A, %B %d at %I:%M %p CT') if deadline else "TBD"
    
    subject = f"⚠️ ADMIN ALERT: Field sync issue for {tournament.name}"
    
    body = f"""Hi {ADMIN_NAME},

This is an automated alert from Golf Pick 'Em.

⚠️ FIELD SYNC ISSUE DETECTED

Tournament: {tournament.name}
Current Field Size: {field_count} players (minimum required: {MIN_FIELD_SIZE})
Pick Deadline: {deadline_str}
Tournament Start: {tournament.start_date.strftime('%A, %B %d')}

What this means:
• The Wednesday field confirmation pass did not find enough players
• Users will NOT receive "Picks Are Open" emails
• Deadline reminder emails will NOT be sent
• Users cannot make picks without a synced field

Recommended Actions:
1. Check if the API has field data available
2. Try running a manual field sync: ./run_sync.sh field
3. Check SlashGolf API status for any outages
4. If the tournament is cancelled/postponed, update the database

Admin Dashboard: {SITE_URL}/admin

This alert will only be sent once per tournament.

---
Golf Pick 'Em Automated Alert System
"""
    
    return send_email(ADMIN_EMAIL, subject, body)


# =============================================================================
# MAIN REMINDER CHECK (Runs hourly via scheduled task)
# =============================================================================

def main():
    """Main reminder processing function."""
    now = get_current_time()
    
    print()
    print("=" * 60)
    print(f"Golf Pick 'Em Reminder Check")
    print(f"Time: {now.strftime('%A, %B %d, %Y at %I:%M %p %Z')}")
    print("=" * 60)
    
    if not CONFIG_LOADED:
        print("\n❌ Cannot proceed without email configuration")
        return
    
    # Find upcoming tournament needing reminders
    with app.app_context():
        tournament = get_upcoming_tournament()
        
        if not tournament:
            print("\n📭 No upcoming tournaments within reminder window (or field not ready)")
            return
        
        deadline = tournament._aware_deadline
        print(f"\n🏌️ Tournament: {tournament.name}")
        print(f"📅 Deadline: {deadline.strftime('%A, %B %d at %I:%M %p %Z')}")
        print(f"⏱️ Time remaining: {format_time_remaining(deadline)}")
        print(f"👥 Field size: {get_field_count(tournament.id)} players")
        
        # Check which reminder window is active
        window = get_active_reminder_window(deadline)
        
        if not window:
            print(f"\n⏳ Not within any reminder window")
            print(f"   Next windows: 24h, 12h, 1h before deadline")
            return
        
        print(f"\n📬 Active reminder window: {window['hours']}-hour ({window['type']})")
        
        # Get users who need reminders
        users_without_picks = get_users_without_picks(tournament)
        
        if not users_without_picks:
            print(f"\n✅ All users have made their picks for {tournament.name}!")
            return
        
        print(f"\n👥 Users without picks: {len(users_without_picks)}")
        
        # Send reminders
        success_count = 0
        for user in users_without_picks:
            subject, body = build_reminder_email(user, tournament, deadline, window)
            if send_email(user.email, subject, body):
                success_count += 1
        
        print()
        print("-" * 60)
        print(f"📊 Summary: {success_count}/{len(users_without_picks)} reminders sent")
        print("=" * 60)


if __name__ == "__main__":
    main()
