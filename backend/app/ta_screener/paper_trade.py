"""Paper trade outcome tracking — check if TA recommendations worked."""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from httpx import AsyncClient

from app.core.config import settings

REPO_ROOT = Path(__file__).resolve().parents[3]
SCANS_DIR = REPO_ROOT / "runtime" / "ta-scans"
OUTCOMES_DIR = REPO_ROOT / "runtime" / "ta-outcomes"


async def track_outcomes():
    """Read latest TA scan, check today's prices for top recommendations."""
    if not SCANS_DIR.exists():
        return {"status": "no_scans"}

    scans = sorted(SCANS_DIR.glob("scan-*.json"))
    if len(scans) < 2:
        return {"status": "need_second_scan", "message": "Need at least 2 scans to compare"}

    yesterday = json.loads(scans[-2].read_text())
    today = json.loads(scans[-1].read_text())

    api_key = settings.massive_api_key
    if not api_key:
        return {"error": "no_api_key"}

    results = []
    async with AsyncClient(base_url=settings.massive_base_url, timeout=30) as client:
        for rec in yesterday["top_recommendations"][:10]:
            ticker = rec["ticker"]
            yest_score = rec["score"]
            try:
                end = datetime.now(timezone.utc).date().isoformat()
                start = (datetime.now(timezone.utc).date() - timedelta(days=30)).isoformat()
                resp = await client.get(
                    f"/v2/aggs/ticker/{ticker}/range/1/day/{start}/{end}",
                    params={"adjusted": "true", "sort": "asc", "limit": 50000, "apiKey": api_key},
                )
                if resp.status_code != 200:
                    continue
                raw = resp.json().get("results", [])
                if not raw:
                    continue

                rec_date = yesterday["scan_date"]
                rec_price = raw[-2]["c"] if len(raw) >= 2 else None  # price when recommended
                today_price = raw[-1]["c"]  # latest price

                change_pct = round((today_price - rec_price) / rec_price * 100, 2) if rec_price else None
                hit_target = change_pct >= 3.0 if change_pct else False  # 3% gain = target hit
                hit_stop = change_pct <= -2.0 if change_pct else False  # 2% loss = stop hit

                results.append({
                    "ticker": ticker,
                    "score": yest_score,
                    "rec_date": rec_date,
                    "rec_price": rec_price,
                    "current_price": today_price,
                    "change_pct": change_pct,
                    "hit_target": hit_target,
                    "hit_stop": hit_stop,
                    "status": "win" if hit_target else ("loss" if hit_stop else "open"),
                })
            except Exception:
                continue

    # Save outcomes
    OUTCOMES_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTCOMES_DIR / f"outcome-{today['scan_date']}.json"
    outcome = {"scan_date": today["scan_date"], "compare_date": yesterday["scan_date"], "results": results}
    out_path.write_text(json.dumps(outcome, indent=2))

    return outcome
