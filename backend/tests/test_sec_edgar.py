import httpx
import pytest

from app.providers.sec_edgar import SecEdgarProvider


@pytest.mark.asyncio
async def test_sec_edgar_requires_user_agent():
    provider = SecEdgarProvider(user_agent="")

    with pytest.raises(ValueError, match="user_agent"):
        await provider.get_company_submissions("0000320193")


@pytest.mark.asyncio
async def test_sec_edgar_normalizes_company_filings():
    async def handler(request):
        assert request.headers["User-Agent"] == "ai-trading-system test@example.com"
        return httpx.Response(
            200,
            json={
                "cik": "0000320193",
                "name": "Apple Inc.",
                "filings": {
                    "recent": {
                        "accessionNumber": ["0000320193-24-000001", "0000320193-24-000002"],
                        "filingDate": ["2024-01-01", "2024-01-02"],
                        "reportDate": ["2023-12-31", "2024-01-01"],
                        "form": ["8-K", "10-Q"],
                        "primaryDocument": ["aapl-8k.htm", "aapl-10q.htm"],
                        "primaryDocDescription": ["Current report", "Quarterly report"],
                    }
                },
            },
        )

    provider = SecEdgarProvider(
        user_agent="ai-trading-system test@example.com",
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://data.sec.gov"),
    )

    filings = await provider.get_company_submissions("0000320193")

    assert filings[0] == {
        "provider": "sec_edgar",
        "cik": "0000320193",
        "company_name": "Apple Inc.",
        "accession_number": "0000320193-24-000001",
        "filing_date": "2024-01-01",
        "report_date": "2023-12-31",
        "form": "8-K",
        "primary_document": "aapl-8k.htm",
        "description": "Current report",
        "catalyst_type": "sec_filing_8k",
        "raw": {
            "accessionNumber": "0000320193-24-000001",
            "filingDate": "2024-01-01",
            "reportDate": "2023-12-31",
            "form": "8-K",
            "primaryDocument": "aapl-8k.htm",
            "primaryDocDescription": "Current report",
        },
    }
    assert filings[1]["catalyst_type"] == "sec_filing_quarterly_report"

    await provider.aclose()


def test_sec_edgar_classifies_known_forms():
    provider = SecEdgarProvider(user_agent="ai-trading-system test@example.com")

    assert provider.classify_form("8-K") == "sec_filing_8k"
    assert provider.classify_form("10-Q") == "sec_filing_quarterly_report"
    assert provider.classify_form("10-K") == "sec_filing_annual_report"
    assert provider.classify_form("S-1") == "sec_filing_registration"
    assert provider.classify_form("SC 13G") == "sec_filing_ownership"
    assert provider.classify_form("UNKNOWN") == "sec_filing_other"
