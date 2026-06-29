"""
Golf Pick 'Em - Tournament Reminder & Notification Script
==========================================================

Handles three types of emails:
1. "Picks Are Open" - Sent when field is synced (called from sync_api.py)
2. Deadline Reminders - Sent at 24h, 12h, 1h before deadline
3. Results Recap - Sent once per tournament after earnings finalized

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
from contextlib import contextmanager
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from html import escape as _esc  # escape dynamic text before it enters email markup
import pytz

# Add project path for PythonAnywhere
PROJECT_HOME = '/home/GolfPickEm/Golf_Pick_Em'
if PROJECT_HOME not in sys.path:
    sys.path.insert(0, PROJECT_HOME)

# Set environment
os.environ.setdefault('FLASK_ENV', 'production')

from flask import has_app_context
from app import app
from models import db, User, Tournament, TournamentField, TournamentResult, Pick, format_score_to_par


@contextmanager
def _app_context():
    """Push app context only if not already in one (avoids nested session issues)."""
    if has_app_context():
        yield
    else:
        with app.app_context():
            yield

# Import email configuration
try:
    from email_config import (  # type: ignore[reportMissingImports]  # gitignored local config; absence is expected and handled below
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
REMINDER_WINDOWS = [
    {'hours': 24, 'type': 'warning'},
    {'hours': 12, 'type': 'reminder'},
    {'hours': 1, 'type': 'final'},
]

# Tolerance window (minutes) - send reminder if within this window of the target time
TOLERANCE_MINUTES = 35

# ============================================================================
# Inline style constants — Gmail-safe, no <style> blocks
# ============================================================================
_FONT_DISPLAY = "Georgia, 'Times New Roman', serif"
_FONT_BODY = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif"

_GREEN_900 = "#00432e"
_GREEN_800 = "#005c3f"
_GREEN_700 = "#006747"
_GREEN_100 = "#e8f5ef"
_GREEN_50 = "#f0faf5"
_GOLD_700 = "#92722a"  # gold-deep — AA-safe gold text on light fills
_GOLD_500 = "#b8993e"
_GOLD_300 = "#d4be6a"
_GOLD_100 = "#faf3e0"
_CREAM = "#faf8f4"
_WHITE = "#ffffff"
_TEXT_PRIMARY = "#1a1f25"
_TEXT_SECONDARY = "#4a5568"
_TEXT_MUTED = "#8b95a2"
_TEXT_ON_DARK = "#f7f8f9"
_DANGER = "#b91c1c"
_WARNING = "#d97706"

# Hairline border — full borders + tints replace side-stripes (DESIGN.md)
_BORDER = "rgba(0, 67, 46, 0.12)"


# ============================================================================
# HTML Email Infrastructure
# ============================================================================

def _html_wrapper(content_html, season_year=2026):
    """Wrap email content in the standard Greenside Ledger HTML shell."""
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Golf Pick 'Em</title>
<!--[if mso]><xml><o:OfficeDocumentSettings><o:PixelsPerInch>96</o:PixelsPerInch></o:OfficeDocumentSettings></xml><![endif]-->
</head>
<body style="margin: 0; padding: 0; background-color: {_CREAM}; font-family: {_FONT_BODY}; -webkit-font-smoothing: antialiased;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: {_CREAM};">
<tr><td align="center" style="padding: 24px 16px;">

<table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="max-width: 600px; width: 100%; background-color: {_WHITE};">

<!-- HEADER -->
<tr><td style="background-color: {_GREEN_800}; padding: 22px 32px; text-align: center;">
<span style="font-family: {_FONT_DISPLAY}; font-size: 22px; font-weight: 700; color: {_TEXT_ON_DARK}; letter-spacing: 0.01em;">&#9971; Golf Pick &#8217;Em</span>
</td></tr>

<!-- GOLD ACCENT BAR -->
<tr><td style="background-color: {_GOLD_500}; height: 3px; font-size: 0; line-height: 0;">&nbsp;</td></tr>

<!-- CONTENT -->
<tr><td style="padding: 32px 32px 24px 32px;">
{content_html}
</td></tr>

<!-- FOOTER -->
<tr><td style="background-color: {_GREEN_900}; padding: 20px 32px; text-align: center;">
<p style="margin: 0; font-size: 13px; color: rgba(247,248,249,0.6); font-family: {_FONT_BODY};">
Golf Pick &#8217;Em {season_year} &middot; <a href="{SITE_URL}" style="color: {_GOLD_300}; text-decoration: none;">golfpickem.pythonanywhere.com</a>
</p>
</td></tr>

</table>

</td></tr>
</table>
</body>
</html>'''


def _html_button(url, label, bg_color=None):
    """Render a CTA button as a styled <a> tag (Gmail-safe)."""
    bg = bg_color or _GREEN_700
    return f'''<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
<tr><td align="center" style="padding: 8px 0 16px 0;">
<a href="{url}" style="display: inline-block; background-color: {bg}; color: {_TEXT_ON_DARK}; font-family: {_FONT_BODY}; font-size: 16px; font-weight: 600; text-decoration: none; padding: 14px 36px; border-radius: 6px;">{label} &rarr;</a>
</td></tr>
</table>'''


def _html_masthead(eyebrow, title, eyebrow_color=None,
                   hero_value=None, hero_label=None, hero_color=None):
    """Ceremonial email masthead: a single status eyebrow, the tournament name
    in the serif display register, and an optional display-scale hero figure —
    the one number that matters (countdown, earnings). When no hero is given,
    the tournament name itself becomes the hero and renders larger."""
    eb_color = eyebrow_color or _GREEN_700
    has_hero = hero_value is not None
    title_size = 24 if has_hero else 33
    title_mb = 12 if has_hero else 2

    # Escape all dynamic text — tournament names and member names are untrusted.
    title = _esc(title)
    eyebrow = _esc(eyebrow) if eyebrow else eyebrow
    hero_label = _esc(hero_label) if hero_label else hero_label
    hero_value = _esc(str(hero_value)) if has_hero else hero_value

    eyebrow_html = ""
    if eyebrow:
        eyebrow_html = (
            f'<p style="margin: 0 0 10px 0; font-family: {_FONT_BODY}; '
            f'font-size: 12px; font-weight: 700; color: {eb_color}; '
            f'text-transform: uppercase; letter-spacing: 0.1em;">{eyebrow}</p>'
        )

    hero_html = ""
    if has_hero:
        h_color = hero_color or _GREEN_700
        label_html = ""
        if hero_label:
            label_html = (
                f'<p style="margin: 0 0 2px 0; font-family: {_FONT_BODY}; '
                f'font-size: 11px; font-weight: 600; color: {_TEXT_SECONDARY}; '
                f'text-transform: uppercase; letter-spacing: 0.08em;">{hero_label}</p>'
            )
        hero_html = (
            f'{label_html}'
            f'<p style="margin: 0; font-family: {_FONT_DISPLAY}; '
            f'font-size: 46px; line-height: 1.04; font-weight: 700; '
            f'letter-spacing: -0.01em; color: {h_color};">{hero_value}</p>'
        )

    return f'''<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom: 24px;">
<tr><td style="padding: 0;">
{eyebrow_html}
<p style="margin: 0 0 {title_mb}px 0; font-family: {_FONT_DISPLAY}; font-size: {title_size}px; line-height: 1.12; font-weight: 700; letter-spacing: -0.01em; color: {_TEXT_PRIMARY};">{title}</p>
{hero_html}
</td></tr>
</table>'''


def _html_ledger_panel(cells, bg=None):
    """A bordered ledger panel: full hairline border (never a side-stripe),
    cells split by an internal hairline rule. cells = list of (label, value)."""
    bg = bg or _WHITE
    n = len(cells)
    width = f"{round(100 / n)}%" if n else "100%"
    tds = ""
    for i, (label, value) in enumerate(cells):
        label = _esc(str(label))
        value = _esc(str(value))
        divider = "" if i == n - 1 else f"border-right: 1px solid {_BORDER};"
        tds += (
            f'<td width="{width}" valign="top" style="padding: 16px 22px; {divider}">'
            f'<p style="margin: 0 0 4px 0; font-family: {_FONT_BODY}; font-size: 11px; '
            f'font-weight: 600; color: {_TEXT_SECONDARY}; text-transform: uppercase; '
            f'letter-spacing: 0.06em;">{label}</p>'
            f'<p style="margin: 0; font-family: {_FONT_BODY}; font-size: 18px; '
            f'font-weight: 700; color: {_TEXT_PRIMARY};">{value}</p>'
            f'</td>'
        )
    return f'''<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: {bg}; border: 1px solid {_BORDER}; border-radius: 10px; margin-bottom: 24px;">
<tr>{tds}</tr>
</table>'''


# ============================================================================
# Utility Functions
# ============================================================================

def get_current_time():
    """Get current time in Central timezone."""
    return datetime.now(CENTRAL_TZ)


def get_field_count(tournament_id):
    """Get the number of players in a tournament's field."""
    return TournamentField.query.filter_by(tournament_id=tournament_id).count()


