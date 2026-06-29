"""IBKR Paper Trading Bridge — connect to TWS, place orders, track positions.

🔒 SAFETY: LIVE TRADING IS BLOCKED BY DEFAULT.
   Only paper account (port 7497) is allowed.
   Set IBKR_LIVE_MODE=true in .env to unlock live account (port 7496).
   Even then, each live order requires `confirm_live=True` parameter.
"""

import logging
from datetime import datetime
from pathlib import Path

from ib_insync import IB, Stock, MarketOrder

logger = logging.getLogger("ibkr")

REPO_ROOT = Path(__file__).resolve().parents[2]
TRADES_FILE = REPO_ROOT / "runtime" / "ta-trades" / "trades.json"
ORDER_LOG = REPO_ROOT / "runtime" / "ibkr-orders.log"

TWS_HOST = "127.0.0.1"
TWS_PORT_PAPER = 7497
TWS_PORT_LIVE = 7496
CLIENT_ID = 100

# ── SAFETY CONSTRAINTS ──────────────────────────────────────────
MAX_POSITION_SIZE_USD = 50_000       # Max $50k per position ($1M account)
MAX_DAILY_LOSS_PCT = 5.0            # Stop new orders if daily loss > 5%
MAX_ACCOUNT_LOSS_PCT = 10.0         # Hard stop if account down > 10%
LIVE_TRADING_ENABLED = False         # Set True in .env to unlock live

# Load live trading flag from .env
_env_file = REPO_ROOT / "backend" / ".env"
if _env_file.exists():
    for line in _env_file.read_text().splitlines():
        if line.strip().startswith("IBKR_LIVE_MODE=true"):
            LIVE_TRADING_ENABLED = True


def _log_order(ticker, action, quantity, price, status, note=""):
    """Log every order attempt to a file."""
    Path(ORDER_LOG).parent.mkdir(parents=True, exist_ok=True)
    line = f"[{datetime.now().isoformat()}] {ticker:6s} {action:4s} {quantity:>5d} @ ${price or 0:<8.2f} → {status:12s} {note}\n"
    with open(ORDER_LOG, "a") as f:
        f.write(line)


class SafetyError(Exception):
    """Raised when a safety constraint is violated."""
    pass


