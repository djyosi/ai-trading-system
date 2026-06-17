# Daily Research Operations Implementation Plan

> **For Hermes:** Implement this plan task-by-task with strict TDD. Keep broker/order placement out of scope. Use atomic commits after each verified slice.

**Goal:** Move the AI trading system from safe daily preflight into a controlled daily research loop that collects evidence, labels paper outcomes, diagnoses weak segments, and only promotes improvements after measured validation.

**Architecture:** Keep the system as a research/recommendation platform, not an auto-trader. Daily automation should flow from preflight -> guarded live Massive paper-validation -> artifact persistence -> diagnostics -> dashboard/API surfacing -> policy-change candidates. Execution/broker order placement stays disabled.

**Tech Stack:** Python 3.9 backend, pytest, ruff, FastAPI/service modules, Hermes cron, Massive provider abstraction, local sanitized artifacts under `runtime/daily-research/`.

---

## Current Context

Already completed and verified:

- Daily paper-safe preflight job exists.
- Hermes cron job exists and is enabled:
  - `job_id: 1bb4556e3590`
  - `name: ai-trading-daily-research-preflight`
  - `schedule: 0 8 * * 1-5`
  - `deliver: local`
- Current preflight artifact path:
  - `runtime/daily-research/daily-research-2026-06-17.md`
- Recent verification:
  - `195 passed`
  - `ruff check app tests` passed
- Latest relevant commits:
  - `6fb2ef1 chore: make daily research preflight executable`
  - `fbff644 feat: add guarded daily live research runner`
  - `3598066 feat: add paper safe daily research preflight`

Safety boundaries:

- `orders_enabled=false` remains mandatory.
- No IBKR order placement.
- No broker connectivity changes.
- No credential printing.
- Live Massive data only through explicit guarded mode.
- Saved artifacts must be sanitized: counts, summaries, status, diagnostics; no raw provider payloads and no credentials.

---

## Process We Are Building

### Phase 0 — Daily preflight, already active

Purpose: every weekday, estimate the next research run before using provider calls.

Current output:

```text
mode: preflight
orders_enabled: false
live_data_enabled: false
universe_preset: liquid_research_500
tickers_total: 500
estimated_provider_calls: 1003
```

This tells us: “If we run the real daily research, here is the scope and cost/rate-limit shape.”

### Phase 1 — Guarded daily live Massive paper-validation

Purpose: perform actual data collection and paper-safe validation, still without broker/orders.

Expected output:

```text
mode: live
orders_enabled: false
live_data_enabled: true
tickers_completed: N
tickers_failed: M
news_catalysts_fetched: N
paper_expectancy_r: X
phase_3_readiness_status: ...
next_step: ...
```

### Phase 2 — Daily evidence diagnostics

Purpose: identify what worked and what failed.

Diagnostics must include:

- Evidence-backed vs baseline expectancy.
- Loss drivers by:
  - score band,
  - catalyst type,
  - market context,
  - symbol,
  - strategy/catalyst/context segment.
- No-trade rejection reasons.
- Low-actionability warnings.

### Phase 3 — Daily dashboard/API reporting

Purpose: expose the daily research state without reading local markdown manually.

Dashboard/API should show:

- latest daily run status,
- latest artifact path,
- preflight vs live mode,
- warnings,
- paper validation summary,
- readiness status,
- next research actions.

### Phase 4 — Controlled policy candidate generation

Purpose: convert diagnostics into proposed improvements, not automatic strategy changes.

Examples:

```text
candidate_action: deprioritize catalyst_type=analyst_upgrade
reason: negative expectancy across sufficient sample
status: requires_backtest_confirmation
```

No production ranking/scoring policy should change unless:

- sample size guard passes,
- expectancy is positive,
- improvement beats baseline,
- backtest/paper validation confirms it,
- tests prove defaults stay conservative.

### Phase 5 — Promotion workflow

Purpose: only promote policy changes after evidence.

Promotion requires:

- regression tests,
- backtest comparison before/after,
- paper validation evidence,
- full test suite + ruff,
- atomic commit.

---

## Implementation Tasks

### Task 1: Add a non-mutating daily operations status reader

**Objective:** Provide a backend function that reads the latest daily artifact and returns a compact status summary.

**Files:**

- Create/modify: `backend/app/jobs/daily_research_status.py`
- Test: `backend/tests/test_daily_research_status.py`

