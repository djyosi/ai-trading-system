import re
from collections import Counter


class InsiderActivityProvider:
    provider_name = "insider_activity"
    source_name = "SEC Form 4"

    def normalize_transactions(self, rows):
        events = [self.normalize_transaction(row) for row in rows]
        purchase_counts = Counter(
            event["ticker"]
            for event in events
            if event["transaction_type"] == "purchase" and "director" in event["insider_role"]
        )
        cluster_tickers = {ticker for ticker, count in purchase_counts.items() if count >= 2}
        for event in events:
            if event["ticker"] in cluster_tickers and event["transaction_type"] == "purchase":
                event["catalyst_type"] = "insider_cluster_buying"
                event["signal"] = "bullish"
                event["strength"] = "strong"
        return events

    def normalize_transaction(self, row):
        transaction_code = str(row.get("transaction_code") or "").upper().strip()
        transaction_type = self.classify_transaction_code(transaction_code)
        role = self.classify_role(row.get("title"))
        shares = self._parse_number(row.get("shares"))
        price = self._parse_number(row.get("price"))
        value = None if shares is None or price is None else shares * price
        is_option_related = self._is_option_related(row)
        catalyst_type, signal, strength = self.classify_catalyst(
            role=role,
            transaction_type=transaction_type,
            value=value,
            is_option_related=is_option_related,
        )

        return {
            "provider": self.provider_name,
            "source": self.source_name,
            "ticker": row.get("ticker"),
            "company_name": row.get("company_name"),
            "insider_name": row.get("insider_name"),
            "title": row.get("title"),
            "insider_role": role,
            "transaction_code": transaction_code,
            "transaction_type": transaction_type,
            "shares": shares,
            "price": price,
            "value": value,
            "owned": self._parse_number(row.get("owned")),
            "ownership_change_percent": self._parse_number(row.get("ownership_change_percent")),
            "filing_date": row.get("filing_date"),
            "trade_date": row.get("trade_date"),
            "catalyst_type": catalyst_type,
            "signal": signal,
            "strength": strength,
            "is_option_related": is_option_related,
            "source_url": row.get("source_url"),
            "raw": row,
        }

    def classify_transaction_code(self, code):
        normalized = str(code or "").upper().strip()
        mapping = {
            "P": "purchase",
            "S": "sale",
            "M": "option_exercise",
            "F": "tax_withholding",
            "G": "gift",
            "A": "grant_or_award",
        }
        return mapping.get(normalized, "other")

    def classify_role(self, title):
        normalized = str(title or "").lower()
        is_director = "dir" in normalized or "director" in normalized
        is_ten_percent = "10%" in normalized or "10 percent" in normalized
        officer_tokens = ["ceo", "cfo", "coo", "cto", "pres", "president", "officer", "chief"]
        is_officer = any(token in normalized for token in officer_tokens)

        if is_director and is_ten_percent:
            return "director_10_percent_owner"
        if is_director:
            return "director"
        if is_officer:
            return "officer"
        if is_ten_percent:
            return "10_percent_owner"
        return "other"

    def classify_catalyst(self, role, transaction_type, value, is_option_related):
        abs_value = abs(value or 0)
        if transaction_type == "purchase" and "director" in role:
            strength = "strong" if abs_value >= 100000 else "medium"
            return "insider_director_purchase", "bullish", strength
        if transaction_type == "purchase" and role == "officer":
            strength = "strong" if abs_value >= 100000 else "medium"
            return "insider_officer_purchase", "bullish", strength
        if transaction_type == "sale" and is_option_related:
            return "insider_option_related_sale", "neutral", "weak"
        if transaction_type == "sale":
            strength = "strong" if abs_value >= 1000000 else "medium"
            return "insider_large_sale", "bearish", strength
        return "insider_other", "neutral", "weak"

    def _is_option_related(self, row):
        trade_type = str(row.get("trade_type") or "").lower()
        transaction_code = str(row.get("transaction_code") or "").upper().strip()
        return "+oe" in trade_type or "option" in trade_type or transaction_code == "M"

    def _parse_number(self, value):
        if value is None or value == "":
            return None
        if isinstance(value, (int, float)):
            return value
        text = str(value).replace(",", "").strip()
        text = text.replace("$", "").replace("%", "")
        match = re.search(r"[-+]?\d+(?:\.\d+)?", text)
        if not match:
            return None
        number = float(match.group(0))
        return int(number) if number.is_integer() else number
