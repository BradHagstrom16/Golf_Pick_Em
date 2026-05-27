"""
Test: desktop standings table renders the missed-cut penalty badge on a LIVE major.

Bug (P0): On an active (un-finalized) major, pick.active_player_id is NULL so both
active_is_primary and active_is_backup are False → no penalty badge on desktop.
The fix gates each cell on backup_activated (which is derived from result status,
not from the nullable active_player_id).
"""
from datetime import datetime, timedelta


def _make_past_deadline():
    """Return a naive datetime in the past (3 hours ago) for use as pick_deadline."""
    return datetime.now() - timedelta(hours=3)


class TestDesktopPenaltyBadge:

    def test_live_major_primary_cut_shows_penalty_once_in_primary_column(
        self, db, make_user, make_player, make_tournament, make_result, make_pick, login
    ):
        """
        LIVE major — primary player missed the cut — desktop table must show
        badge-penalty exactly once (in the primary-pick column).

        On an un-finalized tournament active_player_id is NULL, so the previous
        active_is_primary gate suppressed the badge entirely; gating on
        backup_activated (False for a non-WD cut) renders it in the primary column.
        """
        # 1. Users
        admin = make_user(username='admin', is_admin=True)
        member = make_user(username='member')

        # 2. Players
        primary = make_player(first_name='Cut', last_name='Primary')
        backup = make_player(first_name='Safe', last_name='Backup')

        # 3. Active major with pick_deadline in the past so picks are revealed
        major = make_tournament(
            name='Test Major',
            is_major=True,
            status='active',
            purse=0,
        )
        major.pick_deadline = _make_past_deadline()
        db.session.flush()

        # 4. Result: primary missed the cut at the live major (not yet finalized —
        #    active_player_id on the Pick is NOT set, simulating a mid-tournament state)
        make_result(
            major, primary,
            status='cut',
            earnings=0,
            rounds_completed=2,
            final_position='CUT',
        )

        # 5. Pick: penalty_triggered=True, active_player_id intentionally left NULL
        #    (simulates the un-finalized live state where resolve_pick() hasn't run)
        make_pick(
            member, major,
            primary=primary,
            backup=backup,
            penalty_triggered=True,
            # active_player_id deliberately omitted → stays NULL
        )

        db.session.commit()

        # 6. GET the tournament detail page as admin (admin sees all picks)
        client = login(admin)
        resp = client.get(f'/tournament/{major.id}')
        assert resp.status_code == 200, f'Expected 200, got {resp.status_code}'

        html = resp.get_data(as_text=True)

        # Sanity: picks section rendered (deadline passed)
        assert 'Cut Primary' in html, 'Primary player name missing — picks not rendering'

        # Isolate the desktop table block only.
        # The mobile card list comes first; the legend after </table> also has badge-penalty.
        # We grab from the desktop-table class marker to its closing </table> tag.
        assert 'desktop-table' in html, 'desktop-table class missing from page'
        start = html.index('desktop-table')
        desktop = html[start: start + html[start:].index('</table>')]

        assert 'badge-penalty' in desktop, (
            'FAIL: desktop table must render the live penalty badge — '
            'badge-penalty not found in desktop table block'
        )
        assert desktop.count('badge-penalty') == 1, (
            f'FAIL: badge must render exactly once, not in both columns — '
            f'found {desktop.count("badge-penalty")} occurrences'
        )

    def test_live_major_backup_activated_cut_shows_penalty_once_in_backup_column(
        self, db, make_user, make_player, make_tournament, make_result, make_pick, login
    ):
        """
        LIVE major — primary WD'd before R2 (backup activated) and the backup
        missed the cut — the penalty badge must render exactly once and in the
        BACKUP column, never the primary column. Guards the backup-activated half
        of the backup_activated gate (the primary-cut test guards the other half).
        """
        admin = make_user(username='admin2', is_admin=True)
        member = make_user(username='member2')
        primary = make_player(first_name='Wd', last_name='Primary')
        backup = make_player(first_name='Cut', last_name='Backup')

        major = make_tournament(name='Test Major 2', is_major=True, status='active', purse=0)
        major.pick_deadline = _make_past_deadline()
        db.session.flush()

        # Primary withdrew before completing R2 → backup activates on a live tournament
        make_result(major, primary, status='wd', earnings=0, rounds_completed=1)
        # Backup is now the active golfer and missed the cut at the major
        make_result(major, backup, status='cut', earnings=0, rounds_completed=2,
                    final_position='CUT')
        make_pick(member, major, primary=primary, backup=backup, penalty_triggered=True)
        db.session.commit()

        resp = login(admin).get(f'/tournament/{major.id}')
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)
        assert 'Cut Backup' in html, 'Backup name missing — picks not rendering'

        start = html.index('desktop-table')
        desktop = html[start: start + html[start:].index('</table>')]

        assert desktop.count('badge-penalty') == 1, (
            f'badge must render exactly once — found {desktop.count("badge-penalty")}'
        )
        assert desktop.index('badge-penalty') > desktop.index('Cut Backup'), (
            'penalty badge must sit in the backup column (after the backup name), '
            'not the primary column'
        )