def is_field_ready(tournament_id, minimum=MIN_FIELD_SIZE):
    """Check if tournament field has enough players for picks to be open."""
    return get_field_count(tournament_id) >= minimum


def get_upcoming_tournament_for_reminders():
    """
    Find the next tournament that:
    - Has a pick_deadline in the future
    - Has a deadline within the next 24 hours + tolerance (for reminders)
    - Has a synced field (≥50 players)
    - Is NOT already complete

    NOTE: We intentionally do NOT filter on status == 'upcoming' because
    the tournament can flip to 'active' (via start_date) before the
    pick deadline. Reminders should keep firing until the deadline passes.

    Returns:
        Tuple of (tournament, aware_deadline) or (None, None)
    """
    now = get_current_time()
    max_future = now + timedelta(hours=24, minutes=TOLERANCE_MINUTES)

    tournament = Tournament.query.filter(
        Tournament.status != 'complete',
        Tournament.pick_deadline.isnot(None)
    ).order_by(Tournament.pick_deadline).first()

    if not tournament:
        return None, None

    deadline = tournament.pick_deadline
    if deadline.tzinfo is None:
        deadline = CENTRAL_TZ.localize(deadline)

    if deadline <= now:
        return None, None

    if deadline > max_future:
        return None, None

    if not is_field_ready(tournament.id):
        print(f"⚠️ Field not ready for {tournament.name} ({get_field_count(tournament.id)} players)")
        print(f"   Reminders will not be sent until field has ≥{MIN_FIELD_SIZE} players")
        return None, None

    return tournament, deadline