**Test first:**

- Create temp `daily-research-YYYY-MM-DD.json` files.
- Assert the function returns the newest run.
- Assert it omits raw payloads and per-trade item dumps.
- Assert missing directory returns a safe empty status.

**Expected behavior:**

```python
status = latest_daily_research_status(output_dir=tmp_path)
assert status["latest_run_date"] == "2026-06-17"
assert status["mode"] == "preflight"
assert status["orders_enabled"] is False
assert "raw_payload" not in json.dumps(status)
```

**Verification:**

```bash
cd /Users/YosiG/ai-trading-system/backend
. .venv/bin/activate
python -m pytest tests/test_daily_research_status.py -v
python -m pytest -v
python -m ruff check app tests
```

**Commit:**

```bash
git add backend/app/jobs/daily_research_status.py backend/tests/test_daily_research_status.py
git commit -m "feat: expose latest daily research status reader"
```

---

### Task 2: Add API endpoint for latest daily research status

**Objective:** Let the dashboard/backend consumers retrieve the latest daily research state through API instead of local files.

**Files:**

- Modify: `backend/app/api/routes/backtests.py` or create `backend/app/api/routes/daily_research.py`
- Modify: `backend/app/main.py` if a new router is created
- Test: `backend/tests/test_api_daily_research.py`

**Test first:**

- Use `TestClient`.
- Override/default artifact directory if needed via dependency injection.
- Assert endpoint returns:
  - `latest_run_date`,
  - `mode`,
  - `orders_enabled`,
  - `live_data_enabled`,
  - `phase_3_readiness_status` when available,
  - `next_step`.

**Endpoint candidate:**

```text
GET /api/daily-research/latest
```

**Verification:**

```bash
python -m pytest tests/test_api_daily_research.py -v
python -m pytest -v
python -m ruff check app tests
```

**Commit:**

```bash
git add backend/app/api/routes/daily_research.py backend/app/main.py backend/tests/test_api_daily_research.py
git commit -m "feat: add latest daily research API"
```

---

### Task 3: Add explicit live-run shell wrapper, disabled from cron by default

**Objective:** Prepare a safe command for live Massive paper-validation without automatically scheduling it yet.

**Files:**

- Create: `scripts/daily_research_live.sh`
- Test: extend `backend/tests/test_daily_research_job.py` if script behavior can be covered through Python CLI args.

**Rules:**

The script must include:

```bash
python -m app.jobs.daily_research \
  --mode live \
  --confirm-live-data \
  --universe-preset liquid_research_25 \
  --include-news-catalysts \
  --include-market-context \
  --actionable-score-threshold 30 \
  --min-trades 5 \
  --output-dir "$OUTPUT_DIR"
```

Start with `liquid_research_25` for first live daily smoke. Do not default to 500 for first unattended live run.

**Safety tests:**

- Existing `DailyResearchSafetyError` must fail live mode without `--confirm-live-data`.
- Live mode must keep `orders_enabled=false`.
- JSON/Markdown must omit raw provider payloads.

**Verification:**

```bash
python -m pytest tests/test_daily_research_job.py -v
python -m pytest -v
python -m ruff check app tests
```

**Commit:**

```bash
git add scripts/daily_research_live.sh backend/tests/test_daily_research_job.py
git commit -m "feat: add guarded daily live research script"
```

---

### Task 4: Run controlled live Massive smoke manually, not by cron

**Objective:** Prove live path works with real data once, in a small scope, before scheduling.

**Preconditions:**

- Confirm `.env` is ignored:

```bash
git status --short --ignored backend/.env
```

Expected:

```text
!! backend/.env
```

- Do not print API key.
- Do not connect broker.
- Use `liquid_research_25` first.

**Command:**

```bash
cd /Users/YosiG/ai-trading-system
./scripts/daily_research_live.sh
```

**Expected artifact:**

```text
runtime/daily-research/daily-research-YYYY-MM-DD.md
runtime/daily-research/daily-research-YYYY-MM-DD.json
```

**Report only sanitized values:**

- tickers completed/failed,
- news count,
- evaluated bars,
- paper expectancy,
- readiness status,
- next step.

**No commit required unless code changes.**

---

### Task 5: Add daily diagnostics summary extraction

**Objective:** Make every live daily artifact include the key self-improvement signals in a compact top-level shape.

**Files:**

