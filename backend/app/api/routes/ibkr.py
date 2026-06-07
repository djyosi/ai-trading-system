from fastapi import APIRouter, Depends

from app.providers.ibkr_paper import IBKRPaperBroker

router = APIRouter(prefix="/ibkr/paper", tags=["ibkr-paper"])


def get_ibkr_broker():
    return IBKRPaperBroker()


@router.get("/account")
async def get_paper_account(broker=Depends(get_ibkr_broker)):
    await broker.connect()
    return await broker.get_account_summary()


@router.get("/tradability/{ticker}")
async def check_paper_tradability(ticker: str, broker=Depends(get_ibkr_broker)):
    await broker.connect()
    return {
        "ticker": ticker.upper(),
        "tradable": await broker.is_symbol_tradable(ticker.upper()),
        "mode": "paper",
        "orders_enabled": False,
    }
