from app.universe.presets import resolve_universe_preset


def test_liquid_research_presets_include_larger_broad_universes():
    liquid_250 = resolve_universe_preset("liquid_research_250")
    liquid_500 = resolve_universe_preset("liquid_research_500")

    assert len(liquid_250) == 250
    assert len(set(liquid_250)) == 250
    assert liquid_250[:5] == ["AAPL", "MSFT", "NVDA", "TSLA", "AMD"]

    assert len(liquid_500) == 500
    assert len(set(liquid_500)) == 500
    assert liquid_500[:5] == ["AAPL", "MSFT", "NVDA", "TSLA", "AMD"]
    assert liquid_500[:250] == liquid_250
