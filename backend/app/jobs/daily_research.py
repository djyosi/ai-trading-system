import argparse
import asyncio
import json
from datetime import date, timedelta
from pathlib import Path

from app.backtesting.paper_validation_research import PHASE_3_DEFAULT_UNIVERSE_PRESET, run_paper_validation_research
from app.universe.presets import resolve_universe_preset


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUTPUT_DIR = REPO_ROOT / "docs" / "daily-research"


class DailyResearchSafetyError(RuntimeError):
    """Raised when a daily research run would cross a safety boundary."""


async def run_daily_research(
    mode="preflight",
    market_data_provider=None,
    confirm_live_data=False,
    run_date=None,
    start=None,
    end=None,
    universe_preset=PHASE_3_DEFAULT_UNIVERSE_PRESET,
    tickers=None,
    include_news_catalysts=False,
    include_market_context=False,
    lookback_bars=20,
    horizon_bars=5,
    catalyst_max_age_minutes=None,
    actionable_score_threshold=30,
    thresholds=None,
    min_trades=5,
    paper_account_equity=100_000,
    paper_risk_fraction=0.01,
):
    run_date = run_date or date.today().isoformat()
    start, end = _default_window(start, end, run_date)
    if mode == "preflight":
        return build_daily_research_preflight(
            run_date=run_date,
            start=start,
            end=end,
            universe_preset=universe_preset,
            tickers=tickers,
            include_news_catalysts=include_news_catalysts,
            include_market_context=include_market_context,
            actionable_score_threshold=actionable_score_threshold,
            min_trades=min_trades,
        )
    if mode != "live":
        raise ValueError("mode must be 'preflight' or 'live'")
    if not confirm_live_data:
        raise DailyResearchSafetyError("explicit live research confirmation is required before provider fetches")
    if market_data_provider is None:
        from app.providers.massive import MassiveProvider

        market_data_provider = MassiveProvider()
    report = await run_paper_validation_research(
        market_data_provider=market_data_provider,
        start=start,
        end=end,
        universe_preset=universe_preset,
        tickers=tickers,
        include_news_catalysts=include_news_catalysts,
        include_market_context=include_market_context,
        lookback_bars=lookback_bars,
        horizon_bars=horizon_bars,
        catalyst_max_age_minutes=catalyst_max_age_minutes,
        actionable_score_threshold=actionable_score_threshold,
        thresholds=thresholds,
        min_trades=min_trades,
        paper_account_equity=paper_account_equity,
        paper_risk_fraction=paper_risk_fraction,
    )
    report = dict(report)
    report["run_type"] = "daily_phase_3_research_live"
    report["run_date"] = run_date
    report["mode"] = "live"
    report["live_data_enabled"] = True
    report["orders_enabled"] = False
    report["next_step"] = _daily_live_next_step(report)
    return report


def build_daily_research_preflight(
    run_date=None,
    start=None,
    end=None,
    universe_preset=PHASE_3_DEFAULT_UNIVERSE_PRESET,
    tickers=None,
    include_news_catalysts=False,
    include_market_context=False,
    actionable_score_threshold=30,
    min_trades=5,
):
    run_date = run_date or date.today().isoformat()
    start, end = _default_window(start, end, run_date)
    resolved_tickers = _resolve_tickers(tickers or [], universe_preset)
    market_data_calls = len(resolved_tickers) + (3 if include_market_context else 0)
    news_calls = len(resolved_tickers) if include_news_catalysts else 0
    estimated_provider_calls = market_data_calls + news_calls
    warnings = ["large_provider_call_count"] if estimated_provider_calls >= 500 else []
    return {
        "run_type": "daily_phase_3_research_preflight",
        "run_date": run_date,
        "orders_enabled": False,
        "live_data_enabled": False,
        "mode": "preflight",
        "universe_preset": universe_preset,
        "tickers_total": len(resolved_tickers),
        "start": start,
        "end": end,
        "market_data_candle_calls": market_data_calls,
        "news_catalyst_calls": news_calls,
        "estimated_provider_calls": estimated_provider_calls,
        "include_news_catalysts": include_news_catalysts,
        "include_market_context": include_market_context,
        "actionable_score_threshold": actionable_score_threshold,
        "min_trades": min_trades,
        "warnings": warnings,
        "next_step": "review_preflight_then_enable_explicit_live_research_run",
    }


def write_daily_research_artifacts(report, output_dir=DEFAULT_OUTPUT_DIR):
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    run_date = report["run_date"]
    markdown_path = output_path / f"daily-research-{run_date}.md"
    json_path = output_path / f"daily-research-{run_date}.json"
    markdown_path.write_text(_markdown_report(report), encoding="utf-8")
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"markdown_path": str(markdown_path), "json_path": str(json_path)}


def _markdown_report(report):
    if report.get("mode") == "live":
        return _markdown_live_report(report)
    return _markdown_preflight_report(report)


def _markdown_preflight_report(report):
    warning_text = ", ".join(report["warnings"]) if report["warnings"] else "none"
    return "\n".join(
        [
            f"# Daily AI Trading Research Preflight — {report['run_date']}",
            "",
            "```text",
            f"mode: {report['mode']}",
            "orders_enabled: false",
            "live_data_enabled: false",
            f"universe_preset: {report['universe_preset']}",
            f"tickers_total: {report['tickers_total']}",
            f"start: {report['start']}",
            f"end: {report['end']}",
            f"market_data_candle_calls: {report['market_data_candle_calls']}",
            f"news_catalyst_calls: {report['news_catalyst_calls']}",
            f"estimated_provider_calls: {report['estimated_provider_calls']}",
            f"include_news_catalysts: {str(report['include_news_catalysts']).lower()}",
            f"include_market_context: {str(report['include_market_context']).lower()}",
            f"actionable_score_threshold: {report['actionable_score_threshold']}",
            f"min_trades: {report['min_trades']}",
            f"warnings: {warning_text}",
            f"next_step: {report['next_step']}",
            "```",
            "",
            "No live provider data was fetched. No broker connection or order placement was attempted.",
            "",
        ]
    )


