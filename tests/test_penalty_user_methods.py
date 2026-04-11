"""Tests for User.penalty_owed() / penalty_outstanding()."""


class TestPenaltyOwed:

    def test_zero_when_no_triggered_picks(self, make_user, make_player, make_tournament, make_pick):
        u = make_user()
        p1, p2 = make_player(), make_player()
        t = make_tournament(is_major=True)
        make_pick(u, t, p1, p2)  # penalty_triggered defaults False
        assert u.penalty_owed(2026) == 0

    def test_sums_triggered_picks_at_15(self, make_user, make_player, make_tournament, make_pick):
        u = make_user()
        t1 = make_tournament(is_major=True)
        t2 = make_tournament(is_major=True)
        t3 = make_tournament(is_major=True)
        for t in (t1, t2, t3):
            p1, p2 = make_player(), make_player()
            pick = make_pick(u, t, p1, p2)
            pick.penalty_triggered = True
        assert u.penalty_owed(2026) == 45

    def test_other_season_excluded(self, make_user, make_player, make_tournament, make_pick):
        u = make_user()
        t_prior = make_tournament(is_major=True, season_year=2025)
        t_curr = make_tournament(is_major=True, season_year=2026)
        for t in (t_prior, t_curr):
            p1, p2 = make_player(), make_player()
            pick = make_pick(u, t, p1, p2)
            pick.penalty_triggered = True
        assert u.penalty_owed(2026) == 15
        assert u.penalty_owed(2025) == 15

    def test_outstanding_subtracts_paid(self, make_user, make_player, make_tournament, make_pick):
        u = make_user()
        t1 = make_tournament(is_major=True)
        t2 = make_tournament(is_major=True)
        for t in (t1, t2):
            p1, p2 = make_player(), make_player()
            pick = make_pick(u, t, p1, p2)
            pick.penalty_triggered = True
        u.penalty_paid = 15
        assert u.penalty_outstanding(2026) == 15

    def test_outstanding_clamps_at_zero_on_overpayment(self, make_user, make_player, make_tournament, make_pick):
        u = make_user()
        t = make_tournament(is_major=True)
        p1, p2 = make_player(), make_player()
        pick = make_pick(u, t, p1, p2)
        pick.penalty_triggered = True
        u.penalty_paid = 50
        assert u.penalty_outstanding(2026) == 0
