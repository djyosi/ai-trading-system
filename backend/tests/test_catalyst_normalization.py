from app.catalysts.normalization import normalize_catalyst_event


def test_insider_activity_event_normalizes_to_common_catalyst_shape():
    raw_event = {
        "provider": "insider_activity",
        "source": "SEC Form 4",
        "ticker": "PAX",
        "company_name": "Patria Investments Ltd",
        "insider_name": "Neto Olimpio Matarazzo",
        "title": "Dir",
        "catalyst_type": "insider_director_purchase",
        "signal": "bullish",
        "strength": "strong",
        "value": 1129000.0,
        "filing_date": "2026-06-05",
        "trade_date": "2026-06-03",
        "source_url": "https://www.sec.gov/Archives/example",
    }

    catalyst = normalize_catalyst_event(raw_event)

    assert catalyst == {
        "ticker": "PAX",
        "provider": "insider_activity",
        "source": "SEC Form 4",
        "catalyst_type": "insider_director_purchase",
        "signal": "bullish",
        "strength": "strong",
        "event_date": "2026-06-03",
        "filing_date": "2026-06-05",
        "summary": "Director Neto Olimpio Matarazzo reported an insider director purchase worth $1,129,000.",
        "source_url": "https://www.sec.gov/Archives/example",
        "raw": raw_event,
    }


def test_sale_catalyst_summary_uses_sale_language():
    raw_event = {
        "provider": "insider_activity",
        "source": "SEC Form 4",
        "ticker": "DDOG",
        "insider_name": "Ittycheria Dev",
        "title": "Dir",
        "catalyst_type": "insider_option_related_sale",
        "signal": "neutral",
        "strength": "weak",
        "value": -34331640.0,
        "filing_date": "2026-06-05",
        "trade_date": "2026-06-03",
    }

    catalyst = normalize_catalyst_event(raw_event)

    assert catalyst["summary"] == "Director Ittycheria Dev reported an insider option related sale worth $34,331,640."
    assert catalyst["event_date"] == "2026-06-03"
