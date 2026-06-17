from app.features.sectors import get_sector, SECTOR_PRESETS


def test_known_ticker_maps_to_sector():
    sector = get_sector("AAPL")
    assert sector == "technology"


def test_known_ticker_case_insensitive():
    sector = get_sector("aapl")
    assert sector == "technology"


def test_jpm_is_financial():
    sector = get_sector("JPM")
    assert sector == "financials"


def test_unh_is_healthcare():
    sector = get_sector("UNH")
    assert sector == "healthcare"


def test_unknown_ticker_returns_unknown():
    sector = get_sector("ABCDEF")
    assert sector == "unknown"


def test_sector_presets_contain_major_sectors():
    major_sectors = {"technology", "healthcare", "financials", "utilities", "energy", "consumer_cyclical"}
    for sector_name in major_sectors:
        assert sector_name in SECTOR_PRESETS, f"Missing sector preset: {sector_name}"
        assert len(SECTOR_PRESETS[sector_name]) > 0, f"Empty sector preset: {sector_name}"


def test_sector_presets_have_known_tickers():
    assert "AAPL" in SECTOR_PRESETS["technology"]
    assert "JPM" in SECTOR_PRESETS["financials"]
    assert "UNH" in SECTOR_PRESETS["healthcare"]
    assert "DUK" in SECTOR_PRESETS["utilities"]
    assert "CVX" in SECTOR_PRESETS["energy"]


def test_sector_presets_maps_all_liquid_research_tickers():
    """Verify no ticker falls through the cracks."""
    from app.universe.presets import resolve_universe_preset

    tickers = resolve_universe_preset("liquid_research_100")
    unknown = [t for t in tickers if get_sector(t) == "unknown"]
    assert len(unknown) == 0, f"Missing sector mapping for: {unknown[:10]}"
