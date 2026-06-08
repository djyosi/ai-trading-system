def simulate_paper_trade(recommendation, candles, account_equity=100_000, risk_fraction=0.01):
    if recommendation.get("status") == "no_trade":
        return {"status": "skipped", "ticker": recommendation.get("ticker"), "exit_reason": "no_trade_recommendation"}
    if recommendation.get("direction", "long") != "long":
        return {"status": "skipped", "ticker": recommendation.get("ticker"), "exit_reason": "short_model_not_implemented"}

    entry_zone = recommendation.get("entry_zone") or []
    stop_loss = recommendation.get("stop_loss")
    targets = recommendation.get("targets") or []
    if len(entry_zone) < 2 or stop_loss is None or not targets:
        return {"status": "skipped", "ticker": recommendation.get("ticker"), "exit_reason": "missing_trade_plan"}

    entry_price = round(sum(entry_zone[:2]) / 2, 4)
    risk_per_share = entry_price - stop_loss
    if risk_per_share <= 0:
        return {"status": "skipped", "ticker": recommendation.get("ticker"), "exit_reason": "invalid_risk"}

    risk_amount = round(account_equity * risk_fraction, 2)
    shares = int(risk_amount / risk_per_share)
    entered = False

    for candle in candles:
        high = candle.get("high")
        low = candle.get("low")
        if high is None or low is None:
            continue
        if not entered:
            if low <= entry_zone[1] and high >= entry_zone[0]:
                entered = True
            else:
                continue
        if low <= stop_loss:
            return _closed(recommendation, entry_price, stop_loss, "stop_hit", shares, risk_amount)
        if high >= targets[0]:
            return _closed(recommendation, entry_price, targets[0], "target_hit", shares, risk_amount)

    if not entered:
        return {"status": "not_triggered", "ticker": recommendation.get("ticker"), "exit_reason": "entry_not_hit"}
    final_close = candles[-1].get("close") if candles else entry_price
    return _closed(recommendation, entry_price, final_close, "horizon_close", shares, risk_amount)


def _closed(recommendation, entry_price, exit_price, exit_reason, shares, risk_amount):
    pnl = round((exit_price - entry_price) * shares, 2)
    realized_r = round(pnl / risk_amount, 2) if risk_amount else None
    return {
        "status": "closed",
        "ticker": recommendation.get("ticker"),
        "entry_price": entry_price,
        "exit_price": exit_price,
        "exit_reason": exit_reason,
        "shares": shares,
        "risk_amount": risk_amount,
        "realized_pnl": pnl,
        "realized_r": realized_r,
    }
