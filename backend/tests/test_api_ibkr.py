from fastapi.testclient import TestClient

from app.api.routes.ibkr import get_ibkr_broker
from app.main import app


class FakeBroker:
    async def connect(self):
        return True

    async def get_account_summary(self):
        return {"connected": True, "mode": "paper", "net_liquidation": 100000}

    async def is_symbol_tradable(self, ticker):
        return ticker == "AAPL"


def test_ibkr_paper_account_endpoint_is_read_only_and_returns_summary():
    app.dependency_overrides[get_ibkr_broker] = lambda: FakeBroker()
    client = TestClient(app)

    response = client.get("/api/ibkr/paper/account")

    assert response.status_code == 200
    assert response.json() == {"connected": True, "mode": "paper", "net_liquidation": 100000}
    app.dependency_overrides.clear()


def test_ibkr_paper_tradability_endpoint_checks_symbol_without_orders():
    app.dependency_overrides[get_ibkr_broker] = lambda: FakeBroker()
    client = TestClient(app)

    response = client.get("/api/ibkr/paper/tradability/AAPL")

    assert response.status_code == 200
    assert response.json() == {"ticker": "AAPL", "tradable": True, "mode": "paper", "orders_enabled": False}
    app.dependency_overrides.clear()
