from app.core.config import Settings
from app.universe.filters import is_symbol_eligible


def test_liquid_common_stock_is_eligible():
    symbol = {"ticker": "AAPL", "asset_type": "stock", "exchange": "NASDAQ"}
    metrics = {"price": 200.00, "avg_daily_volume": 50_000_000, "dollar_volume": 10_000_000_000}

    eligible, reasons = is_symbol_eligible(symbol, metrics, Settings())

    assert eligible is True
    assert reasons == []


def test_liquid_etf_is_eligible():
    symbol = {"ticker": "SPY", "asset_type": "etf", "exchange": "NYSE"}
    metrics = {"price": 500.00, "avg_daily_volume": 80_000_000, "dollar_volume": 40_000_000_000}

    eligible, reasons = is_symbol_eligible(symbol, metrics, Settings())

    assert eligible is True
    assert reasons == []


def test_stock_under_five_dollars_is_rejected_to_avoid_penny_stocks():
    symbol = {"ticker": "CHEAP", "asset_type": "stock", "exchange": "NASDAQ"}
    metrics = {"price": 4.99, "avg_daily_volume": 5_000_000, "dollar_volume": 25_000_000}

    eligible, reasons = is_symbol_eligible(symbol, metrics, Settings())

    assert eligible is False
    assert "price_below_min" in reasons


def test_otc_stock_is_rejected():
    symbol = {"ticker": "OTCXYZ", "asset_type": "stock", "exchange": "OTC", "is_otc": True}
    metrics = {"price": 10.00, "avg_daily_volume": 5_000_000, "dollar_volume": 50_000_000}

    eligible, reasons = is_symbol_eligible(symbol, metrics, Settings())

    assert eligible is False
    assert "otc_not_allowed" in reasons


def test_non_standard_security_types_are_rejected():
    for flag, reason in [
        ("is_warrant", "warrants_not_allowed"),
        ("is_preferred", "preferreds_not_allowed"),
        ("is_unit", "units_not_allowed"),
        ("is_right", "rights_not_allowed"),
    ]:
        symbol = {"ticker": "BAD", "asset_type": "stock", "exchange": "NYSE", flag: True}
        metrics = {"price": 10.00, "avg_daily_volume": 5_000_000, "dollar_volume": 50_000_000}

        eligible, reasons = is_symbol_eligible(symbol, metrics, Settings())

        assert eligible is False
        assert reason in reasons


def test_thin_volume_is_rejected():
    symbol = {"ticker": "THIN", "asset_type": "stock", "exchange": "NYSE"}
    metrics = {"price": 20.00, "avg_daily_volume": 100_000, "dollar_volume": 2_000_000}

    eligible, reasons = is_symbol_eligible(symbol, metrics, Settings())

    assert eligible is False
    assert "avg_daily_volume_below_min" in reasons
    assert "dollar_volume_below_min" in reasons


def test_leveraged_and_inverse_etfs_are_rejected_initially():
    for flag, reason in [
        ("is_leveraged_etf", "leveraged_etfs_not_allowed"),
        ("is_inverse_etf", "inverse_etfs_not_allowed"),
    ]:
        symbol = {"ticker": "ETF", "asset_type": "etf", "exchange": "NYSE", flag: True}
        metrics = {"price": 50.00, "avg_daily_volume": 5_000_000, "dollar_volume": 250_000_000}

        eligible, reasons = is_symbol_eligible(symbol, metrics, Settings())

        assert eligible is False
        assert reason in reasons


def test_unsupported_asset_type_and_exchange_are_rejected():
    symbol = {"ticker": "BTCUSD", "asset_type": "crypto", "exchange": "CRYPTO"}
    metrics = {"price": 50_000.00, "avg_daily_volume": 5_000_000, "dollar_volume": 250_000_000}

    eligible, reasons = is_symbol_eligible(symbol, metrics, Settings())

    assert eligible is False
    assert "asset_type_not_allowed" in reasons
    assert "exchange_not_allowed" in reasons
