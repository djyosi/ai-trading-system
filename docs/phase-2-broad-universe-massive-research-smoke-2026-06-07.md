# Phase 2 Broad Universe Massive Research Smoke — 2026-06-07

This sanitized report reruns `liquid_research_100` after the first Phase 2 strategy changes:

1. Research-derived strategy segment metadata.
2. Guard that blocks bearish-catalyst `short_watch` ideas from receiving long-only trade plans until a short model exists.
3. Provider-backed SPY/QQQ/IWM market context for batch research.

No API keys, raw provider payloads, broker actions, order placement, or credential values are stored here.

## Request shape

```json
{
  "actionable_score_threshold": 30,
  "end": "2026-03-31",
  "horizon_bars": 5,
  "include_market_context": true,
  "include_news_catalysts": true,
  "include_research_report": true,
  "include_threshold_sweep": true,
  "lookback_bars": 20,
  "min_trades": 20,
  "start": "2025-09-01",
  "universe_preset": "liquid_research_100"
}
```

## Coverage

|Metric|Value|
|---|---:|
|tickers_total|100|
|tickers_completed|100|
|tickers_failed|0|
|news_catalysts_fetched|7247|
|evaluated_bars_total|12474|

Error sample:

```json
[]
```

## Market context used

Source: `provider_etfs`

```json
{
  "iwm_trend": "neutral",
  "qqq_trend": "neutral",
  "risk_context": "mixed",
  "spy_trend": "neutral"
}
```

Interpretation: provider ETF context is now wired through the batch API, but the current implementation summarizes the whole date range into one context. For this broad period it still classified as `mixed`. The next improvement should be date-aware context by replay timestamp.

## Research decision

|Field|Value|
|---|---|
|status|needs_more_data|
|recommended_threshold|None|

Warnings:

```json
[
  "No threshold met both minimum trades (20) and positive expectancy",
  "Low actionability: 4800/12474 recommendations were actionable (38.48%)",
  "Most common no-trade reason: score_below_actionable_threshold (7419)"
]
```

Next research actions:

```json
[
  {
    "action": "increase_sample_size",
    "min_trades": 20,
    "reason": "No global threshold met minimum trades and positive expectancy"
  },
  {
    "action": "investigate_promising_segment",
    "dimension": "catalyst_types",
    "expectancy_r": 1.5,
    "reason": "Positive expectancy but only 1 closed trade(s)",
    "segment": "investigation",
    "trade_count": 1
  },
  {
    "action": "deprioritize_segment",
    "dimension": "catalyst_types",
    "expectancy_r": -0.1,
    "reason": "Negative expectancy segment",
    "segment": "contract_win",
    "trade_count": 536
  }
]
```

## Aggregate threshold sweep

Best threshold: `None`

|threshold|trade_count|win_rate|expectancy_r|wins|
|---|---|---|---|---|
|30|3525|0.33|-0.17|1168|
|40|3191|0.32|-0.2|1027|
|50|2865|0.32|-0.2|912|
|60|590|0.36|-0.11|211|
|70|80|0.35|-0.13|28|
|80|15|0.2|-0.5|3|
|85|0|None|None|0|
|90|0|None|None|0|


## Segment threshold recommendations

|segment|strategy|catalyst_type|recommended_threshold|trade_count|win_rate|expectancy_r|
|---|---|---|---|---|---|---|
|vwap_hold_reclaim|contract_win|vwap_hold_reclaim|contract_win|60|69|0.48|0.2|
|high_relative_volume_breakout|unknown|high_relative_volume_breakout|unknown|30|66|0.44|0.1|
|catalyst_momentum_gap_and_go|analyst_upgrade|catalyst_momentum_gap_and_go|analyst_upgrade|60|41|0.44|0.1|
|vwap_hold_reclaim|unknown|vwap_hold_reclaim|unknown|30|318|0.42|0.06|


## Edge diagnostics — score bands

|segment|trade_count|win_rate|expectancy_r|wins|
|---|---|---|---|---|
|30-39|334|0.42|0.06|141|
|70-79|65|0.38|-0.04|25|
|60-69|510|0.36|-0.1|183|
|40-49|326|0.35|-0.12|115|
|50-59|2275|0.31|-0.23|701|


## Edge diagnostics — catalyst types

|segment|trade_count|win_rate|expectancy_r|wins|
|---|---|---|---|---|
|investigation|1|1.0|1.5|1|
|unknown|384|0.43|0.07|164|
|m_and_a|5|0.4|0.0|2|
|contract_win|536|0.36|-0.1|192|
|fda_approval|450|0.35|-0.12|159|


## Edge diagnostics — market contexts

|segment|trade_count|win_rate|expectancy_r|wins|
|---|---|---|---|---|
|mixed|3525|0.33|-0.17|1168|


## Top symbols in this run

|ticker|closed_total|evaluated_total|win_rate|expectancy_r|
|---|---|---|---|---|
|MSFT|1|126|1.0|1.5|
|XLE|44|126|0.77|0.93|
|XOM|25|126|0.76|0.9|
|AMZN|4|126|0.75|0.88|
|GOOGL|7|126|0.71|0.79|


## Weak symbols in this run

|ticker|closed_total|evaluated_total|win_rate|expectancy_r|
|---|---|---|---|---|
|ADBE|3|126|0.0|-1.0|
|PG|6|126|0.0|-1.0|
|UBER|3|126|0.0|-1.0|
|XLU|1|126|0.0|-1.0|
|DE|29|126|0.07|-0.83|


## What changed vs the previous broad run

- The previously suspicious `vwap_hold_reclaim|analyst_downgrade` recommendation disappeared from segment recommendations because bearish catalysts are now blocked from receiving long-only trade plans until an explicit short model exists.
- `vwap_hold_reclaim|contract_win` remains a positive segment candidate: threshold `60`, 69 trades, win rate `0.48`, expectancy `0.20`.
- `catalyst_momentum_gap_and_go|analyst_upgrade` remains a positive segment candidate: threshold `60`, 41 trades, win rate `0.44`, expectancy `0.10`.
- Global thresholds are still not ready; every global threshold with enough trades has negative expectancy.

## Recommended next Phase 2 step

Implement date-aware market context in walk-forward replay rather than one whole-period context. The current provider-backed context is correctly wired, but it is too coarse for regime diagnostics because all decisions still inherit one `mixed` context.
