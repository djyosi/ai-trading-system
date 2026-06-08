# Phase 3 Massive paper-validation smoke — liquid_research_100 — 2026-06-08

## Purpose

Scale the live Massive.com Phase 3 paper-validation smoke from `liquid_research_25` to `liquid_research_100` while preserving the paper-only safety boundary.

No API key or raw provider payloads are stored here.

## Preflight

```text
universe_preset: liquid_research_100
tickers_total: 100
market_data_candle_calls: 103
news_catalyst_calls: 100
estimated_provider_calls: 203
warnings: none
orders_enabled: false
```

## Run configuration

```text
universe_preset: liquid_research_100
start: 2025-01-02
end: 2025-03-31
include_news_catalysts: true
include_market_context: true
lookback_bars: 20
horizon_bars: 5
actionable_score_threshold: 30
thresholds: [30, 40, 50, 60, 70, 80, 85, 90]
min_trades: 5
paper_account_equity: 100000
paper_risk_fraction: 0.01
orders_enabled: false
```

## Phase 3 run result

```text
run_ok: true
tickers_total: 100
tickers_completed: 100
tickers_failed: 0
evaluated_bars_total: 3960
news_catalysts_fetched: 4658
market_context_source: provider_etfs
orders_enabled: false
```

## Paper-validation summary

```text
recommendations_total: 3960
closed_total: 2494
skipped_total: 1214
not_triggered_total: 252
wins: 1055
losses: 1433
win_rate: 0.42
average_realized_r: -0.09
expectancy_r: -0.09
paper_evidence_buckets: baseline, evidence_backed
```

## Research report summary

```text
research_report_status: research_ready
phase_2_readiness: ready_for_paper_validation
phase_3_status: paper_validation_started
evidence_backed_closed_total: 84
baseline_closed_total: 2410
evidence_backed_expectancy_r: -0.14
baseline_expectancy_r: -0.09
next_step: expand_paper_validation_sample
warnings: none
segment_recommendation_count: 5
market_context_segment_recommendation_count: 5
```

## Interpretation

The `liquid_research_100` live Massive path completed cleanly with no ticker failures.

The broader sample improved overall expectancy compared with the 25-ticker smoke, but expectancy is still negative:

```text
liquid_research_25 overall expectancy: -0.23R
liquid_research_100 overall expectancy: -0.09R
```

However, the evidence-backed subset did not outperform baseline in this 100-ticker run:

```text
evidence_backed_expectancy_r: -0.14R
baseline_expectancy_r: -0.09R
```

This suggests the current evidence/ranking policy should not be trusted as an edge yet. The next research step should diagnose which score bands, catalysts, market contexts, and symbols drove the losses before scaling to 250/500 or relaxing any threshold.