- Modify: `backend/app/jobs/daily_research.py`
- Test: `backend/tests/test_daily_research_job.py`

**Test first:**

Assert live report includes top-level fields:

```python
assert "diagnostics_summary" in report
assert "phase_3_readiness_status" in report["diagnostics_summary"]
assert "evidence_vs_baseline_delta_r" in report["diagnostics_summary"]
assert "worst_loss_drivers" in report["diagnostics_summary"]
assert "next_research_actions" in report["diagnostics_summary"]
```

**Design:**

Extract from existing `research_report`:

- `phase_3_readiness.status`
- `phase_3_readiness.next_step`
- `phase_3_readiness.evidence_vs_baseline_delta_r`
- worst loss drivers from `phase_3_loss_diagnostics`
- `next_research_actions`
- warnings

**Verification:**

```bash
python -m pytest tests/test_daily_research_job.py -v
python -m pytest -v
python -m ruff check app tests
```

**Commit:**

```bash
git add backend/app/jobs/daily_research.py backend/tests/test_daily_research_job.py
git commit -m "feat: summarize daily research diagnostics"
```

---

### Task 6: Add a daily research promotion gate

**Objective:** Prevent strategy/ranking policy changes unless diagnostics and sample requirements pass.

**Files:**

- Create: `backend/app/jobs/daily_research_policy.py`
- Test: `backend/tests/test_daily_research_policy.py`

**Test first:**

Cases:

1. Negative evidence-backed expectancy -> `blocked`.
2. Insufficient sample -> `needs_more_data`.
3. Positive expectancy but not better than baseline -> `blocked`.
4. Positive expectancy, sufficient sample, beats baseline -> `candidate_for_backtest_confirmation`, not auto-promoted.

**Expected result shape:**

```python
{
    "promotion_status": "blocked",
    "reason": "evidence_backed_underperformed_baseline",
    "orders_enabled": False,
    "requires_backtest_confirmation": True,
}
```

**Verification:**

```bash
python -m pytest tests/test_daily_research_policy.py -v
python -m pytest -v
python -m ruff check app tests
```

**Commit:**

```bash
git add backend/app/jobs/daily_research_policy.py backend/tests/test_daily_research_policy.py
git commit -m "feat: gate daily research policy promotion"
```

---

### Task 7: Add cron-controlled live research only after small manual smoke passes

**Objective:** After Task 4 proves live smoke works, create a separate cron job for small live research, not replacing preflight yet.

**Initial schedule candidate:**

```text
30 9 * * 1-5
```

**Mode:**

- `liquid_research_25` first.
- `deliver=local`.
- `no_agent=true`.
- Script under `~/.hermes/scripts/`.

**Stop condition:**

If live smoke shows provider/rate-limit failures, do not schedule. Fix provider handling first.

**Verification:**

```bash
hermes cron list
```

Confirm:

- preflight job remains enabled,
- live job is separate,
- both are local/no-agent,
- no broker/order job exists.

---

## Daily Operating Cadence

### Every weekday morning

1. Preflight runs at 08:00.
2. Review estimated calls/warnings.
3. If live job is enabled later, it runs small controlled research after preflight.
4. Artifacts land in `runtime/daily-research/`.

### Every weekday after data exists

1. Read latest daily status API.
2. Check paper summary.
3. Check evidence-backed vs baseline.
4. Check loss drivers.
5. Generate next research actions.
6. Do not change policy automatically.

### Weekly

1. Aggregate daily artifacts.
2. Compare segments over multiple days.
3. Promote only candidates that survive backtest/paper validation.

---

## Verification Policy

Every code slice must run:

```bash
cd /Users/YosiG/ai-trading-system/backend
. .venv/bin/activate
python -m pytest <targeted-test> -v
python -m pytest -v
python -m ruff check app tests
```

Every slice must commit cleanly:

```bash
git status --short
git add <files>
git commit -m "type: concise message"
git status --short
```

Do not call work done until:

- targeted test passed,
- full suite passed,
- ruff passed,
- code committed,
- working tree clean.

---

## Recommended Immediate Next Step

Start with **Task 1: latest daily research status reader**.

Why this first:

- It is repository-only.
- It has no live API calls.
- It creates the foundation for dashboard/API visibility.
- It lets us inspect daily operation programmatically before expanding live data usage.

After Task 1, proceed to Task 2, then only then consider controlled live Massive smoke.
