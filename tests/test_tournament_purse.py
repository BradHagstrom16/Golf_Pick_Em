"""Tests for Tournament.effective_purse and Tournament.purse_is_estimate."""


def test_actual_purse_takes_precedence(make_tournament):
    tourn = make_tournament(name='Masters Tournament', purse=22_500_000)
    assert tourn.effective_purse == 22_500_000
    assert tourn.purse_is_estimate is False


def test_zero_purse_falls_back_to_estimate(make_tournament):
    tourn = make_tournament(name='PGA Championship', purse=0)
    assert tourn.effective_purse == 19_000_000
    assert tourn.purse_is_estimate is True


def test_none_purse_falls_back_to_estimate(make_tournament):
    tourn = make_tournament(name='U.S. Open', purse=None)
    assert tourn.effective_purse == 21_500_000
    assert tourn.purse_is_estimate is True


def test_unknown_tournament_returns_none(make_tournament):
    tourn = make_tournament(name='Hypothetical Open That Does Not Exist', purse=0)
    assert tourn.effective_purse is None
    assert tourn.purse_is_estimate is False
