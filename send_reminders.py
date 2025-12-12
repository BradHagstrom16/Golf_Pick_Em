"""
Golf Pick 'Em - Tournament Reminder Script
==========================================

Sends email reminders to users who haven't made their picks.

Reminder Schedule:
  • 48 hours before deadline
  • 24 hours before deadline  
  • 1 hour before deadline (FINAL)

Setup:
  1. Create email_config.py from email_config_template.py
  2. Schedule this script to run hourly on PythonAnywhere
     Recommended: Every hour at :00 (e.g., 8:00, 9:00, 10:00...)

PythonAnywhere Scheduled Task:
  cd /home/YOUR_USERNAME/Golf_Pick_Em && python send_reminders.py
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
from models import db, User, Tournament, Pick

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

# Reminder windows (hours before deadline)
REMINDER_WINDOWS = [
    {'hours': 48, 'type': 'early', 'emoji': '📅'},
    {'hours': 24, 'type': 'warning', 'emoji': '⚠️'},
    {'hours': 1, 'type': 'final', 'emoji': '🚨'},
]

# Tolerance window (minutes) - send reminder if within this window of the target time
TOLERANCE_MINUTES = 30


def get_current_time():
    """Get current time in Central timezone."""
    return datetime.now(CENTRAL_TZ)


def get_upcoming_tournament():
    """
    Find the next tournament that:
    - Has status 'upcoming'
    - Has a deadline in the future
    - Has a deadline within the next 48 hours (for reminders)
    """
    with app.app_context():
        now = get_current_time()
        max_future = now + timedelta(hours=48, minutes=TOLERANCE_MINUTES)
        
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
    """Build the email subject and body for a reminder."""
    time_remaining = format_time_remaining(deadline)
    pick_url = f"{SITE_URL}/pick/{tournament.id}"
    
    # Subject line based on urgency
    if window['type'] == 'final':
        subject = f"🚨 FINAL REMINDER: {tournament.name} pick due in ~1 hour!"
    elif window['type'] == 'warning':
        subject = f"⚠️ Reminder: {tournament.name} pick due in ~24 hours"
    else:
        subject = f"📅 Reminder: {tournament.name} pick deadline approaching"
    
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
    elif window['type'] == 'warning':
        body += """You have about 24 hours left. You'll receive one more reminder 
1 hour before the deadline.

"""
    else:
        body += """You'll receive additional reminders at 24 hours and 1 hour 
before the deadline.

"""
    
    body += f"""Good luck!
{COMMISSIONER_NAME}

---
Golf Pick 'Em {tournament.season_year}
{SITE_URL}
"""
    
    return subject, body


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
            print("\n📭 No upcoming tournaments within reminder window")
            return
        
        deadline = tournament._aware_deadline
        print(f"\n🏌️ Tournament: {tournament.name}")
        print(f"📅 Deadline: {deadline.strftime('%A, %B %d at %I:%M %p %Z')}")
        print(f"⏱️ Time remaining: {format_time_remaining(deadline)}")
        
        # Check which reminder window is active
        window = get_active_reminder_window(deadline)
        
        if not window:
            print(f"\n⏳ Not within any reminder window")
            print(f"   Next windows: 48h, 24h, 1h before deadline")
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
