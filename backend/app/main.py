from fastapi import FastAPI

from app.api.routes.health import router as health_router
from app.api.routes.recommendations import router as recommendations_router

app = FastAPI(title="AI Trading Recommendation Engine", version="0.1.0")
app.include_router(health_router, prefix="/api")
app.include_router(recommendations_router, prefix="/api")
