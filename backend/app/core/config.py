from decimal import Decimal
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "local"
    log_level: str = "INFO"
    database_url: str = "postgresql+psycopg://trading:trading@localhost:5432/trading"

    massive_api_key: Optional[str] = None
    massive_base_url: str = "https://api.massive.com"
    enable_yfinance_fallback: bool = True

    llm_provider: Optional[str] = None
    llm_base_url: Optional[str] = None
    llm_api_key: Optional[str] = None
    llm_model: Optional[str] = None

    ibkr_host: str = "127.0.0.1"
    ibkr_port: int = 7497
    ibkr_client_id: int = 7
    ibkr_account_mode: str = "paper"
    enable_ibkr: bool = False

    default_risk_profile: str = "moderate"
    min_price: Decimal = Field(default=Decimal("5.00"))
    min_avg_daily_volume: int = 750_000
    min_dollar_volume: int = 10_000_000
    min_risk_reward: Decimal = Field(default=Decimal("2.0"))
    max_spread_percent: Decimal = Field(default=Decimal("0.75"))


settings = Settings()
