"""IBKR Paper Trading Bridge — connect to TWS, place orders, track positions.

Synchronous API (ib_insync uses its own event loop under the hood).
"""

from pathlib import Path

from ib_insync import IB, Stock, MarketOrder

REPO_ROOT = Path(__file__).resolve().parents[2]
TRADES_FILE = REPO_ROOT / "runtime" / "ta-trades" / "trades.json"

TWS_HOST = "127.0.0.1"
TWS_PORT = 7497  # paper
CLIENT_ID = 100


class IBKRBridge:
    """Synchronous bridge to Interactive Brokers paper trading."""

    def __init__(self):
        self.ib = IB()
        self.connected = False
        self.account = None

    def connect(self):
        try:
            self.ib.connect(TWS_HOST, TWS_PORT, clientId=CLIENT_ID)
            accounts = self.ib.managedAccounts()
            if accounts:
                self.account = accounts[0]
                self.connected = True
                return True
            return False
        except Exception as e:
            print(f"  ⚠️ IBKR connect failed: {e}")
            self.connected = False
            return False

    def disconnect(self):
        if self.connected:
            self.ib.disconnect()
            self.connected = False

    def place_market_order(self, ticker, quantity, action="BUY"):
        if not self.connected:
            return {"error": "not_connected"}
        try:
            contract = Stock(ticker, "SMART", "USD")
            order = MarketOrder(action, int(quantity))
            trade = self.ib.placeOrder(contract, order)
            self.ib.sleep(1)  # wait for fill
            fill = trade.fills[0] if trade.fills else None
            return {
                "order_id": trade.order.orderId,
                "ticker": ticker,
                "action": action,
                "quantity": quantity,
                "status": str(trade.orderStatus.status),
                "filled": trade.orderStatus.filled,
                "avg_fill": round(fill.execution.avgPrice, 2) if fill else None,
            }
        except Exception as e:
            return {"error": str(e), "ticker": ticker}

    def get_positions(self):
        if not self.connected:
            return []
        try:
            positions = self.ib.positions()
            return [
                {
                    "ticker": p.contract.symbol,
                    "shares": p.position,
                    "avg_cost": round(p.avgCost, 2),
                }
                for p in positions
            ]
        except Exception:
            return []

    def get_account_summary(self):
        if not self.connected:
            return {}
        try:
            summary = self.ib.accountSummary()
            result = {}
            for item in summary:
                if item.tag in ("TotalCashValue", "NetLiquidation", "GrossPositionValue", "BuyingPower"):
                    result[item.tag] = float(item.value)
            return result
        except Exception:
            return {}

    def market_snapshot(self):
        """Quick one-shot: connect, get summary, positions, disconnect."""
        if not self.connect():
            return {"status": "offline"}
        try:
            acc = self.get_account_summary()
            pos = self.get_positions()
            return {"status": "ok", "account": acc, "positions": pos}
        finally:
            self.disconnect()


def place_top_picks(recommendations, position_size=2000):
    """Place paper trades for top TA recommendations. Returns results dict."""
    bridge = IBKRBridge()
    if not bridge.connect():
        return {"status": "tws_offline", "message": "TWS not running"}

    try:
        existing = {p["ticker"] for p in bridge.get_positions()}
        acc = bridge.get_account_summary()
        cash = acc.get("TotalCashValue", 0)
        orders = []

        for rec in recommendations[:10]:
            ticker = rec["ticker"]
            if ticker in existing:
                orders.append({"ticker": ticker, "action": "skip", "reason": "already_held"})
                continue

            price = rec.get("close") or 50
            if not price or price <= 0:
                orders.append({"ticker": ticker, "action": "skip", "reason": "no_price"})
                continue

            quantity = max(1, int(position_size / price))
            cost = quantity * price
            if cash < cost * 1.2:
                orders.append({"ticker": ticker, "action": "skip", "reason": "insufficient_cash"})
                continue

            order = bridge.place_market_order(ticker, quantity, "BUY")
            orders.append(order)
            if order.get("avg_fill"):
                cash -= quantity * order["avg_fill"]

        return {"status": "ok", "account": acc, "orders": orders}
    finally:
        bridge.disconnect()
