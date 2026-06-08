# Phase 3 Massive paper-validation smoke — 2026-06-08

## Purpose

Validate that live Massive.com data can flow through the Phase 3 research path without broker execution:

```text
Massive historical candles
+ Massive news catalysts
+ provider-backed SPY/QQQ/IWM market context
-> walk-forward recommendations
-> deterministic paper validation
-> research report
```

No API key or raw provider payloads are stored here.

## Run configuration

```text
universe_preset: liquid_research_25
start: 2025-01-02
end: 2025-03-31
include_news_catalysts: true
include_market_context: true
lookback_bars: 20
horizon_bars: 5
actionable_score_threshold: 30
thresholds: [30, 40, 50, 60, 70, 80, 85, 90]
min_trades: 3
paper_account_equity: 100000
paper_risk_fraction: 0.01
orders_enabled: false
```

## Live Massive smoke checks

```text
massive_key_loaded: true
AAPL snapshot: ok
AAPL daily candles 2025-01-02..2025-03-31: 60
AAPL news call: ok
AAPL news records fetched: 100
```

## Phase 3 run result

```text
run_ok: true
tickers_total: 25
tickers_completed: 25
tickers_failed: 0
evaluated_bars_total: 1000
news_catalysts_fetched: 2039
market_context_source: provider_etfs
orders_enabled: false
```

## Paper-validation summary

```text
recommendations_total: 1000
closed_total: 613
skipped_total: 323
not_triggered_total: 64
wins: 223
losses: 388
win_rate: 0.36
average_realized_r: -0.23
expectancy_r: -0.23
paper_evidence_buckets: baseline, evidence_backed
```

## Research report summary

```text
research_report_status: research_ready
phase_2_readiness: ready_for_paper_validation
phase_3_status: paper_validation_started
evidence_backed_closed_total: 41
baseline_closed_total: 572
evidence_backed_expectancy_r: -0.18
baseline_expectancy_r: -0.23
next_step: expand_paper_validation_sample
warnings: none
segment_recommendation_count: 5
market_context_segment_recommendation_count: 5
```

## Interpretation

This proves the live Massive-backed Phase 3 plumbing works on a small universe:

```text
Massive -> catalysts/context/candles -> replay -> recommendations -> paper validation -> report
```

The first sample is not yet evidence of a profitable strategy. Overall expectancy was negative, though evidence-backed candidates were slightly less negative than baseline in this small run. The valid next step is to expand the sample, preferably `liquid_research_100` or `liquid_research_250`, while preserving the same paper-only safety boundary.
