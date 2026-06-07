LIQUID_RESEARCH_25 = [
    "AAPL",
    "MSFT",
    "NVDA",
    "TSLA",
    "AMD",
    "META",
    "AMZN",
    "GOOGL",
    "NFLX",
    "AVGO",
    "SMCI",
    "COIN",
    "PLTR",
    "MU",
    "QQQ",
    "SPY",
    "IWM",
    "JPM",
    "LLY",
    "UNH",
    "COST",
    "CRM",
    "ORCL",
    "BAC",
    "XOM",
]

UNIVERSE_PRESETS = {
    "liquid_research_25": LIQUID_RESEARCH_25,
}


def resolve_universe_preset(name):
    if name not in UNIVERSE_PRESETS:
        allowed = ", ".join(sorted(UNIVERSE_PRESETS))
        raise ValueError(f"Unknown universe preset '{name}'. Available presets: {allowed}")
    return list(UNIVERSE_PRESETS[name])
