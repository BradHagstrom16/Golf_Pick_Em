"""Guard tests for the redesigned league emails (send_reminders.py).

These render the pure HTML builders with representative data and lock in the
brand invariants the redesign established: no side-stripe borders (DESIGN.md
bans border-left/right > 1px as a decorative accent), clubhouse-voice subjects
free of siren emoji, the display-scale hero figures, and status-blue staying
reserved for tournament state (not the BACKUP marker).

The builders are pure (no DB), so they are exercised directly.
"""
import re
from datetime import datetime

import send_reminders as sr

# Matches a left/right border with its pixel value, e.g. "border-left: 4px".
# A full internal divider at 1px is allowed; anything thicker is a side-stripe.
SIDE_STRIPE_RE = re.compile(r"border-(?:left|right):\s*(\d+)px")
SIREN_EMOJI = ("🚨", "⏰", "⚠️")

TOP3 = [
    {'user_id': 1, 'user_name': 'Reilly', 'golfer_name': 'Scottie Scheffler',
     'earnings': 4_000_000, 'position': '1', 'score_to_par': '-20', 'backup_activated': False},
    {'user_id': 2, 'user_name': 'Marcus', 'golfer_name': 'Xander Schauffele',
     'earnings': 2_160_000, 'position': '2', 'score_to_par': '-18', 'backup_activated': False},
    {'user_id': 3, 'user_name': 'Dana', 'golfer_name': 'Collin Morikawa',
     'earnings': 1_360_000, 'position': 'T3', 'score_to_par': '-15', 'backup_activated': False},
]


def _deadline():
    return sr.CENTRAL_TZ.localize(datetime(2026, 7, 3, 7, 0))


def _all_member_html():
    """Render every member-facing email variant to HTML."""
    htmls = [
        sr._build_picks_open_html(
            "Reilly", "the Memorial Tournament", 20_000_000,
            "Thursday, July 3 at 7:00 AM CT", "https://x/pick/1", 2026),
    ]
    for window in sr.REMINDER_WINDOWS:
        _s, _p, html = sr.build_reminder_email(
            "Reilly", 0, 0, "the Genesis Scottish Open", 1,
            9_000_000, 2026, _deadline(), window)
        htmls.append(html)
    # Recap: winner, backup-activated, missed-cut/$0, no-pick.
    htmls.append(sr._build_recap_html(
        "Reilly", "the Memorial Tournament", "Scottie Scheffler", "1", "-20",
        4_000_000, False, "1 of 60", 8_230_500, TOP3, 1, 2026))
    htmls.append(sr._build_recap_html(
        "Marcus", "the Memorial Tournament", "Rory McIlroy", "T8", "-6",
        215_000, True, "T5 of 60", 1_200_000, TOP3, 2, 2026))
    htmls.append(sr._build_recap_html(
        "Dana", "the Memorial Tournament", "Jordan Spieth", "CUT", None,
        0, False, "42 of 60", 300_000, TOP3, 42, 2026))
    htmls.append(sr._build_recap_html(
        "Pat", "the Memorial Tournament", None, None, None,
        0, False, "58 of 60", 0, TOP3, 58, 2026))
    return htmls


def test_no_side_stripe_borders():
    for html in _all_member_html():
        for match in SIDE_STRIPE_RE.finditer(html):
            assert int(match.group(1)) <= 1, (
                f"side-stripe border '{match.group(0)}' is banned by DESIGN.md")


def test_builders_return_nonempty_html():
    for html in _all_member_html():
        assert html.lstrip().startswith("<!DOCTYPE html>")
        assert "Golf Pick" in html


def test_reminder_subjects_have_no_siren_emoji():
    for window in sr.REMINDER_WINDOWS:
        subject, _plain, _html = sr.build_reminder_email(
            "Reilly", 0, 0, "Memorial", 1, 9_000_000, 2026, _deadline(), window)
        assert not any(e in subject for e in SIREN_EMOJI), subject


def test_reminder_hero_reflects_tier():
    expected = {'warning': '24 hours', 'reminder': '12 hours', 'final': '1 hour'}
    for window in sr.REMINDER_WINDOWS:
        _s, _p, html = sr.build_reminder_email(
            "Reilly", 0, 0, "Memorial", 1, 9_000_000, 2026, _deadline(), window)
        assert expected[window['type']] in html
        if window['type'] == 'final':
            # Final tier carries the danger-red hero and CTA.
            assert sr._DANGER in html


def test_recap_earnings_hero_present():
    html = sr._build_recap_html(
        "Reilly", "Memorial", "Scottie Scheffler", "1", "-20",
        4_000_000, False, "1 of 60", 8_230_500, TOP3, 1, 2026)
    assert "$4,000,000" in html      # the hero figure
    assert "You earned" in html      # the hero label


def test_recap_backup_badge_avoids_status_blue():
    html = sr._build_recap_html(
        "Marcus", "Memorial", "Rory McIlroy", "T8", "-6",
        215_000, True, "T5 of 60", 1_200_000, TOP3, 2, 2026)
    assert "BACKUP" in html
    # Live-blue is reserved for tournament status, never the backup marker.
    assert "#2563eb" not in html


def test_recap_no_pick_is_graceful():
    html = sr._build_recap_html(
        "Pat", "Memorial", None, None, None,
        0, False, "58 of 60", 0, TOP3, 58, 2026)
    assert "didn" in html and "submit a pick" in html
    assert "$0" in html


def test_dynamic_text_is_html_escaped():
    """Member names and upstream API strings must render as text, not markup."""
    xss = '<script>alert(1)</script> & "x"'

    html = sr._build_picks_open_html(
        xss, xss, 1000, "deadline", "https://x/pick/1", 2026)
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html

    _s, _p, rhtml = sr.build_reminder_email(
        xss, 0, 0, xss, 1, 1000, 2026, _deadline(), sr.REMINDER_WINDOWS[0])
    assert "<script>alert(1)</script>" not in rhtml
    assert "&lt;script&gt;" in rhtml  # member + tournament text is escaped, not dropped

    top3 = [{'user_id': 9, 'user_name': xss, 'golfer_name': xss, 'earnings': 100,
             'position': 'T2', 'score_to_par': '-3', 'backup_activated': False}]
    chtml = sr._build_recap_html(
        "Pat", xss, xss, "T2", "-3", 100, False, "2 of 3", 100, top3, 1, 2026)
    assert "<script>alert(1)</script>" not in chtml
    assert "&lt;script&gt;" in chtml


def test_recap_handles_null_position():
    """A result row with a null final_position must not crash escaping."""
    html = sr._build_recap_html(
        "Pat", "Memorial", "Scottie Scheffler", None, None,
        0, False, "5 of 60", 100, TOP3, 99, 2026)
    assert "Scottie Scheffler" in html
    assert "—" in html  # em-dash fallback for the missing finish
