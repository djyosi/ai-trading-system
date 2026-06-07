# Broad Universe Massive Research Smoke — 2026-06-07

This is a sanitized live-smoke summary for the broad research universe. It records counts and research conclusions only; no API keys or raw provider payloads are stored.

## Request shape

```json
{
  "universe_preset": "liquid_research_100",
  "start": "2025-09-01",
  "end": "2026-03-31",
  "lookback_bars": 20,
  "horizon_bars": 5,
  "include_news_catalysts": true,
  "include_research_report": true,
  "include_threshold_sweep": true,
  "actionable_score_threshold": 30,
  "min_trades": 20
}
```

Safety: read-only research run. No broker execution, no order placement, and no credential changes.

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

## Research decision

|Field|Value|
|---|---|
|status|needs_more_data|
|recommended_threshold|None|

Warnings:

```json
[
  "No threshold met both minimum trades (20) and positive expectancy",
  "Low actionability: 4988/12474 recommendations were actionable (39.99%)",
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
    "reason": "Positive expectancy but only 2 closed trade(s)",
    "segment": "guidance_cut",
    "trade_count": 2
  },
  {
    "action": "deprioritize_segment",
    "dimension": "catalyst_types",
    "expectancy_r": -0.02,
    "reason": "Negative expectancy segment",
    "segment": "analyst_downgrade",
    "trade_count": 135
  }
]
```

## Segment threshold recommendations

|segment|strategy|catalyst_type|recommended_threshold|trade_count|win_rate|expectancy_r|
|---|---|---|---|---|---|---|
|vwap_hold_reclaim|analyst_downgrade|vwap_hold_reclaim|analyst_downgrade|50|35|0.49|0.21|
|vwap_hold_reclaim|contract_win|vwap_hold_reclaim|contract_win|60|69|0.48|0.2|
|high_relative_volume_breakout|unknown|high_relative_volume_breakout|unknown|30|66|0.44|0.1|
|catalyst_momentum_gap_and_go|analyst_upgrade|catalyst_momentum_gap_and_go|analyst_upgrade|60|41|0.44|0.1|
|vwap_hold_reclaim|unknown|vwap_hold_reclaim|unknown|30|318|0.42|0.06|


## Edge diagnostics — score bands

|segment|trade_count|win_rate|expectancy_r|wins|
|---|---|---|---|---|
|30-39|341|0.43|0.07|146|
|70-79|66|0.39|-0.02|26|
|60-69|513|0.36|-0.11|183|
|40-49|421|0.35|-0.12|148|
|50-59|2306|0.31|-0.22|717|


## Edge diagnostics — catalyst types

|segment|trade_count|win_rate|expectancy_r|wins|
|---|---|---|---|---|
|guidance_cut|2|1.0|1.5|2|
|investigation|1|1.0|1.5|1|
|unknown|384|0.43|0.07|164|
|m_and_a|5|0.4|0.0|2|
|analyst_downgrade|135|0.39|-0.02|53|


## Edge diagnostics — market contexts

|segment|trade_count|win_rate|expectancy_r|wins|
|---|---|---|---|---|
|mixed|3662|0.33|-0.17|1223|


## Top symbols in this run

|ticker|closed_total|evaluated_total|win_rate|expectancy_r|
|---|---|---|---|---|
|MSFT|1|126|1.0|1.5|
|GOOGL|9|126|0.78|0.94|
|XLE|44|126|0.77|0.93|
|XOM|25|126|0.76|0.9|
|AMZN|4|126|0.75|0.88|


## Weak symbols in this run

|ticker|closed_total|evaluated_total|win_rate|expectancy_r|
|---|---|---|---|---|
|PG|6|126|0.0|-1.0|
|UBER|3|126|0.0|-1.0|
|XLU|1|126|0.0|-1.0|
|DE|29|126|0.07|-0.83|
|SNAP|12|126|0.08|-0.79|


## Interpretation

The broad universe gave a much stronger sample than the 25-name run:

- 100/100 tickers completed.
- 7,247 Massive news catalyst records were fetched and normalized.
- 12,474 decision bars were evaluated.
- The system still correctly reports `needs_more_data` for the global threshold because no global threshold cleared both the minimum-trade guard and positive-expectancy requirement.

The useful signal is now segment-level, not global-threshold-level:

- `vwap_hold_reclaim|analyst_downgrade` cleared current segment guardrails with expectancy `0.21` over 35 trades.
- `vwap_hold_reclaim|contract_win` cleared current segment guardrails with expectancy `0.20` over 69 trades.
- `high_relative_volume_breakout|unknown` remains positive but should be treated cautiously because unknown catalyst classification is still broad.

Recommended next strategy work:

1. Start Phase 2 with segment-specific scoring/rules instead of one global threshold.
2. Add a rule to deprioritize broad analyst-downgrade exposure except where the strategy segment has positive expectancy.
3. Improve market-context modeling: every closed trade in this run is still grouped under `mixed`, so context diagnostics are not yet useful.
4. Continue improving catalyst classification to reduce dependence on `unknown`.
