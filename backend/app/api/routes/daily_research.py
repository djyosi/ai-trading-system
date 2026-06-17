from pathlib import Path

from fastapi import APIRouter, Depends

from app.jobs.daily_research import DEFAULT_OUTPUT_DIR
from app.jobs.daily_research_status import latest_daily_research_status

router = APIRouter(prefix="/daily-research", tags=["daily-research"])


def get_daily_research_output_dir() -> Path:
    return DEFAULT_OUTPUT_DIR


@router.get("/latest")
def get_latest_daily_research(output_dir: Path = Depends(get_daily_research_output_dir)):
    return latest_daily_research_status(output_dir=output_dir)