def get_users_without_picks(tournament_id):
    """Get users who haven't made a pick for this tournament."""
    all_users = User.query.all()
    picked_user_ids = {
        p.user_id for p in Pick.query.filter_by(tournament_id=tournament_id)
    }
    return [u for u in all_users if u.id not in picked_user_ids]


def should_send_reminder(deadline, window_hours):
    """Check if we should send a reminder for this window."""
    now = get_current_time()
    target_time = deadline - timedelta(hours=window_hours)
    window_start = target_time - timedelta(minutes=TOLERANCE_MINUTES)
    window_end = target_time + timedelta(minutes=TOLERANCE_MINUTES)
    return window_start <= now <= window_end


def get_active_reminder_window(deadline):
    """Determine which reminder window (if any) is currently active."""
    now = get_current_time()
    if deadline <= now:
        return None
    for window in REMINDER_WINDOWS:
        if should_send_reminder(deadline, window['hours']):
            return window
    return None


def format_time_remaining(deadline):
    """Format time remaining with clean rounding."""
    now = get_current_time()
    delta = deadline - now
    total_hours = delta.total_seconds() / 3600

    if total_hours >= 36:
        days = round(total_hours / 24)
        return f"{days} days"
    elif total_hours >= 18:
        return "1 day"
    elif total_hours >= 1.5:
        hours = round(total_hours)
        return f"{hours} hours"
    elif total_hours >= 0.75:
        return "1 hour"
    else:
        minutes = max(1, round(total_hours * 60))
        return f"{minutes} minutes"


def get_time_remaining_display(window):
    """Return a clean, rounded time-remaining string based on the reminder window."""
    display_map = {
        'warning': '24 hours',
        'reminder': '12 hours',
        'final': '1 hour',
    }
    return display_map.get(window['type'], f"{window['hours']} hours")


# ============================================================================
# Email Sending
# ============================================================================

def send_email(to_addr: str, subject: str, body: str, html_body: str = None) -> bool:
    """Send an email with plain text and optional HTML body."""
    if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
        print(f"  ❌ Cannot send to {to_addr}: Email credentials not configured")
        return False

    msg = MIMEMultipart('alternative')
    msg["From"] = f"{COMMISSIONER_NAME} <{EMAIL_ADDRESS}>"
    msg["To"] = to_addr
    msg["Subject"] = subject

    # Plain text first (lowest priority in 'alternative')
    msg.attach(MIMEText(body, "plain"))

    # HTML second (highest priority — email clients prefer this)
    if html_body:
        msg.attach(MIMEText(html_body, "html"))

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


# =============================================================================
# PICKS OPEN NOTIFICATION (Called from sync_api.py after field sync)
# =============================================================================

def _build_picks_open_html(display_name, tournament_name, purse,
                           deadline_str, pick_url, season_year):
    """Build the HTML body for the 'Picks Are Open' email."""
    content = f'''{_html_masthead("The field is set", tournament_name)}
<p style="margin: 0 0 24px 0; font-size: 15px; line-height: 1.5; color: {_TEXT_SECONDARY};">The full field is in, {_esc(display_name)} — your one pick for the week is open.</p>

{_html_ledger_panel([("Purse", f"${purse:,}"), ("Pick deadline", deadline_str)])}
{_html_button(pick_url, "Make Your Pick")}

<p style="margin: 16px 0 0 0; font-size: 13px; color: {_TEXT_SECONDARY}; text-align: center;">Pick a primary and a backup. Each golfer is yours to use once all season.</p>'''
    return _html_wrapper(content, season_year)


