from decimal import Decimal

from app.core.config import settings as default_settings

ALLOWED_ASSET_TYPES = {"stock", "etf"}
ALLOWED_EXCHANGES = {"NYSE", "NASDAQ", "AMEX"}


def _as_decimal(value, default="0"):
    if value is None:
        return Decimal(default)
    return Decimal(str(value))


def _as_int(value, default=0):
    if value is None:
        return default
    return int(value)


def is_symbol_eligible(symbol, metrics, settings=None):
    """Return whether a symbol passes the MVP universe and liquidity filters.

    The MVP targets liquid US stocks/ETFs and intentionally avoids penny stocks,
    OTC names, non-standard securities, leveraged ETFs, and inverse ETFs.
    """
    active_settings = settings or default_settings
    reasons = []

    asset_type = str(symbol.get("asset_type", "")).lower()
    exchange = str(symbol.get("exchange", "")).upper()
    price = _as_decimal(metrics.get("price"))
    avg_daily_volume = _as_int(metrics.get("avg_daily_volume"))
    dollar_volume = _as_decimal(metrics.get("dollar_volume"))

    if asset_type not in ALLOWED_ASSET_TYPES:
        reasons.append("asset_type_not_allowed")

    if exchange not in ALLOWED_EXCHANGES:
        reasons.append("exchange_not_allowed")

    if symbol.get("is_otc") or exchange == "OTC":
        reasons.append("otc_not_allowed")

    if symbol.get("is_warrant"):
        reasons.append("warrants_not_allowed")

    if symbol.get("is_preferred"):
        reasons.append("preferreds_not_allowed")

    if symbol.get("is_unit"):
        reasons.append("units_not_allowed")

    if symbol.get("is_right"):
        reasons.append("rights_not_allowed")

    if symbol.get("is_leveraged_etf"):
        reasons.append("leveraged_etfs_not_allowed")

    if symbol.get("is_inverse_etf"):
        reasons.append("inverse_etfs_not_allowed")

    if price < active_settings.min_price:
        reasons.append("price_below_min")

    if avg_daily_volume < active_settings.min_avg_daily_volume:
        reasons.append("avg_daily_volume_below_min")

    if dollar_volume < active_settings.min_dollar_volume:
        reasons.append("dollar_volume_below_min")

    return len(reasons) == 0, reasons
