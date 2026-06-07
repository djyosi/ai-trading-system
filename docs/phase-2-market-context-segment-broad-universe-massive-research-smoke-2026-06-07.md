# Phase 2 Market-Context Segment Broad Universe Massive Research Smoke — 2026-06-07

This sanitized live-smoke report reruns `liquid_research_100` after adding market-context-aware segment recommendations.

The research report now surfaces both:

- `strategy|catalyst` segment thresholds
- `strategy|catalyst|market_context` segment thresholds

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

## Latest market context

Source: `provider_etfs`

```json
{
  "iwm_trend": "neutral",
  "qqq_trend": "neutral",
  "risk_context": "mixed",
  "spy_trend": "neutral"
}
```

## Research decision

|Field|Value|
|---|---|
|status|needs_more_data|
|recommended_threshold|None|

Warnings:

```json
[
  "No threshold met both minimum trades (20) and positive expectancy"
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
    "action": "deprioritize_segment",
    "dimension": "catalyst_types",
    "expectancy_r": -0.02,
    "reason": "Negative expectancy segment",
    "segment": "m_and_a",
    "trade_count": 69
  }
]
```

## Aggregate threshold sweep

Best threshold: `None`

|threshold|trade_count|win_rate|expectancy_r|wins|
|---|---|---|---|---|
|30|4779|0.34|-0.14|1644|
|40|3170|0.32|-0.2|1019|
|50|2065|0.31|-0.22|648|
|60|1012|0.34|-0.15|345|
|70|216|0.34|-0.16|73|
|80|31|0.29|-0.27|9|
|85|8|0.38|-0.06|3|
|90|5|0.2|-0.5|1|


## Market-context segment recommendations

These are the new, more precise research candidates.

|segment|strategy|catalyst_type|market_context|recommended_threshold|trade_count|win_rate|expectancy_r|
|---|---|---|---|---|---|---|---|
|vwap_hold_reclaim|contract_win|mixed|vwap_hold_reclaim|contract_win|mixed|60|25|0.52|0.3|
|vwap_hold_reclaim|fda_approval|risk_off|vwap_hold_reclaim|fda_approval|risk_off|50|22|0.5|0.25|
|vwap_hold_reclaim|earnings_beat|risk_off|vwap_hold_reclaim|earnings_beat|risk_off|50|50|0.48|0.2|
|high_relative_volume_breakout|unknown|mixed|high_relative_volume_breakout|unknown|mixed|30|25|0.48|0.2|
|vwap_hold_reclaim|contract_win|supportive|vwap_hold_reclaim|contract_win|supportive|60|74|0.45|0.11|


## Strategy/catalyst segment recommendations

|segment|strategy|catalyst_type|recommended_threshold|trade_count|win_rate|expectancy_r|
|---|---|---|---|---|---|---|
|vwap_hold_reclaim|contract_win|vwap_hold_reclaim|contract_win|70|21|0.62|0.55|
|catalyst_momentum_gap_and_go|analyst_upgrade|catalyst_momentum_gap_and_go|analyst_upgrade|60|38|0.45|0.12|
|vwap_hold_reclaim|unknown|vwap_hold_reclaim|unknown|40|156|0.41|0.03|
|high_relative_volume_breakout|unknown|high_relative_volume_breakout|unknown|40|29|0.41|0.03|


## Edge diagnostics — market contexts

|segment|trade_count|win_rate|expectancy_r|wins|
|---|---|---|---|---|
|risk_off|3167|0.39|-0.03|1224|
|supportive|2386|0.37|-0.08|876|
|mixed|1114|0.29|-0.27|326|


## Edge diagnostics — score bands

|segment|trade_count|win_rate|expectancy_r|wins|
|---|---|---|---|---|
|20-29|95|0.46|0.16|44|
|10-19|957|0.42|0.05|402|
|0-9|836|0.4|0.0|336|
|30-39|1609|0.39|-0.03|625|
|70-79|185|0.35|-0.14|64|


## Edge diagnostics — catalyst types

|segment|trade_count|win_rate|expectancy_r|wins|
|---|---|---|---|---|
|unknown|3369|0.4|0.01|1363|
|m_and_a|69|0.39|-0.02|27|
|product_launch|91|0.36|-0.09|33|
|contract_win|536|0.36|-0.1|192|
|fda_approval|450|0.35|-0.12|159|


## Top symbols in this run

|ticker|closed_total|evaluated_total|win_rate|expectancy_r|
|---|---|---|---|---|
|XLE|74|126|0.68|0.69|
|GLD|60|126|0.65|0.62|
|SLV|74|126|0.61|0.52|
|MRK|71|126|0.61|0.51|
|XOM|65|126|0.6|0.5|


## Weak symbols in this run

|ticker|closed_total|evaluated_total|win_rate|expectancy_r|
|---|---|---|---|---|
|HYG|4|126|0.0|-1.0|
|TXN|34|126|0.12|-0.71|
|TSLA|54|126|0.17|-0.58|
|V|64|126|0.17|-0.57|
|NIO|37|126|0.22|-0.46|


## Key interpretation

Global thresholds remain not ready: every global threshold with enough trades still has negative expectancy.

The more useful layer is now context-specific:

1. `vwap_hold_reclaim|contract_win|mixed`
   - threshold `60`
   - 25 trades
   - win rate `0.52`
   - expectancy `0.30`
2. `vwap_hold_reclaim|fda_approval|risk_off`
   - threshold `50`
   - 22 trades
   - win rate `0.50`
   - expectancy `0.25`
3. `vwap_hold_reclaim|earnings_beat|risk_off`
   - threshold `50`
   - 50 trades
   - win rate `0.48`
   - expectancy `0.20`
4. `vwap_hold_reclaim|contract_win|supportive`
   - threshold `60`
   - 74 trades
   - win rate `0.45`
   - expectancy `0.11`

This is exactly the kind of evidence we need before turning research candidates into recommendation policy.

## Recommended next Phase 2 step

Turn only the strongest market-context segment candidates into conservative strategy policy metadata. Do not promote all positive segments equally. Start with `vwap_hold_reclaim|contract_win`, but attach the market-context evidence so the dashboard can explain where the edge came from.