def send_picks_open_email(tournament_id_or_obj) -> int:
    """
    Send "Picks Are Open" notification to all users.
    Called from sync_api.py after successful field sync.
    """
    if isinstance(tournament_id_or_obj, int):
        tournament_id = tournament_id_or_obj
    else:
        tournament_id = tournament_id_or_obj.id

    print(f"\n📬 Sending 'Picks Are Open' notifications...")

    if not CONFIG_LOADED:
        print("  ❌ Cannot send: Email configuration not loaded")
        return 0

    with _app_context():
        tournament = db.session.get(Tournament, tournament_id)
        if not tournament:
            print(f"  ❌ Tournament ID {tournament_id} not found")
            return 0

        print(f"  Tournament: {tournament.name}")

        deadline = tournament.pick_deadline
        if deadline and deadline.tzinfo is None:
            deadline = CENTRAL_TZ.localize(deadline)
        deadline_str = deadline.strftime('%A, %B %d at %I:%M %p CT') if deadline else "TBD"

        pick_url = f"{SITE_URL}/pick/{tournament.id}"
        subject = f"Picks are open: {tournament.name}"
        season_year = tournament.season_year
        tournament_name = tournament.name
        purse = tournament.purse

        users = User.query.all()
        success_count = 0

        for user in users:
            display_name = user.get_display_name()
            user_email = user.email

            # Plain text
            plain = f"""Hi {display_name},

The field for {tournament_name} is now available, and picks are open!

Tournament: {tournament_name}
Purse: ${purse:,}
Pick Deadline: {deadline_str}

Make your pick now: {pick_url}

Remember:
• Pick a primary golfer and a backup
• Each golfer can only be used once this season
• Points = actual prize money earned

Good luck this week!
{COMMISSIONER_NAME}

---
Golf Pick 'Em {season_year}
{SITE_URL}
"""

            # HTML
            html = _build_picks_open_html(
                display_name, tournament_name, purse,
                deadline_str, pick_url, season_year
            )

            if send_email(user_email, subject, plain, html_body=html):
                success_count += 1

        print(f"\n📊 Picks Open Summary: {success_count}/{len(users)} emails sent")
        return success_count


# =============================================================================
# DEADLINE REMINDER EMAILS
# =============================================================================

def build_reminder_email(user_display_name, user_total_points, user_golfers_used,
                         tournament_name, tournament_id, tournament_purse, tournament_season_year,
                         deadline, window):
    """
    Build the email subject, plain-text body, and HTML body for a deadline reminder.

    Returns:
        Tuple of (subject, plain_body, html_body)
    """
    time_remaining = get_time_remaining_display(window)
    pick_url = f"{SITE_URL}/pick/{tournament_id}"
    deadline_str = deadline.strftime('%A, %B %d at %I:%M %p %Z')

    # Subject line based on urgency
    if window['type'] == 'final':
        subject = f"Final call: {tournament_name} picks close within the hour"
    elif window['type'] == 'reminder':
        subject = f"{tournament_name} — picks close in ~12 hours"
    else:
        subject = f"{tournament_name} — picks close in ~24 hours"

    # --- Plain text body ---
    plain = f"""Hi {user_display_name},

You haven't made your pick for {tournament_name} yet!

Tournament: {tournament_name}
Purse: ${tournament_purse:,}
Deadline: {deadline_str}
Time Remaining: {time_remaining}

Make your pick now: {pick_url}

"""
    if window['type'] == 'final':
        plain += """This is the last reminder. The deadline is almost here —
make your pick before the gate closes.

"""
    elif window['type'] == 'reminder':
        plain += """About 12 hours left. One more reminder will go out
1 hour before the deadline.

"""
    else:
        plain += """About 24 hours left. Reminders will also go out
at 12 hours and 1 hour before the deadline.

"""

    plain += f"""Good luck!
{COMMISSIONER_NAME}

---
Golf Pick 'Em {tournament_season_year}
{SITE_URL}
"""

    # --- HTML body ---
    # The countdown is the hero; the tier reads through color, never a siren.
    safe_name = _esc(user_display_name)
    if window['type'] == 'final':
        accent_color = _DANGER
        hero_value = "1 hour"
        support_msg = (
            f"This is the last reminder, {safe_name} — make your pick "
            f"before the gate closes."
        )
    elif window['type'] == 'reminder':
        accent_color = _GOLD_700
        hero_value = "12 hours"
        support_msg = (
            f"About 12 hours left to make your pick, {safe_name}. "
            f"One more reminder goes out at 1 hour."
        )
    else:
        accent_color = _GREEN_700
        hero_value = "24 hours"
        support_msg = (
            f"You haven&#8217;t made your pick yet, {safe_name}. "
            f"Reminders also go out at 12 and 1 hour."
        )

    masthead = _html_masthead(
        eyebrow="Pick deadline",
        title=tournament_name,
        eyebrow_color=accent_color,
        hero_value=hero_value,
        hero_label="Time left to pick",
        hero_color=accent_color,
    )

    content = f'''{masthead}
<p style="margin: 0 0 24px 0; font-size: 15px; line-height: 1.5; color: {_TEXT_SECONDARY};">{support_msg}</p>

{_html_ledger_panel([("Purse", f"${tournament_purse:,}"), ("Deadline", deadline_str)])}
{_html_button(pick_url, "Make Your Pick", bg_color=_DANGER if window['type'] == 'final' else None)}'''

    html = _html_wrapper(content, tournament_season_year)
    return subject, plain, html


