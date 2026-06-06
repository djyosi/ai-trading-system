from app.providers.insider_activity import InsiderActivityProvider


def test_director_open_market_purchase_is_strong_bullish_catalyst():
    provider = InsiderActivityProvider()
    row = {
        "ticker": "PAX",
        "company_name": "Patria Investments Ltd",
        "insider_name": "Neto Olimpio Matarazzo",
        "title": "Dir",
        "transaction_code": "P",
        "trade_type": "P - Purchase",
        "price": 11.29,
        "shares": 100000,
        "owned": 660724,
        "ownership_change_percent": 18,
        "filing_date": "2026-06-05",
        "trade_date": "2026-06-03",
        "source_url": "https://www.sec.gov/Archives/example",
    }

    event = provider.normalize_transaction(row)

    assert event == {
        "provider": "insider_activity",
        "source": "SEC Form 4",
        "ticker": "PAX",
        "company_name": "Patria Investments Ltd",
        "insider_name": "Neto Olimpio Matarazzo",
        "title": "Dir",
        "insider_role": "director",
        "transaction_code": "P",
        "transaction_type": "purchase",
        "shares": 100000,
        "price": 11.29,
        "value": 1129000.0,
        "owned": 660724,
        "ownership_change_percent": 18.0,
        "filing_date": "2026-06-05",
        "trade_date": "2026-06-03",
        "catalyst_type": "insider_director_purchase",
        "signal": "bullish",
        "strength": "strong",
        "is_option_related": False,
        "source_url": "https://www.sec.gov/Archives/example",
        "raw": row,
    }


def test_director_sale_with_option_exercise_is_discounted():
    provider = InsiderActivityProvider()
    row = {
        "ticker": "DDOG",
        "company_name": "Datadog, Inc.",
        "insider_name": "Ittycheria Dev",
        "title": "Dir",
        "transaction_code": "S",
        "trade_type": "S - Sale+OE",
        "price": "$248.78",
        "shares": "-138,000",
        "owned": "1,000,000",
        "ownership_change_percent": "-12%",
        "filing_date": "2026-06-05",
        "trade_date": "2026-06-03",
    }

    event = provider.normalize_transaction(row)

    assert event["transaction_type"] == "sale"
    assert event["value"] == -34331640.0
    assert event["catalyst_type"] == "insider_option_related_sale"
    assert event["signal"] == "neutral"
    assert event["strength"] == "weak"
    assert event["is_option_related"] is True


def test_multiple_director_purchases_are_cluster_buying():
    provider = InsiderActivityProvider()
    rows = [
        {
            "ticker": "ABC",
            "company_name": "ABC Corp",
            "insider_name": "Director One",
            "title": "Dir",
            "transaction_code": "P",
            "price": 10,
            "shares": 20000,
            "filing_date": "2026-06-05",
            "trade_date": "2026-06-04",
        },
        {
            "ticker": "ABC",
            "company_name": "ABC Corp",
            "insider_name": "Director Two",
            "title": "Director",
            "transaction_code": "P",
            "price": 11,
            "shares": 15000,
            "filing_date": "2026-06-05",
            "trade_date": "2026-06-04",
        },
    ]

    events = provider.normalize_transactions(rows)

    assert len(events) == 2
    assert all(event["catalyst_type"] == "insider_cluster_buying" for event in events)
    assert all(event["strength"] == "strong" for event in events)


def test_transaction_code_classifier_handles_common_form4_codes():
    provider = InsiderActivityProvider()

    assert provider.classify_transaction_code("P") == "purchase"
    assert provider.classify_transaction_code("S") == "sale"
    assert provider.classify_transaction_code("M") == "option_exercise"
    assert provider.classify_transaction_code("F") == "tax_withholding"
    assert provider.classify_transaction_code("G") == "gift"
    assert provider.classify_transaction_code("A") == "grant_or_award"
    assert provider.classify_transaction_code("X") == "other"


def test_role_classifier_detects_director_officer_and_ten_percent_owner():
    provider = InsiderActivityProvider()

    assert provider.classify_role("Dir") == "director"
    assert provider.classify_role("CEO, Pres") == "officer"
    assert provider.classify_role("Dir, 10%") == "director_10_percent_owner"
    assert provider.classify_role("10%") == "10_percent_owner"
    assert provider.classify_role("See remarks") == "other"
