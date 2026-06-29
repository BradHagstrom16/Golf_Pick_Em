"""Tests for sync_api module functions."""
from sync_api import calculate_projected_earnings, normalize_position


class TestNormalizePosition:
    """normalize_position keeps a single invariant: final_position is always a
    string ("" when absent), never None — so display code never has to guard."""

    def test_none_becomes_empty_string(self):
        """Absent/null position (the crash-causing case) coerces to ""."""
        assert normalize_position(None) == ""

    def test_empty_string_stays_empty(self):
        assert normalize_position("") == ""

    def test_whitespace_is_stripped(self):
        assert normalize_position("  T5  ") == "T5"

    def test_plain_position_preserved(self):
        assert normalize_position("1") == "1"
        assert normalize_position("CUT") == "CUT"

    def test_mongodb_number_format(self):
        """API drift: positions can arrive as MongoDB-style number objects."""
        assert normalize_position({"$numberInt": "5"}) == "5"
        assert normalize_position({"$numberLong": "12"}) == "12"

    def test_numeric_type_coerced(self):
        assert normalize_position(5) == "5"

    def test_never_returns_none(self):
        for raw in (None, "", "  ", {}, {"unexpected": "shape"}, "T2", 7):
            assert normalize_position(raw) is not None
            assert isinstance(normalize_position(raw), str)


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