# =============================================================================
# ADMIN ALERT (Called from sync_api.py on Wednesday if field not ready)
# =============================================================================

def send_admin_field_alert(tournament_id_or_obj, field_count: int) -> bool:
    """Send alert to admin when field sync fails on Wednesday."""
    if isinstance(tournament_id_or_obj, int):
        tournament_id = tournament_id_or_obj
    else:
        tournament_id = tournament_id_or_obj.id

    print(f"\n🚨 Sending admin alert...")

    if not CONFIG_LOADED:
        print("  ❌ Cannot send: Email configuration not loaded")
        return False

    with _app_context():
        tournament = db.session.get(Tournament, tournament_id)
        if not tournament:
            print(f"  ❌ Tournament ID {tournament_id} not found")
            return False

        print(f"  Tournament: {tournament.name}")

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
# RESULTS RECAP EMAIL (Called from sync_api.py after earnings finalization)
# =============================================================================

def send_results_recap_email(tournament_id: int) -> int:
    """
    Send personalized results recap to all league members.
    Called after process_tournament_picks() finalizes earnings.

    Args:
        tournament_id: ID of the finalized tournament

    Returns:
        Number of emails successfully sent
    """
    print(f"\n📊 Sending Results Recap emails...")

    if not CONFIG_LOADED:
        print("  ❌ Cannot send: Email configuration not loaded")
        return 0

    with _app_context():
        tournament = db.session.get(Tournament, tournament_id)
        if not tournament:
            print(f"  ❌ Tournament ID {tournament_id} not found")
            return 0

        print(f"  Tournament: {tournament.name}")

        season_year = tournament.season_year
        tournament_name = tournament.name

        # ---- Gather all picks for this tournament ----
        all_picks = Pick.query.filter_by(tournament_id=tournament_id).all()
        pick_by_user = {pick.user_id: pick for pick in all_picks}

        # ---- Build weekly results for top-3 and per-user display ----
        weekly_results = []
        for pick in all_picks:
            earnings = pick.points_earned or 0
            active = pick.active_player
            backup_activated = (
                pick.active_player_id is not None
                and pick.active_player_id == pick.backup_player_id
            )

            result = None
            if pick.active_player_id:
                result = TournamentResult.query.filter_by(
                    tournament_id=tournament_id,
                    player_id=pick.active_player_id
                ).first()

            weekly_results.append({
                'user_id': pick.user_id,
                'user_name': pick.user.get_display_name(),
                'golfer_name': f"{active.first_name} {active.last_name}" if active else "N/A",
                'earnings': earnings,
                'position': result.final_position if result else None,
                'score_to_par': format_score_to_par(result.score_to_par) if result else None,
                'backup_activated': backup_activated,
            })

        # Sort by earnings desc for top-3
        weekly_results.sort(key=lambda x: x['earnings'], reverse=True)
        top_3 = weekly_results[:3]

        # ---- Calculate standings with tied ranks ----
        all_users = User.query.order_by(User.total_points.desc(), User.id).all()
        total_users = len(all_users)

        standings = {}
        prev_points = None
        prev_rank = 0
        rank_counts = {}

        for i, user in enumerate(all_users):
            if user.total_points != prev_points:
                rank = i + 1
            else:
                rank = prev_rank
            standings[user.id] = {'rank': rank, 'total_points': user.total_points}
            rank_counts[rank] = rank_counts.get(rank, 0) + 1
            prev_points = user.total_points
            prev_rank = rank

        # ---- Send personalized recap to each user ----
        users = User.query.all()
        success_count = 0

        subject = f"📊 Results: {tournament_name}"

        for user in users:
            display_name = user.get_display_name()
            user_email = user.email

            pick = pick_by_user.get(user.id)
            user_standing = standings.get(user.id, {'rank': total_users, 'total_points': 0})
            rank = user_standing['rank']
            is_tied = rank_counts.get(rank, 1) > 1
            rank_str = f"T{rank}" if is_tied else str(rank)
            rank_display = f"{rank_str} of {total_users}"
            season_total = user_standing['total_points']

            # User's pick details
            if pick and pick.active_player_id:
                active = pick.active_player
                golfer_name = f"{active.first_name} {active.last_name}" if active else "N/A"
                earnings = pick.points_earned or 0
                backup_activated = (
                    pick.active_player_id == pick.backup_player_id
                )
                result = TournamentResult.query.filter_by(
                    tournament_id=tournament_id,
                    player_id=pick.active_player_id
                ).first()
                position = result.final_position if result else "—"
                score = format_score_to_par(result.score_to_par) if result else None
            elif pick:
                # Pick exists but no active player resolved (both WD edge case)
                golfer_name = f"{pick.primary_player.first_name} {pick.primary_player.last_name}"
                earnings = pick.points_earned or 0
                backup_activated = False
                position = "WD"
                score = None
            else:
                # No pick submitted
                golfer_name = None
                earnings = 0
                backup_activated = False
                position = None
                score = None

            plain = _build_recap_plain_text(
                display_name, tournament_name, golfer_name, position,
                earnings, backup_activated, rank_display, season_total,
                top_3, user.id, season_year
            )
            html = _build_recap_html(
                display_name, tournament_name, golfer_name, position,
                score, earnings, backup_activated, rank_display, season_total,
                top_3, user.id, season_year
            )

            if send_email(user_email, subject, plain, html_body=html):
                success_count += 1

        print(f"\n📊 Results Recap Summary: {success_count}/{len(users)} emails sent")
        return success_count


