from decimal import Decimal

from app.core.config import Settings


def test_default_filters_avoid_penny_stocks():
    settings = Settings()

    assert settings.min_price == Decimal("5.00")
    assert settings.min_avg_daily_volume == 750_000
    assert settings.min_dollar_volume == 10_000_000
    assert settings.default_risk_profile == "moderate"


def test_default_ibkr_configuration_is_paper_and_disabled():
    settings = Settings()

    assert settings.ibkr_host == "127.0.0.1"
    assert settings.ibkr_port == 7497
    assert settings.ibkr_client_id == 7
    assert settings.ibkr_account_mode == "paper"
    assert settings.enable_ibkr is False


def test_default_data_provider_configuration_prefers_massive_with_fallback():
    settings = Settings()

    assert settings.massive_base_url == "https://api.massive.com"
    assert settings.massive_api_key is None
    assert settings.enable_yfinance_fallback is True


def test_environment_overrides_are_supported():
    settings = Settings(
        min_price="10.00",
        massive_api_key="test-key",
        enable_ibkr=True,
    )

    assert settings.min_price == Decimal("10.00")
    assert settings.massive_api_key == "test-key"
    assert settings.enable_ibkr is True
