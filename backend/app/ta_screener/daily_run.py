"""
Daily stock screener — scans all tickers, ranks matches, saves results.

Run: python -m app.ta_screener.daily_run
"""

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

from httpx import AsyncClient

from app.core.config import settings
from app.ta_screener import SCREENS
from app.ta_screener.indicators import compute_indicators, check_screen
from app.ta_screener.portfolio import add_trades_from_scan, update_open_trades
from app.features.sectors import get_sector

REPO_ROOT = Path(__file__).resolve().parents[3]
OUTPUT_DIR = REPO_ROOT / "runtime" / "ta-scans"


async def run_daily_scan():
    """Scan all tickers, rank results, save to file."""

    # Load tickers
    tickers_file = REPO_ROOT / "backend" / "tmp" / "research_tickers.json"
    # If not available, build from sector map
    if not tickers_file.exists():
        from app.features.sectors import _SECTOR_MAP
        from app.universe.presets import resolve_universe_preset
        all_t = set(k for k in _SECTOR_MAP if k not in ('THIN','CHEAP','FAIL'))
        for p in ['liquid_research_25','liquid_research_50','liquid_research_100','liquid_research_500']:
            all_t.update(resolve_universe_preset(p))
        tickers = sorted(all_t)
    else:
        tickers = json.loads(tickers_file.read_text())

    print(f"Scanning {len(tickers)} tickers across {len(SCREENS)} screens...")
    api_key = settings.massive_api_key
    scan_date = datetime.now(timezone.utc).date().isoformat()
    matches = {s: [] for s in SCREENS}
    ticker_scores = {}  # ticker -> list of (screen, rank)

    async with AsyncClient(base_url=settings.massive_base_url, timeout=30) as client:
        for idx, ticker in enumerate(tickers):
            try:
                end = datetime.now(timezone.utc).date().isoformat()
                # Fetch ~9 months for SMA 200
                resp = await client.get(
                    f"/v2/aggs/ticker/{ticker}/range/1/day/2025-09-01/{end}",
                    params={"adjusted": "true", "sort": "asc", "limit": 50000, "apiKey": api_key},
                )
                if resp.status_code != 200:
                    continue
                raw = resp.json().get("results", [])
                if len(raw) < 25:
                    continue

                candles = [
                    {"timestamp_ms": r["t"], "open": r["o"], "high": r["h"],
                     "low": r["l"], "close": r["c"], "volume": r["v"]}
                    for r in raw
                ]
                indicators = compute_indicators(candles)
                if indicators.get("error"):
                    continue

                # Check each screen
                for screen_name in SCREENS:
                    if check_screen(indicators, screen_name):
                        matches[screen_name].append(ticker)
                        ticker_scores.setdefault(ticker, []).append(screen_name)

            except Exception:
                continue

            if (idx + 1) % 100 == 0:
                total = sum(len(v) for v in matches.values())
                print(f"  {idx+1}/{len(tickers)}... ({total} matches)")

    # Rank tickers by number of screen matches
    ranked = sorted(ticker_scores.items(), key=lambda x: (-len(x[1]), x[0]))
    recommendations = [
        {
            "ticker": ticker,
            "sector": get_sector(ticker),
            "score": len(screens),
            "screens": screens,
        }
        for ticker, screens in ranked
    ]

    # Build output
    result = {
        "scan_date": scan_date,
        "tickers_scanned": len(tickers),
        "tickers_matched": len(ticker_scores),
        "total_matches": sum(len(v) for v in matches.values()),
        "screens": {name: {"description": SCREENS[name]["description"], "matches": tickers}
                     for name, tickers in matches.items()},
        "top_recommendations": recommendations[:50],  # Top 50
        "full_count_by_screen": {name: len(m) for name, m in matches.items()},
    }

    # Save
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"scan-{scan_date}.json"
    out_path.write_text(json.dumps(result, indent=2, sort_keys=True))
    print(f"\nResults saved to {out_path}")
    print(f"Tickers matched: {len(ticker_scores)}")
    print(f"Total matches: {result['total_matches']}")

    # Save trades from top recommendations
    trades_added = add_trades_from_scan(result)
    print(f"Trades added: {trades_added}")

    # Update existing open trades
    summary = await update_open_trades()
    print(f"Portfolio: {summary['open']} open, {summary['closed']} closed ({summary['wins']}W/{summary['losses']}L)")

    # Print top 10
    print(f"\n{'='*60}")
    print(f"TOP RECOMMENDATIONS — {scan_date}")
    print(f"{'='*60}")
    for rec in recommendations[:10]:
        print(f"  {rec['ticker']:6s} ({rec['sector']:15s}) score={rec['score']} → {', '.join(rec['screens'][:3])}")

    return result


def main():
    asyncio.run(run_daily_scan())


if __name__ == "__main__":
    main()
