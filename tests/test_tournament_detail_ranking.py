"""
Test: desktop standings table ranks only picked rows by earnings; no-pick users
are unnumbered and collapsed into a "Didn't pick (N)" disclosure.

Bug (U4 P1): loop.index was used as the rank number, so no-pick rows (earning $0)
received sequential position numbers, causing non-pickers to appear at positions
above pickers with identical $0 earnings, and obscuring correct competition ranking.

U4 P2 (Phase 3): the no-pick rows that previously sat below a "Did not pick" divider
are now collapsed into a single muted "Didn't pick (N)" <details> disclosure listing
the non-pickers' names, so they never occupy a numbered paying row.
"""
from datetime import datetime, timedelta, timezone

from models import LEAGUE_TZ


def _desktop(html):
    """Extract just the desktop table block from the full page HTML."""
    start = html.index('desktop-table')
    return html[start: start + html[start:].index('</table>')]


def _make_past_deadline():
    """Naive Central-time timestamp 3h in the past.

    Tournament.is_deadline_passed() localizes a naive pick_deadline to LEAGUE_TZ,
    so the value must be built in Central wall-clock time (not the machine's local
    zone) to read as "passed" regardless of where the suite runs (e.g. UTC CI).
    """
    return datetime.now(timezone.utc).astimezone(LEAGUE_TZ).replace(tzinfo=None) - timedelta(hours=3)


class TestTournamentDetailRanking:
    """Standings rank only picked rows (competition ties); no-pick rows sit below a divider."""

    def test_no_pick_rows_unnumbered_and_below_divider(
        self, db, make_user, make_player, make_tournament, make_result, make_pick, login
    ):
        """
        Complete tournament: m1 ($1M), m2 ($500k), m3 (no pick).
        Picked rows must be ranked 1 and 2 with <strong>; m3 must appear in the
        "Didn't pick" collapse (after the picked rows) and must NOT have a rank number.
        """
        # Users
        admin = make_user(username='ranking_admin', is_admin=True)
        m1 = make_user(username='ranking_m1')
        m2 = make_user(username='ranking_m2')
        m3 = make_user(username='ranking_m3')

        # Players (need 4: 2 primaries + 2 backups)
        pa = make_player(first_name='Alpha', last_name='Primary')
        ba = make_player(first_name='Alpha', last_name='Backup')
        pb = make_player(first_name='Beta', last_name='Primary')
        bb = make_player(first_name='Beta', last_name='Backup')

        # Tournament (complete so pick_results use points_earned)
        t = make_tournament(name='Ranking Test', status='complete')
        t.pick_deadline = _make_past_deadline()
        db.session.flush()

        # Results for the primary players (not strictly required by the route for
        # a complete tournament, but add them so nothing blows up)
        make_result(t, pa, earnings=1_000_000)
        make_result(t, pb, earnings=500_000)

        # Picks with points_earned set directly (route reads pick.points_earned for complete)
        make_pick(m1, t, primary=pa, backup=ba, points_earned=1_000_000)
        make_pick(m2, t, primary=pb, backup=bb, points_earned=500_000)
        # m3 gets NO pick

        db.session.commit()

        client = login(admin)
        resp = client.get(f'/tournament/{t.id}')
        assert resp.status_code == 200, f'Expected 200, got {resp.status_code}'

        html = resp.get_data(as_text=True)
        desktop = _desktop(html)

        # No-pick collapse must be present ("Didn't pick (N)"; admin is also a non-picker)
        assert "Didn't pick (" in desktop, 'No-pick "Didn\'t pick (N)" collapse missing from desktop table'

        # Picked rows must show competition ranks 1 and 2
        assert '<strong>1</strong>' in desktop, 'Rank 1 missing from desktop table'
        assert '<strong>2</strong>' in desktop, 'Rank 2 missing from desktop table'

        # m3 (no-pick) must appear inside the collapse, after the picked rows
        assert desktop.index("Didn't pick") < desktop.index(m3.get_display_name()), (
            'm3 (no-pick user) must appear in the "Didn\'t pick" collapse, after the picked rows'
        )

        # No-pick users must never receive a paying rank number
        assert '<strong>3</strong>' not in desktop, (
            'No-pick user must not receive rank 3 — found <strong>3</strong> in the table'
        )

    def test_shared_ties_get_same_rank(
        self, db, make_user, make_player, make_tournament, make_result, make_pick, login
    ):
        """
        m1 $1M (rank 1), m2 $500k (rank 2), m3 $500k (rank 2), m4 no pick.
        The two $500k rows must both show rank 2; rank 3 must NOT appear;
        m4 (no pick) must sit in the "Didn't pick" collapse and be unranked.
        """
        admin = make_user(username='tie_admin', is_admin=True)
        m1 = make_user(username='tie_m1')
        m2 = make_user(username='tie_m2')
        m3 = make_user(username='tie_m3')
        m4 = make_user(username='tie_m4')

        pa = make_player(first_name='TieAlpha', last_name='Primary')
        bka = make_player(first_name='TieAlpha', last_name='Backup')
        pb = make_player(first_name='TieBeta', last_name='Primary')
        bkb = make_player(first_name='TieBeta', last_name='Backup')
        pc = make_player(first_name='TieGamma', last_name='Primary')
        bkc = make_player(first_name='TieGamma', last_name='Backup')

        t = make_tournament(name='Tie Test', status='complete')
        t.pick_deadline = _make_past_deadline()
        db.session.flush()

        make_result(t, pa, earnings=1_000_000)
        make_result(t, pb, earnings=500_000)
        make_result(t, pc, earnings=500_000)

        make_pick(m1, t, primary=pa, backup=bka, points_earned=1_000_000)
        make_pick(m2, t, primary=pb, backup=bkb, points_earned=500_000)
        make_pick(m3, t, primary=pc, backup=bkc, points_earned=500_000)
        # m4 gets NO pick

        db.session.commit()

        client = login(admin)
        resp = client.get(f'/tournament/{t.id}')
        assert resp.status_code == 200, f'Expected 200, got {resp.status_code}'

        html = resp.get_data(as_text=True)
        desktop = _desktop(html)

        # Rank 1 appears exactly once
        assert desktop.count('<strong>1</strong>') == 1, (
            f'Expected rank 1 exactly once, got {desktop.count("<strong>1</strong>")}'
        )

        # Both $500k rows share rank 2 → appears twice
        assert desktop.count('<strong>2</strong>') == 2, (
            f'Expected rank 2 exactly twice (tie), got {desktop.count("<strong>2</strong>")}'
        )

        # Rank 3 must NOT appear (tie skips 3; next would be 4)
        assert '<strong>3</strong>' not in desktop, (
            'Rank 3 must not appear — tied rank-2 entries skip to 4'
        )

        # m4 (no-pick) must be in the "Didn't pick" collapse and unranked
        assert "Didn't pick (" in desktop, 'No-pick collapse missing from desktop table'
        assert desktop.index("Didn't pick") < desktop.index(m4.get_display_name()), (
            'm4 (no-pick user) must appear in the "Didn\'t pick" collapse, after the picked rows'
        )
