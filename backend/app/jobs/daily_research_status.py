import json
from pathlib import Path

from app.jobs.daily_research import DEFAULT_OUTPUT_DIR


def latest_daily_research_status(output_dir=DEFAULT_OUTPUT_DIR):
    output_path = Path(output_dir)
    artifacts = sorted(output_path.glob("daily-research-*.json")) if output_path.exists() else []
    if not artifacts:
        return {
            "status": "missing",
            "latest_run_date": None,
            "mode": None,
            "orders_enabled": False,
            "live_data_enabled": False,
            "artifact_paths": None,
            "next_step": "run_daily_research_preflight",
        }

    latest_artifact = max(artifacts, key=_artifact_sort_key)
    report = json.loads(latest_artifact.read_text(encoding="utf-8"))
    readiness = report.get("research_report", {}).get("phase_3_readiness", {}) or {}
    markdown_artifact = latest_artifact.with_suffix(".md")
    status = {
        "status": "available",
        "latest_run_date": report.get("run_date") or _run_date_from_artifact(latest_artifact),
        "run_type": report.get("run_type"),
        "mode": report.get("mode"),
        "orders_enabled": bool(report.get("orders_enabled", False)),
        "live_data_enabled": bool(report.get("live_data_enabled", False)),
        "universe_preset": report.get("universe_preset"),
        "tickers_total": report.get("tickers_total"),
        "start": report.get("start"),
        "end": report.get("end"),
        "estimated_provider_calls": report.get("estimated_provider_calls"),
        "warnings": report.get("warnings", []),
        "phase_3_readiness_status": readiness.get("status"),
        "paper_validation_summary": report.get("paper_validation", {}).get("summary"),
        "diagnostics_summary": report.get("diagnostics_summary"),
        "next_step": report.get("next_step") or readiness.get("next_step"),
        "artifact_paths": {
            "json": str(latest_artifact),
            "markdown": str(markdown_artifact),
        },
    }
    _copy_if_present(report, status, "tickers_completed")
    _copy_if_present(report, status, "tickers_failed")
    _copy_if_present(report, status, "news_catalysts_fetched")
    _copy_if_present(report, status, "promotion_gate")
    _copy_if_present(report, status, "aggregate_threshold_sweep")
    research = report.get("research_report", {})
    _copy_if_present(research, status, "segment_threshold_recommendations")
    _copy_if_present(research, status, "next_research_actions")
    _copy_if_present(research, status, "top_symbols")
    _copy_if_present(research, status, "weak_symbols")
    return status


def _copy_if_present(source, target, key):
    if key in source:
        target[key] = source[key]


def _artifact_sort_key(path):
    run_date = _run_date_from_artifact(path)
    return (run_date or "", path.stat().st_mtime)


def _run_date_from_artifact(path):
    name = path.stem
    prefix = "daily-research-"
    return name.removeprefix(prefix) if name.startswith(prefix) else None