def _markdown_live_report(report):
    readiness = report.get("research_report", {}).get("phase_3_readiness", {})
    paper_summary = report.get("paper_validation", {}).get("summary", {})
    return "\n".join(
        [
            f"# Daily AI Trading Research Live Paper Validation — {report['run_date']}",
            "",
            "```text",
            "mode: live",
            "orders_enabled: false",
            "live_data_enabled: true",
            f"universe_preset: {report['universe_preset']}",
            f"tickers_total: {report['tickers_total']}",
            f"tickers_completed: {report['tickers_completed']}",
            f"tickers_failed: {report['tickers_failed']}",
            f"start: {report['start']}",
            f"end: {report['end']}",
            f"evaluated_bars_total: {report['evaluated_bars_total']}",
            f"news_catalysts_fetched: {report['news_catalysts_fetched']}",
            f"market_context_source: {report['market_context_source']}",
            f"paper_closed_count: {paper_summary.get('closed_count', 0)}",
            f"paper_expectancy_r: {paper_summary.get('expectancy_r')}",
            f"phase_3_readiness_status: {readiness.get('status')}",
            f"next_step: {report['next_step']}",
            "```",
            "",
            "No broker connection or order placement was attempted.",
            "Raw provider payloads and per-trade item dumps are intentionally omitted.",
            "",
        ]
    )


def _daily_live_next_step(report):
    readiness = report.get("research_report", {}).get("phase_3_readiness", {})
    return readiness.get("next_step") or "review_daily_paper_validation_before_policy_changes"


def _resolve_tickers(tickers, universe_preset):
    resolved = [ticker.upper() for ticker in tickers]
    if universe_preset:
        resolved = [*resolved, *resolve_universe_preset(universe_preset)]
    deduped = list(dict.fromkeys(resolved))
    if not deduped:
        raise ValueError("Either tickers or universe_preset is required")
    return deduped


def _default_window(start, end, run_date):
    if start and end:
        return start, end
    current = date.fromisoformat(run_date)
    default_end = current - timedelta(days=1)
    default_start = default_end - timedelta(days=90)
    return start or default_start.isoformat(), end or default_end.isoformat()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Write daily paper-safe AI trading research artifacts.")
    parser.add_argument("--mode", choices=["preflight", "live"], default="preflight")
    parser.add_argument("--confirm-live-data", action="store_true")
    parser.add_argument("--run-date")
    parser.add_argument("--start")
    parser.add_argument("--end")
    parser.add_argument("--universe-preset", default=PHASE_3_DEFAULT_UNIVERSE_PRESET)
    parser.add_argument("--ticker", action="append", dest="tickers", default=[])
    parser.add_argument("--include-news-catalysts", action="store_true")
    parser.add_argument("--include-market-context", action="store_true")
    parser.add_argument("--lookback-bars", type=int, default=20)
    parser.add_argument("--horizon-bars", type=int, default=5)
    parser.add_argument("--catalyst-max-age-minutes", type=int)
    parser.add_argument("--actionable-score-threshold", type=int, default=30)
    parser.add_argument("--min-trades", type=int, default=5)
    parser.add_argument("--paper-account-equity", type=int, default=100_000)
    parser.add_argument("--paper-risk-fraction", type=float, default=0.01)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args(argv)

    report = asyncio.run(
        run_daily_research(
            mode=args.mode,
            confirm_live_data=args.confirm_live_data,
            run_date=args.run_date,
            start=args.start,
            end=args.end,
            universe_preset=args.universe_preset,
            tickers=args.tickers,
            include_news_catalysts=args.include_news_catalysts,
            include_market_context=args.include_market_context,
            lookback_bars=args.lookback_bars,
            horizon_bars=args.horizon_bars,
            catalyst_max_age_minutes=args.catalyst_max_age_minutes,
            actionable_score_threshold=args.actionable_score_threshold,
            min_trades=args.min_trades,
            paper_account_equity=args.paper_account_equity,
            paper_risk_fraction=args.paper_risk_fraction,
        )
    )
    artifact = write_daily_research_artifacts(report, output_dir=args.output_dir)
    print(_summary_line(report, artifact))


def _summary_line(report, artifact):
    if report.get("mode") == "live":
        return (
            "daily_phase_3_research_live "
            f"run_date={report['run_date']} "
            f"universe_preset={report['universe_preset']} "
            f"tickers_completed={report['tickers_completed']}/{report['tickers_total']} "
            f"orders_enabled=false live_data_enabled=true "
            f"markdown_path={artifact['markdown_path']}"
        )
    return (
        "daily_phase_3_research_preflight "
        f"run_date={report['run_date']} "
        f"universe_preset={report['universe_preset']} "
        f"tickers_total={report['tickers_total']} "
        f"estimated_provider_calls={report['estimated_provider_calls']} "
        f"orders_enabled=false live_data_enabled=false "
        f"markdown_path={artifact['markdown_path']}"
    )


if __name__ == "__main__":
    main()
