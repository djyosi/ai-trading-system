"""Market intelligence catalog for TA recommendations.

Adds non-technical evidence from Massive.com:
- news/catalysts
- company fundamentals/reference data
- live snapshot liquidity / gap context

Important policy: news/catalysts are CATALOG-ONLY for now. They are stored so
future analysis can measure whether historical news improved outcomes, but they
must not affect ranking, final score, or IBKR execution decisions.
"""

import asyncio
from datetime import datetime, timedelta, timezone

from app.catalysts.classifier import classify_catalyst

BULLISH_CATALYSTS = {
    "insider_director_purchase",
    "insider_officer_purchase",
    "insider_cluster_buying",
    "earnings_beat",
    "guidance_raise",
    "analyst_upgrade",
    "analyst_initiation",
    "fda_approval",
    "fda_clinical",
    "contract_win",
    "product_launch",
    "partnership",
    "buyback",
    "dividend",
    "credit_rating",
    "merger_acquisition",
    "m_and_a",
}

BEARISH_CATALYSTS = {
    "insider_large_sale",
    "earnings_miss",
    "guidance_cut",
    "analyst_downgrade",
    "investigation",
}


class MarketIntelError(RuntimeError):
    """Raised only for programmer errors. Provider failures are swallowed."""


def _parse_dt(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _infer_catalyst_type(title, description=""):
    text = f"{title or ''} {description or ''}".lower()
    if "earnings beat" in text or "beats earnings" in text or "beats estimates" in text:
        return "earnings_beat"
    if "earnings miss" in text or "misses earnings" in text or "missed expectations" in text:
        return "earnings_miss"
    if "raises guidance" in text or "guidance raise" in text:
        return "guidance_raise"
    if "cuts guidance" in text or "guidance cut" in text:
        return "guidance_cut"
    if "upgrade" in text:
        return "analyst_upgrade"
    if "downgrade" in text:
        return "analyst_downgrade"
    if "fda approval" in text or "approved by fda" in text or "fda clearance" in text:
        return "fda_approval"
    if "clinical trial" in text or "phase 1" in text or "phase 2" in text or "phase 3" in text:
        return "fda_clinical"
    if "contract" in text and ("win" in text or "award" in text):
        return "contract_win"
    if "partnership" in text or "strategic alliance" in text or "collaborat" in text:
        return "partnership"
    if "buyback" in text or "repurchase" in text:
        return "buyback"
    if "dividend" in text and ("increase" in text or "raise" in text or "special" in text):
        return "dividend"
    if "launch" in text or "unveils" in text or "introduces" in text:
        return "product_launch"
    if "acquire" in text or "acquisition" in text or "merger" in text or "buyout" in text:
        return "m_and_a"
    if "investigation" in text or "lawsuit" in text or "sec probe" in text:
        return "investigation"
    if "initiat" in text and ("coverage" in text or "rating" in text):
        return "analyst_initiation"
    if "credit rating" in text or ("moody" in text and "rating" in text):
        return "credit_rating"
    return "unknown"


def catalog_news(news_items, now=None):
    """Return classified news evidence for future analysis; never score it for ranking."""
    now = now or datetime.now(timezone.utc)
    evidence = []
    risk_flags = []

    for item in news_items[:10]:
        title = item.get("title") or item.get("headline") or ""
        desc = item.get("description") or item.get("summary") or ""
        catalyst_type = item.get("catalyst_type") or _infer_catalyst_type(title, desc)
        classified = classify_catalyst({"catalyst_type": catalyst_type})
        published = _parse_dt(item.get("published_utc"))
        age_days = (now - published).days if published else None

        if catalyst_type in BEARISH_CATALYSTS:
            risk_flags.append(catalyst_type)

        evidence.append({
            "type": catalyst_type,
            "signal": classified.get("signal"),
            "strength": classified.get("strength"),
            "classifier_score": classified.get("score", 0),
            "headline": title[:160],
            "source": (item.get("publisher") or {}).get("name") or item.get("source"),
            "url": item.get("article_url") or item.get("url"),
            "published_utc": item.get("published_utc"),
            "age_days": age_days,
            "catalog_only": True,
        })

    return {
        "news_score": 0,
        "catalysts": evidence[:5],
        "risk_flags": risk_flags[:5],
        "catalog_only": True,
    }


def score_snapshot(snapshot):
    """Score snapshot context: day gap, liquidity, spread.

    This is small by design; TA still carries the signal. Snapshot is context.
    """
    if not snapshot:
        return {"snapshot_score": 0, "snapshot": {}, "risk_flags": []}

    day = snapshot.get("day") or {}
    prev = snapshot.get("prevDay") or {}
    quote = snapshot.get("lastQuote") or {}
    price = day.get("c") or snapshot.get("price")
    prev_close = prev.get("c") or snapshot.get("previous_close")
    volume = day.get("v") or snapshot.get("volume") or 0
    bid = quote.get("p") or snapshot.get("bid")
    ask = quote.get("P") or snapshot.get("ask")

    gap_pct = None
    if price and prev_close:
        gap_pct = (price - prev_close) / prev_close * 100

    spread_pct = None
    if bid and ask and price:
        spread_pct = (ask - bid) / price * 100

    score = 0
    flags = []
    if volume >= 5_000_000:
        score += 1
    elif volume < 500_000:
        flags.append("thin_volume")
        score -= 1

    if gap_pct is not None:
        if 0.5 <= gap_pct <= 5:
            score += 1
        elif gap_pct < -3:
            score -= 1
            flags.append("gap_down")
        elif gap_pct > 8:
            flags.append("overextended_gap")
            score -= 0.5

    if spread_pct is not None and spread_pct > 0.75:
        score -= 1
        flags.append("wide_spread")

    return {
        "snapshot_score": round(score, 2),
        "snapshot": {
            "price": price,
            "previous_close": prev_close,
            "gap_pct": round(gap_pct, 2) if gap_pct is not None else None,
            "volume": volume,
            "spread_pct": round(spread_pct, 3) if spread_pct is not None else None,
        },
        "risk_flags": flags,
    }


def score_details(details):
    """Score company/reference data from Massive ticker details."""
    if not details:
        return {"details_score": 0, "details": {}, "risk_flags": []}
    market_cap = details.get("market_cap") or 0
    active = details.get("active", True)
    ticker_type = details.get("type")

    score = 0
    flags = []
    if not active:
        score -= 5
        flags.append("inactive_ticker")
    if ticker_type and ticker_type not in {"CS", "ETF", "ADRC"}:
        flags.append(f"type_{ticker_type}")
        score -= 0.5
    if market_cap >= 10_000_000_000:
        score += 1
    elif 0 < market_cap < 1_000_000_000:
        score -= 1
        flags.append("small_cap")

    return {
        "details_score": round(score, 2),
        "details": {
            "name": details.get("name"),
            "market_cap": market_cap or None,
            "type": ticker_type,
            "active": active,
            "homepage_url": details.get("homepage_url"),
        },
        "risk_flags": flags,
    }


def combine_intelligence(news=None, snapshot=None, details=None):
    news_part = catalog_news(news or [])
    snapshot_part = score_snapshot(snapshot or {})
    details_part = score_details(details or {})
    # Policy: market/news intelligence is catalog-only for now. Keep raw context for
    # future outcome analysis, but do not let it affect score/ranking/orders.
    return {
        "intel_score": 0,
        "news_score": 0,
        "snapshot_score": 0,
        "details_score": 0,
        "catalysts": news_part["catalysts"],
        "snapshot": snapshot_part["snapshot"],
        "details": details_part["details"],
        "risk_flags": news_part["risk_flags"] + snapshot_part["risk_flags"] + details_part["risk_flags"],
        "catalog_only": True,
    }


async def _fetch_json(client, path, params):
    try:
        resp = await client.get(path, params=params)
        if resp.status_code != 200:
            return {}
        return resp.json()
    except Exception:
        return {}


async def fetch_ticker_intel(client, ticker, api_key, end_date=None):
    """Fetch Massive intelligence for one ticker. Provider failures return empty intel."""
    if not api_key:
        return combine_intelligence()

    end_dt = datetime.now(timezone.utc) if end_date is None else datetime.fromisoformat(str(end_date))
    start_dt = end_dt - timedelta(days=7)
    params_key = {"apiKey": api_key}

    news_task = _fetch_json(
        client,
        "/v2/reference/news",
        {
            "ticker": ticker,
            "published_utc.gte": start_dt.date().isoformat(),
            "published_utc.lte": end_dt.date().isoformat(),
            "order": "desc",
            "limit": 10,
            "apiKey": api_key,
        },
    )
    details_task = _fetch_json(client, f"/v3/reference/tickers/{ticker}", params_key)
    snapshot_task = _fetch_json(
        client,
        f"/v2/snapshot/locale/us/markets/stocks/tickers/{ticker}",
        params_key,
    )
    news_payload, details_payload, snapshot_payload = await asyncio.gather(
        news_task,
        details_task,
        snapshot_task,
    )
    return combine_intelligence(
        news=news_payload.get("results", []),
        details=details_payload.get("results", {}),
        snapshot=snapshot_payload.get("ticker", {}),
    )


async def enrich_recommendations(client, recommendations, api_key, scan_date=None, limit=50):
    """Attach Massive catalog data without changing ranking or scores."""
    if not recommendations:
        return []

    sem = asyncio.Semaphore(8)

    async def enrich_one(rec):
        async with sem:
            intel = await fetch_ticker_intel(client, rec["ticker"], api_key, scan_date)
        enriched = dict(rec)
        enriched["ta_score"] = rec.get("score", 0)
        enriched["intel_score"] = 0
        enriched["final_score"] = enriched["ta_score"]
        enriched["market_intel"] = intel
        enriched["news_policy"] = "catalog_only_not_scored"
        return enriched

    head = await asyncio.gather(*(enrich_one(rec) for rec in recommendations[:limit]))
    tail = [
        dict(
            rec,
            ta_score=rec.get("score", 0),
            intel_score=0,
            final_score=rec.get("score", 0),
            news_policy="catalog_only_not_scored",
        )
        for rec in recommendations[limit:]
    ]
    # Preserve original TA ranking. News/catalog data must not reorder picks.
    return head + tail