def _build_recap_plain_text(display_name, tournament_name, golfer_name, position,
                            earnings, backup_activated, rank_display, season_total,
                            top_3, user_id, season_year):
    """Build plain-text fallback for the results recap email."""
    backup_note = " (backup activated)" if backup_activated else ""

    if golfer_name:
        pick_line = f"Your Pick: {golfer_name}{backup_note}"
        position_line = f"Finish: {position}"
        earnings_line = f"Earnings: ${earnings:,}"
    else:
        pick_line = "Your Pick: No pick submitted"
        position_line = ""
        earnings_line = "Earnings: $0"

    top3_lines = ""
    for i, entry in enumerate(top_3, 1):
        marker = " ← YOU" if entry['user_id'] == user_id else ""
        pos = entry.get('position') or ''
        if pos in ('1', 'T1'):
            pos_label = 'Win'
        elif pos:
            pos_label = pos
        else:
            pos_label = ''
        score_part = entry['score_to_par'] if entry['score_to_par'] else ''
        detail_parts = [p for p in [pos_label, score_part] if p]
        detail = f" ({', '.join(detail_parts)})" if detail_parts else ''
        top3_lines += f"  {i}. {entry['user_name']} — {entry['golfer_name']}{detail} — ${entry['earnings']:,}{marker}\n"

    text = f"""Hi {display_name},

Here's your recap for {tournament_name}.

{pick_line}
{position_line}
{earnings_line}

Your Standing: {rank_display}
Season Total: ${season_total:,}

This Week's Top 3:
{top3_lines}
View full standings: {SITE_URL}/

Good luck next week!
{COMMISSIONER_NAME}

---
Golf Pick 'Em {season_year}
{SITE_URL}
"""
    return text


