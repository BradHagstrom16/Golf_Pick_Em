"""Penalty flag resolution — tests the 9-branch matrix for Pick.resolve_pick()."""


def _resolve(pick):
    pick.resolve_pick()
    return pick


class TestPenaltyTriggered:

    def test_major_primary_cut(self, make_user, make_player, make_tournament, make_result, make_pick):
        """Major + primary plays + CUT → penalty triggered."""
        u = make_user()
        p1, p2 = make_player(), make_player()
        t = make_tournament(is_major=True, purse=22_500_000)
        make_result(t, p1, status='cut', final_position='CUT', earnings=0, rounds_completed=2)
        make_result(t, p2, status='complete', final_position='10', earnings=100_000)
        pick = make_pick(u, t, p1, p2)
        _resolve(pick)
        assert pick.penalty_triggered is True
        assert pick.active_player_id == p1.id

    def test_major_primary_dq(self, make_user, make_player, make_tournament, make_result, make_pick):
        """Major + primary plays + DQ → penalty triggered."""
        u = make_user()
        p1, p2 = make_player(), make_player()
        t = make_tournament(is_major=True)
        make_result(t, p1, status='dq', final_position='DQ', earnings=0, rounds_completed=2)
        make_result(t, p2, status='complete', earnings=50_000)
        pick = make_pick(u, t, p1, p2)
        _resolve(pick)
        assert pick.penalty_triggered is True

    def test_major_primary_made_cut(self, make_user, make_player, make_tournament, make_result, make_pick):
        """Major + primary plays + made cut → no penalty."""
        u = make_user()
        p1, p2 = make_player(), make_player()
        t = make_tournament(is_major=True)
        make_result(t, p1, status='complete', final_position='T15', earnings=200_000)
        make_result(t, p2, status='complete', earnings=50_000)
        pick = make_pick(u, t, p1, p2)
        _resolve(pick)
        assert pick.penalty_triggered is False

    def test_non_major_primary_cut(self, make_user, make_player, make_tournament, make_result, make_pick):
        """Non-major + primary CUT → no penalty."""
        u = make_user()
        p1, p2 = make_player(), make_player()
        t = make_tournament(is_major=False)
        make_result(t, p1, status='cut', earnings=0, rounds_completed=2)
        make_result(t, p2, status='complete', earnings=50_000)
        pick = make_pick(u, t, p1, p2)
        _resolve(pick)
        assert pick.penalty_triggered is False

    def test_major_primary_wd_early_backup_cut(self, make_user, make_player, make_tournament, make_result, make_pick):
        """Major + primary WD before R2 + backup plays and CUTs → backup active, penalty triggered."""
        u = make_user()
        p1, p2 = make_player(), make_player()
        t = make_tournament(is_major=True)
        make_result(t, p1, status='wd', earnings=0, rounds_completed=0)
        make_result(t, p2, status='cut', final_position='CUT', earnings=0, rounds_completed=2)
        pick = make_pick(u, t, p1, p2)
        _resolve(pick)
        assert pick.active_player_id == p2.id
        assert pick.penalty_triggered is True

    def test_major_primary_wd_early_backup_made_cut(self, make_user, make_player, make_tournament, make_result, make_pick):
        """Major + primary WD before R2 + backup plays through → no penalty."""
        u = make_user()
        p1, p2 = make_player(), make_player()
        t = make_tournament(is_major=True)
        make_result(t, p1, status='wd', earnings=0, rounds_completed=0)
        make_result(t, p2, status='complete', final_position='T20', earnings=150_000)
        pick = make_pick(u, t, p1, p2)
        _resolve(pick)
        assert pick.active_player_id == p2.id
        assert pick.penalty_triggered is False

    def test_major_both_wd_early(self, make_user, make_player, make_tournament, make_result, make_pick):
        """Major + both WD before R2 → primary active with 0 pts, no penalty (status is 'wd' not 'cut'/'dq')."""
        u = make_user()
        p1, p2 = make_player(), make_player()
        t = make_tournament(is_major=True)
        make_result(t, p1, status='wd', earnings=0, rounds_completed=0)
        make_result(t, p2, status='wd', earnings=0, rounds_completed=0)
        pick = make_pick(u, t, p1, p2)
        _resolve(pick)
        assert pick.active_player_id == p1.id
        assert pick.penalty_triggered is False

    def test_major_primary_wd_after_r2(self, make_user, make_player, make_tournament, make_result, make_pick):
        """Major + primary WD after R2 → primary stays active with 0 pts, no penalty (status 'wd')."""
        u = make_user()
        p1, p2 = make_player(), make_player()
        t = make_tournament(is_major=True)
        make_result(t, p1, status='wd', earnings=0, rounds_completed=3)
        make_result(t, p2, status='complete', earnings=50_000)
        pick = make_pick(u, t, p1, p2)
        _resolve(pick)
        assert pick.active_player_id == p1.id
        assert pick.penalty_triggered is False

    def test_major_primary_dq_explicit(self, make_user, make_player, make_tournament, make_result, make_pick):
        """Major + primary DQ → penalty triggered (duplicate coverage of DQ path)."""
        u = make_user()
        p1, p2 = make_player(), make_player()
        t = make_tournament(is_major=True)
        make_result(t, p1, status='dq', earnings=0, rounds_completed=1)
        make_result(t, p2, status='complete', earnings=50_000)
        pick = make_pick(u, t, p1, p2)
        _resolve(pick)
        assert pick.penalty_triggered is True
