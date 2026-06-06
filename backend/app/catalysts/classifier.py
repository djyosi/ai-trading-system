CATALYST_RULES = {
    "insider_director_purchase": ("bullish", "strong", 90),
    "insider_officer_purchase": ("bullish", "strong", 85),
    "insider_cluster_buying": ("bullish", "strong", 95),
    "insider_large_sale": ("bearish", "medium", 35),
    "insider_option_related_sale": ("neutral", "weak", 10),
    "earnings_beat": ("bullish", "medium", 75),
    "guidance_raise": ("bullish", "strong", 85),
    "guidance_cut": ("bearish", "strong", 20),
    "analyst_upgrade": ("bullish", "medium", 60),
    "analyst_downgrade": ("bearish", "medium", 25),
    "fda_approval": ("bullish", "strong", 90),
    "fda_clinical": ("bullish", "medium", 70),
    "merger_acquisition": ("bullish", "strong", 80),
    "contract_win": ("bullish", "medium", 65),
    "sec_filing_8k": ("neutral", "medium", 40),
}


def classify_catalyst(catalyst):
    catalyst_type = catalyst.get("catalyst_type") or "unknown"
    signal, strength, score = CATALYST_RULES.get(catalyst_type, ("neutral", "weak", 0))
    return {
        "catalyst_type": catalyst_type,
        "signal": catalyst.get("signal") or signal,
        "strength": catalyst.get("strength") or strength,
        "score": score,
    }


def calculate_freshness(age_minutes):
    if age_minutes <= 60:
        return "fresh"
    if age_minutes <= 390:
        return "same_day"
    return "stale"