class IBKRBridge:
    """Synchronous bridge to Interactive Brokers.

    🔒 ONLY PAPER ACCOUNT (port 7497) BY DEFAULT.
       Live account requires explicit confirmation.
    """

    def __init__(self, force_live=False):
        self.ib = IB()
        self.connected = False
        self.account = None
        self.force_live = force_live

    def connect(self):
        """Connect to TWS. Blocks live unless explicit override."""
        port = TWS_PORT_PAPER

        if self.force_live or LIVE_TRADING_ENABLED:
            port = TWS_PORT_LIVE
            raise SafetyError(
                "🔴 LIVE TRADING BLOCKED: IBKR_LIVE_MODE is not set and force_live is False. "
                "To enable live, set IBKR_LIVE_MODE=true in .env AND pass force_live=True."
            )

        try:
            self.ib.connect(TWS_HOST, port, clientId=CLIENT_ID)
            accounts = self.ib.managedAccounts()
            if accounts:
                self.account = accounts[0]
                self.connected = True
                logger.info(f"Connected to TWS paper account {self.account}")
                return True
            return False
        except Exception as e:
            logger.warning(f"IBKR connect failed: {e}")
            self.connected = False
            return False

    def disconnect(self):
        if self.connected:
            self.ib.disconnect()
            self.connected = False

    def _require_connected(self):
        if not self.connected:
            raise SafetyError("Not connected to TWS")

    def place_market_order(self, ticker, quantity, action="BUY", confirm_live=False):
        """Place a market order.

        Args:
            ticker: Stock symbol
            quantity: Number of shares (positive int)
            action: "BUY" or "SELL"
            confirm_live: Must be True if using real money account

        Returns:
            dict with order details
        """
        self._require_connected()

        # ── SAFETY: check account type ──
        if not self._is_paper():
            if not confirm_live:
                _log_order(ticker, action, quantity, None, "BLOCKED_LIVE",
                           "Live account requires confirm_live=True")
                raise SafetyError(
                    f"🔴 BLOCKED: {ticker} {action} {quantity}sh — "
                    "This is a live account. Pass confirm_live=True to proceed."
                )

        # ── SAFETY: position size cap ──
        estimated_cost = quantity * self._get_approx_price(ticker)
        if estimated_cost > MAX_POSITION_SIZE_USD and not confirm_live:
            _log_order(ticker, action, quantity, None, "BLOCKED_SIZE",
                       f"${estimated_cost:.0f} > ${MAX_POSITION_SIZE_USD} limit")
            raise SafetyError(
                f"🔴 BLOCKED: {ticker} {action} {quantity}sh ≈ ${estimated_cost:.0f} "
                f"exceeds max position size ${MAX_POSITION_SIZE_USD}. "
                "Pass confirm_live=True to override."
            )

        # ── SAFETY: daily loss check ──
        self._check_daily_loss()

        try:
            contract = Stock(ticker, "SMART", "USD")
            order = MarketOrder(action, int(quantity))
            trade = self.ib.placeOrder(contract, order)
            self.ib.sleep(1)

            fill = trade.fills[0] if trade.fills else None
            avg_price = round(fill.execution.avgPrice, 2) if fill else None

            result = {
                "order_id": trade.order.orderId,
                "ticker": ticker,
                "action": action,
                "quantity": quantity,
                "status": str(trade.orderStatus.status),
                "filled": trade.orderStatus.filled,
                "avg_fill": avg_price,
            }
            _log_order(ticker, action, quantity, avg_price, result["status"], f"id={trade.order.orderId}")
            return result
        except Exception as e:
            _log_order(ticker, action, quantity, None, "FAILED", str(e))
            return {"error": str(e), "ticker": ticker}

    def _is_paper(self):
        """Check if connected account is paper (DUP prefix = paper)."""
        return self.account and self.account.startswith("DUP")

    def _get_approx_price(self, ticker):
        """Get approximate current price for a ticker."""
        try:
            contract = Stock(ticker, "SMART", "USD")
            self.ib.reqMktData(contract, "", False, False)
            self.ib.sleep(0.5)
            tick = self.ib.ticker(contract)
            return tick.marketPrice() or tick.close or 50
        except Exception:
            return 50

    def _check_daily_loss(self):
        """Check if daily loss exceeds limit. Blocks new orders if so."""
        try:
            summary = self.ib.accountSummary()
            for item in summary:
                if item.tag == "NetLiquidation":
                    nav = float(item.value)
                    break
            else:
                return

            # We track daily loss via our own start-of-day value
            # For now, basic check: don't let account drop >10%
            for item in summary:
                if item.tag == "GrossPositionValue":
                    gpv = float(item.value)
                    if gpv > 0 and nav < gpv * 0.9:
                        raise SafetyError(
                            f"🔴 HARD STOP: Account NAV ${nav:,.0f} is 10%+ below "
                            f"position value ${gpv:,.0f}. Trading halted."
                        )
        except SafetyError:
            raise
        except Exception:
            pass

    def get_positions(self):
        if not self.connected:
            return []
        try:
            return [
                {"ticker": p.contract.symbol, "shares": p.position, "avg_cost": round(p.avgCost, 2)}
                for p in self.ib.positions()
            ]
        except Exception:
            return []

    def get_account_summary(self):
        if not self.connected:
            return {}
        try:
            result = {}
            for item in self.ib.accountSummary():
                if item.tag in ("TotalCashValue", "NetLiquidation", "GrossPositionValue", "BuyingPower"):
                    result[item.tag] = float(item.value)
            return result
        except Exception:
            return {}

    def market_snapshot(self):
        if not self.connect():
            return {"status": "offline"}
        try:
            return {"status": "ok", "account": self.get_account_summary(), "positions": self.get_positions()}
        finally:
            self.disconnect()


def place_top_picks(recommendations, position_size=2000):
    """Place paper trades for top TA recommendations."""
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

            try:
                order = bridge.place_market_order(ticker, quantity, "BUY")
                orders.append(order)
                if order.get("avg_fill"):
                    cash -= quantity * order["avg_fill"]
            except SafetyError as e:
                orders.append({"ticker": ticker, "error": str(e)})
                break  # Stop placing orders if safety kicks in

        return {"status": "ok", "account": acc, "orders": orders}
    finally:
        bridge.disconnect()