def _build_recap_html(display_name, tournament_name, golfer_name, position,
                      score, earnings, backup_activated, rank_display, season_total,
                      top_3, user_id, season_year):
    """Build the HTML body for the results recap email."""

    # --- Earnings hero + supporting pick line ---
    # The week's earnings is the hero figure; the pick reads as a ledger note
    # beneath it. Earnings is settled money, so it stays green; $0 reads slate.
    if golfer_name:
        backup_badge = ""
        if backup_activated:
            backup_badge = (
                f' <span style="display: inline-block; background-color: {_GOLD_100}; '
                f'color: {_TEXT_PRIMARY}; font-size: 11px; font-weight: 700; '
                f'padding: 2px 8px; border-radius: 4px; letter-spacing: 0.04em; '
                f'vertical-align: middle;">BACKUP</span>'
            )
        finish_label = "Win" if position in ('1', 'T1') else _esc(position)
        score_text = f' ({_esc(score)})' if score else ""
        pick_line = (
            f'<p style="margin: 0 0 28px 0; font-size: 15px; line-height: 1.5; color: {_TEXT_SECONDARY};">'
            f'Your pick: <strong style="color: {_TEXT_PRIMARY};">{_esc(golfer_name)}</strong>'
            f'{backup_badge} &middot; {finish_label}{score_text}</p>'
        )
        hero_color = _GREEN_700 if earnings > 0 else _TEXT_SECONDARY
    else:
        pick_line = (
            f'<p style="margin: 0 0 28px 0; font-size: 15px; line-height: 1.5; color: {_TEXT_SECONDARY};">'
            f'You didn&#8217;t submit a pick this week.</p>'
        )
        hero_color = _TEXT_SECONDARY

    masthead = _html_masthead(
        eyebrow="Results",
        title=tournament_name,
        hero_value=f"${earnings:,}",
        hero_label="You earned",
        hero_color=hero_color,
    )

    # --- Your Standing ---
    standing_card = f'''<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom: 28px;">
<tr>
<td width="50%" style="padding-right: 8px;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: {_GREEN_100}; text-align: center; border-radius: 10px;">
<tr><td style="padding: 16px;">
<p style="margin: 0 0 2px 0; font-size: 11px; font-weight: 600; color: {_TEXT_SECONDARY}; text-transform: uppercase; letter-spacing: 0.05em;">Rank</p>
<p style="margin: 0; font-family: {_FONT_DISPLAY}; font-size: 26px; font-weight: 700; color: {_GREEN_700};">{rank_display}</p>
</td></tr>
</table>
</td>
<td width="50%" style="padding-left: 8px;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: {_GOLD_100}; text-align: center; border-radius: 10px;">
<tr><td style="padding: 16px;">
<p style="margin: 0 0 2px 0; font-size: 11px; font-weight: 600; color: {_TEXT_SECONDARY}; text-transform: uppercase; letter-spacing: 0.05em;">Season Total</p>
<p style="margin: 0; font-family: {_FONT_DISPLAY}; font-size: 26px; font-weight: 700; color: {_GOLD_700};">${season_total:,}</p>
</td></tr>
</table>
</td>
</tr>
</table>'''

    # --- Top 3 Weekly Leaderboard ---
    top3_rows = ""
    for i, entry in enumerate(top_3):
        is_self = entry['user_id'] == user_id
        pos = entry.get('position') or ''
        is_winner = pos in ('1', 'T1')

        # Row background: winner gets gold, self gets gold, else alternating
        if is_winner:
            row_bg = _GOLD_100
        elif is_self:
            row_bg = _GOLD_100
        else:
            row_bg = _CREAM if i % 2 == 1 else _WHITE

        bold = "font-weight: 700;" if is_self else ""
        self_marker = f' <span style="color: {_GOLD_700}; font-size: 11px; font-weight: 700;">★</span>' if is_self else ""
        score_part = f' <span style="color: {_TEXT_SECONDARY}; font-size: 12px;">({_esc(entry["score_to_par"])})</span>' if entry['score_to_par'] else ""

        # Position badge — winner gets the trophy + a pine-deep "WIN" label.
        # Pine Deep on the gold-wash row is the documented gold-surface text
        # pairing (~10:1) and sidesteps the small-pill contrast trap.
        if is_winner:
            pos_badge = (
                f'<span style="font-size: 16px; line-height: 1;">&#127942;</span> '
                f'<span style="color: {_GREEN_900}; font-size: 11px; font-weight: 700; '
                f'letter-spacing: 0.08em; vertical-align: middle; '
                f'text-transform: uppercase;">Win</span> '
            )
        elif pos in ('CUT', 'WD'):
            pos_badge = (
                f'<span style="color: {_TEXT_SECONDARY}; font-size: 11px; '
                f'font-style: italic; vertical-align: middle;">{_esc(pos)}</span> '
            )
        elif pos:
            pos_badge = (
                f'<span style="display: inline-block; background-color: {_GREEN_100}; '
                f'color: {_GREEN_700}; font-size: 11px; font-weight: 600; '
                f'padding: 1px 7px; border-radius: 10px; '
                f'vertical-align: middle;">{_esc(pos)}</span> '
            )
        else:
            pos_badge = ''

        # Winner is marked by gold rank + trophy/WIN badge; earnings stay green
        # (settled money). No side-stripe — the gold-wash row carries the accent.
        rank_color = _GOLD_700 if is_winner else _TEXT_PRIMARY
        earn_color = _GREEN_700

        top3_rows += f'''<tr>
<td style="padding: 10px 12px; border-bottom: 1px solid rgba(0,67,46,0.06); background-color: {row_bg}; {bold} font-size: 14px; color: {rank_color}; text-align: center; width: 36px; font-weight: 700;">{i + 1}</td>
<td style="padding: 10px 12px; border-bottom: 1px solid rgba(0,67,46,0.06); background-color: {row_bg}; {bold} font-size: 14px; color: {_TEXT_PRIMARY};">{_esc(entry['user_name'])}{self_marker}</td>
<td style="padding: 10px 12px; border-bottom: 1px solid rgba(0,67,46,0.06); background-color: {row_bg}; font-size: 14px; color: {_TEXT_SECONDARY};">{pos_badge}{_esc(entry['golfer_name'])}{score_part}</td>
<td style="padding: 10px 12px; border-bottom: 1px solid rgba(0,67,46,0.06); background-color: {row_bg}; {bold} font-size: 14px; color: {earn_color}; text-align: right;">${entry['earnings']:,}</td>
</tr>'''

    leaderboard = f'''<p style="margin: 0 0 12px 0; font-family: {_FONT_DISPLAY}; font-size: 18px; color: {_TEXT_PRIMARY};">This Week&#8217;s Top 3</p>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="border-collapse: collapse; margin-bottom: 24px;">
<tr>
<td style="background-color: {_GREEN_800}; color: {_TEXT_ON_DARK}; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; padding: 10px 12px; text-align: center; width: 36px;">#</td>
<td style="background-color: {_GREEN_800}; color: {_TEXT_ON_DARK}; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; padding: 10px 12px;">Member</td>
<td style="background-color: {_GREEN_800}; color: {_TEXT_ON_DARK}; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; padding: 10px 12px;">Golfer</td>
<td style="background-color: {_GREEN_800}; color: {_TEXT_ON_DARK}; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; padding: 10px 12px; text-align: right;">Earned</td>
</tr>
{top3_rows}
</table>'''

    # --- Assemble ---
    content = f'''{masthead}
{pick_line}
{standing_card}
{leaderboard}
{_html_button(SITE_URL + "/", "View Full Standings")}'''

    return _html_wrapper(content, season_year)


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

    with _app_context():
        tournament, deadline = get_upcoming_tournament_for_reminders()

        if not tournament:
            print("\n📭 No upcoming tournaments within reminder window (or field not ready)")
            return

        print(f"\n🏌️ Tournament: {tournament.name}")
        print(f"📅 Deadline: {deadline.strftime('%A, %B %d at %I:%M %p %Z')}")
        print(f"⏱️ Time remaining: {format_time_remaining(deadline)}")
        print(f"👥 Field size: {get_field_count(tournament.id)} players")

        window = get_active_reminder_window(deadline)

        if not window:
            print(f"\n⏳ Not within any reminder window")
            print(f"   Next windows: 24h, 12h, 1h before deadline")
            return

        print(f"\n📬 Active reminder window: {window['hours']}-hour ({window['type']})")

        # Dedup: skip if this tier (or a later tier) was already sent
        REMINDER_ORDER = {'24h': 0, '12h': 1, '1h': 2}

        current_tier = f"{window['hours']}h"
        if tournament.last_reminder_type:
            last_order = REMINDER_ORDER.get(tournament.last_reminder_type, -1)
            current_order = REMINDER_ORDER.get(current_tier, -1)
            if current_order <= last_order:
                print(f"\n✅ {current_tier} reminder already sent (last sent: {tournament.last_reminder_type}). Skipping.")
                return

        users_without_picks = get_users_without_picks(tournament.id)

        if not users_without_picks:
            print(f"\n✅ All users have made their picks for {tournament.name}!")
            return

        print(f"\n👥 Users without picks: {len(users_without_picks)}")

        # Extract tournament data (primitives, not ORM references)
        tournament_name = tournament.name
        tournament_id = tournament.id
        tournament_purse = tournament.purse
        tournament_season_year = tournament.season_year

        success_count = 0
        for user in users_without_picks:
            user_email = user.email
            user_display_name = user.get_display_name()
            user_total_points = user.total_points
            user_golfers_used = len(user.get_used_player_ids())

            subject, plain, html = build_reminder_email(
                user_display_name=user_display_name,
                user_total_points=user_total_points,
                user_golfers_used=user_golfers_used,
                tournament_name=tournament_name,
                tournament_id=tournament_id,
                tournament_purse=tournament_purse,
                tournament_season_year=tournament_season_year,
                deadline=deadline,
                window=window
            )

            if send_email(user_email, subject, plain, html_body=html):
                success_count += 1

        if success_count > 0:
            tournament.last_reminder_type = current_tier
            db.session.commit()
            print(f"📝 Recorded {current_tier} reminder as sent")
        else:
            print(f"⚠️ No emails sent successfully — not recording {current_tier} as sent")

        print()
        print("-" * 60)
        print(f"📊 Summary: {success_count}/{len(users_without_picks)} reminders sent")
        print("=" * 60)


if __name__ == "__main__":
    main()
