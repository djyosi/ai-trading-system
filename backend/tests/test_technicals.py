from app.features.technicals import (
    calculate_atr_percent,
    calculate_gap_percent,
    calculate_opening_range,
    calculate_prior_levels,
    calculate_vwap,
)


def test_calculate_gap_percent_from_previous_close_and_current_price():
    assert calculate_gap_percent(previous_close=100, current_price=108.5) == 8.5


def test_calculate_gap_percent_returns_none_for_missing_or_zero_previous_close():
    assert calculate_gap_percent(previous_close=0, current_price=108.5) is None
    assert calculate_gap_percent(previous_close=None, current_price=108.5) is None


def test_calculate_vwap_from_intraday_candles():
    candles = [
        {"high": 102, "low": 98, "close": 101, "volume": 1000},
        {"high": 104, "low": 100, "close": 103, "volume": 3000},
    ]

    assert calculate_vwap(candles) == 101.83


def test_calculate_vwap_returns_none_when_volume_is_zero():
    assert calculate_vwap([{"high": 1, "low": 1, "close": 1, "volume": 0}]) is None


def test_calculate_atr_percent_from_daily_candles():
    candles = [
        {"high": 110, "low": 100, "close": 105},
        {"high": 112, "low": 104, "close": 110},
        {"high": 120, "low": 108, "close": 118},
    ]

    assert calculate_atr_percent(candles, period=3) == 8.47


def test_calculate_atr_percent_returns_none_without_close_or_candles():
    assert calculate_atr_percent([], period=14) is None
    assert calculate_atr_percent([{"high": 1, "low": 1, "close": 0}], period=1) is None


def test_calculate_opening_range_uses_first_n_candles():
    candles = [
        {"high": 101, "low": 99, "close": 100},
        {"high": 103, "low": 98, "close": 102},
        {"high": 105, "low": 97, "close": 104},
    ]

    assert calculate_opening_range(candles, candle_count=2) == {"opening_range_high": 103, "opening_range_low": 98}


def test_calculate_opening_range_returns_none_values_for_no_candles():
    assert calculate_opening_range([], candle_count=2) == {"opening_range_high": None, "opening_range_low": None}


def test_calculate_prior_levels_excludes_current_candle():
    candles = [
        {"high": 100, "low": 90},
        {"high": 105, "low": 92},
        {"high": 103, "low": 94},
    ]

    assert calculate_prior_levels(candles) == {"prior_high": 105, "prior_low": 90}
