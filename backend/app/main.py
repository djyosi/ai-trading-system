from fastapi import FastAPI

from app.api.routes.backtests import router as backtests_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.health import router as health_router
from app.api.routes.ibkr import router as ibkr_router
from app.api.routes.performance import router as performance_router
from app.api.routes.recommendations import router as recommendations_router
from app.api.routes.scanner import router as scanner_router

app = FastAPI(title="AI Trading Recommendation Engine", version="0.1.0")
app.include_router(health_router, prefix="/api")
app.include_router(recommendations_router, prefix="/api")
app.include_router(scanner_router, prefix="/api")
app.include_router(performance_router, prefix="/api")
app.include_router(backtests_router, prefix="/api")
app.include_router(dashboard_router, prefix="/api")
app.include_router(ibkr_router, prefix="/api")
