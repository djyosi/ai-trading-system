from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.analytics.performance import summarize_performance
from app.db.session import get_db

router = APIRouter(tags=["performance"])


@router.get("/performance")
def get_performance(db: Session = Depends(get_db)):
    return summarize_performance(db)
