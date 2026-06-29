"""Execute IBKR paper trades from latest TA scan results."""
import json
from pathlib import Path

from app.ibkr.bridge import place_top_picks, IBKRBridge

REPO_ROOT = Path(__file__).resolve().parents[3]
SCANS_DIR = REPO_ROOT / "runtime" / "ta-scans"


def run():
    """Read latest TA scan, place paper trades for top picks via IBKR."""
    scans = sorted(SCANS_DIR.glob("scan-*.json"))
    if not scans:
        print("No scans found")
        return

    latest = json.loads(scans[-1].read_text())
    top = latest["top_recommendations"][:10]

    # Check IBKR for existing positions first
    bridge = IBKRBridge()
    if not bridge.connect():
        print("TWS offline, skipping IBKR execution")
        return
    existing = {p["ticker"] for p in bridge.get_positions()}
    bridge.disconnect()

    # Filter out already-held tickers
    new_picks = [r for r in top if r["ticker"] not in existing]

    print(f"Scan: {latest['scan_date']}")
    print(f"Top picks: {len(top)}")
    print(f"Already held: {len(top) - len(new_picks)}")
    print(f"New entries: {len(new_picks)}")
    for r in new_picks[:5]:
        print(f"  {r['ticker']:6s} score={r['score']}")

    if not new_picks:
        print("No new entries to execute")
        return

    result = place_top_picks(new_picks[:5], position_size=10000)
    print(f"\nResult: {result.get('status')}")
    if result.get("account"):
        print(f"Cash: ${result['account'].get('TotalCashValue',0):,.2f}")
    for o in result.get("orders", []):
        if o.get("error"):
            print(f"  ❌ {o['ticker']}: {o['error']}")
        elif o.get("action") == "skip":
            print(f"  ⏭️ {o['ticker']}: {o.get('reason','')}")
        else:
            fill = o.get("avg_fill") or "market"
            print(f"  ✅ {o['ticker']}: BUY {o['quantity']} @ ${fill}")


if __name__ == "__main__":
    run()
