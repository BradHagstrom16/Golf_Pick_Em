"""Tests for sync_api module functions."""
from sync_api import calculate_projected_earnings


class TestCalculateProjectedEarnings:

    def test_major_multiplier_applied(self):
        """Major tournaments apply 1.5x multiplier to projected earnings."""
        all_positions = ["1", "2", "3"]
        purse = 22_500_000

        base = calculate_projected_earnings("1", purse, all_positions, is_major=False)
        major = calculate_projected_earnings("1", purse, all_positions, is_major=True)
        assert major == int(base * 1.5)

    def test_major_default_is_false(self):
        """is_major defaults to False — existing callers unaffected."""
        all_positions = ["1"]
        base = calculate_projected_earnings("1", 10_000_000, all_positions)
        explicit = calculate_projected_earnings("1", 10_000_000, all_positions, is_major=False)
        assert base == explicit

    def test_major_cut_stays_zero(self):
        """CUT earnings stay 0 regardless of major flag."""
        result = calculate_projected_earnings("CUT", 22_500_000, ["CUT"], is_major=True)
        assert result == 0
