# Phase 1 Massive Research Smoke — 2026-06-07

This is a sanitized live-smoke summary. It records counts and research conclusions only; no API keys or raw provider payloads are stored.

## Request shape

- Provider: Massive.com
- Universe preset: `liquid_research_25`
- Date range: `2025-09-01` through `2026-03-31`
- Historical bars: daily candles
- News catalysts: enabled
- Catalyst freshness window: `4320` minutes
- Research actionability threshold: `30`
- Threshold minimum trades: `20`
- Persistence: disabled
- Broker execution: disabled / not used

## Coverage

```text
tickers_total: 25
tickers_completed: 25
tickers_failed: 0
news_catalysts_fetched: 2419
evaluated_bars_total: 3150
```

## Research status

```text
report_status: needs_more_data
recommended_threshold: null
```

The report correctly did not recommend a global threshold because no global score threshold met both:

```text
trade_count >= 20
expectancy_r > 0
```

## Segment threshold recommendation

One segment-specific recommendation cleared the current guardrails:

```json
{
  "segment": "high_relative_volume_breakout|unknown",
  "strategy": "high_relative_volume_breakout",
  "catalyst_type": "unknown",
  "recommended_threshold": 30,
  "trade_count": 23,
  "win_rate": 0.48,
  "expectancy_r": 0.2
}
```

Interpretation: this is promising enough for further research, but it should not be treated as live-trading-ready. The catalyst type is still `unknown`, so the next phase should improve classification and validate whether this is a real setup edge or an artifact.

## Edge diagnostics

### Score bands

```text
40-49: 42 trades, win_rate 0.40, expectancy_r +0.01
30-39: 131 trades, win_rate 0.37, expectancy_r -0.08
60-69: 12 trades, win_rate 0.33, expectancy_r -0.17
50-59: 53 trades, win_rate 0.21, expectancy_r -0.48
80-89: 2 trades, win_rate 0.00, expectancy_r -1.00
```

### Catalyst types

```text
m_and_a: 2 trades, win_rate 1.00, expectancy_r +1.50
guidance_cut: 1 trade, win_rate 1.00, expectancy_r +1.50
fda_approval: 4 trades, win_rate 0.50, expectancy_r +0.25
unknown: 148 trades, win_rate 0.38, expectancy_r -0.05
analyst_upgrade: 37 trades, win_rate 0.30, expectancy_r -0.26
```

## Next research actions emitted by the system

```json
[
  {
    "action": "increase_sample_size",
    "reason": "No global threshold met minimum trades and positive expectancy",
    "min_trades": 20
  },
  {
    "action": "investigate_promising_segment",
    "dimension": "catalyst_types",
    "segment": "m_and_a",
    "trade_count": 2,
    "expectancy_r": 1.5,
    "reason": "Positive expectancy but only 2 closed trade(s)"
  },
  {
    "action": "deprioritize_segment",
    "dimension": "catalyst_types",
    "segment": "unknown",
    "trade_count": 148,
    "expectancy_r": -0.05,
    "reason": "Negative expectancy segment"
  }
]
```

## Warnings emitted by the system

```text
No threshold met both minimum trades (20) and positive expectancy
Low actionability: 342/3150 recommendations were actionable (10.86%)
Most common no-trade reason: score_below_actionable_threshold (2808)
```

## Conclusion

Phase 1 successfully broadened the research run from a small sample to a 25-symbol live Massive smoke. The system is producing honest research output:

- no global threshold is ready yet;
- one segment-level setup is worth investigating;
- `unknown` catalysts remain a major weak area;
- larger samples and better catalyst classification are the highest-value next improvements.
