def normalize_catalyst_event(event):
    return {
        "ticker": event.get("ticker"),
        "provider": event.get("provider"),
        "source": event.get("source"),
        "catalyst_type": event.get("catalyst_type"),
        "signal": event.get("signal"),
        "strength": event.get("strength"),
        "event_date": event.get("trade_date") or event.get("event_date"),
        "filing_date": event.get("filing_date"),
        "summary": _summarize_event(event),
        "source_url": event.get("source_url"),
        "raw": event,
    }


def _summarize_event(event):
    role = _humanize_role(event.get("title"))
    insider_name = event.get("insider_name") or "an insider"
    catalyst_label = str(event.get("catalyst_type") or "insider activity").replace("_", " ")
    value = abs(float(event.get("value") or 0))
    return "{role} {name} reported an {label} worth ${value:,.0f}.".format(
        role=role,
        name=insider_name,
        label=catalyst_label,
        value=value,
    )


def _humanize_role(title):
    normalized = str(title or "").lower()
    if "dir" in normalized or "director" in normalized:
        return "Director"
    if "ceo" in normalized:
        return "CEO"
    if "cfo" in normalized:
        return "CFO"
    if "pres" in normalized:
        return "President"
    return "Insider"
