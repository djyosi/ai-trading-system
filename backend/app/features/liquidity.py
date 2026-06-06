def calculate_dollar_volume(price, volume):
    if price is None or volume is None:
        return None
    return round(price * volume, 2)


def calculate_spread_percent(bid, ask):
    if bid is None or ask is None or bid <= 0 or ask <= 0 or ask < bid:
        return None
    midpoint = (bid + ask) / 2
    if midpoint == 0:
        return None
    return round(((ask - bid) / midpoint) * 100, 2)


def calculate_relative_volume(current_volume, average_volume):
    if average_volume is None or average_volume == 0 or current_volume is None:
        return None
    return round(current_volume / average_volume, 2)


def calculate_liquidity_score(price, volume, average_volume, bid=None, ask=None):
    dollar_volume = calculate_dollar_volume(price, volume) or 0
    relative_volume = calculate_relative_volume(volume, average_volume) or 0
    spread_percent = calculate_spread_percent(bid, ask) if bid is not None and ask is not None else None

    score = 0
    if dollar_volume >= 10_000_000:
        score += 40
    elif dollar_volume >= 5_000_000:
        score += 25
    elif dollar_volume >= 1_000_000:
        score += 10

    if average_volume >= 750_000:
        score += 25
    elif average_volume >= 250_000:
        score += 10

    if relative_volume >= 2:
        score += 20
    elif relative_volume >= 1:
        score += 10

    if spread_percent is None:
        score += 0
    elif spread_percent <= 0.1:
        score += 15
    elif spread_percent <= 0.75:
        score += 10
    elif spread_percent <= 2:
        score += 1

    return min(score, 100)
