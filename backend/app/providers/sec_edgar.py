import httpx


class SecEdgarProvider:
    provider_name = "sec_edgar"

    def __init__(self, user_agent=None, client=None):
        self.user_agent = "ai-trading-system local-development" if user_agent is None else user_agent
        self.client = client or httpx.AsyncClient(base_url="https://data.sec.gov", timeout=30)

    async def aclose(self):
        await self.client.aclose()

    async def get_company_submissions(self, cik):
        if not self.user_agent:
            raise ValueError("user_agent is required for SEC EDGAR requests")

        normalized_cik = str(cik).zfill(10)
        response = await self.client.get(
            f"/submissions/CIK{normalized_cik}.json",
            headers={"User-Agent": self.user_agent},
        )
        response.raise_for_status()
        return self._normalize_submissions(response.json())

    def _normalize_submissions(self, payload):
        recent = (payload.get("filings") or {}).get("recent") or {}
        accession_numbers = recent.get("accessionNumber") or []
        rows = []
        for index, accession_number in enumerate(accession_numbers):
            raw = {
                "accessionNumber": accession_number,
                "filingDate": self._get_list_value(recent, "filingDate", index),
                "reportDate": self._get_list_value(recent, "reportDate", index),
                "form": self._get_list_value(recent, "form", index),
                "primaryDocument": self._get_list_value(recent, "primaryDocument", index),
                "primaryDocDescription": self._get_list_value(recent, "primaryDocDescription", index),
            }
            form = raw["form"]
            rows.append(
                {
                    "provider": self.provider_name,
                    "cik": payload.get("cik"),
                    "company_name": payload.get("name"),
                    "accession_number": accession_number,
                    "filing_date": raw["filingDate"],
                    "report_date": raw["reportDate"],
                    "form": form,
                    "primary_document": raw["primaryDocument"],
                    "description": raw["primaryDocDescription"],
                    "catalyst_type": self.classify_form(form),
                    "raw": raw,
                }
            )
        return rows

    def classify_form(self, form):
        normalized = str(form or "").upper().strip()
        if normalized == "8-K":
            return "sec_filing_8k"
        if normalized == "10-Q":
            return "sec_filing_quarterly_report"
        if normalized == "10-K":
            return "sec_filing_annual_report"
        if normalized.startswith("S-1"):
            return "sec_filing_registration"
        if "13G" in normalized or "13D" in normalized:
            return "sec_filing_ownership"
        return "sec_filing_other"

    def _get_list_value(self, mapping, key, index):
        values = mapping.get(key) or []
        if index >= len(values):
            return None
        return values[index]
