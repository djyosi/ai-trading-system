#!/usr/bin/env bash
# US market preflight — 13:00 BST = 08:00 ET
set -euo pipefail

REPO_ROOT="/Users/YosiG/ai-trading-system"
BACKEND_DIR="$REPO_ROOT/backend"
OUTPUT_DIR="$REPO_ROOT/runtime/daily-research"

cd "$BACKEND_DIR"
. .venv/bin/activate

python -m app.jobs.daily_research \
  --universe-preset liquid_research_500 \
  --include-news-catalysts \
  --include-market-context \
  --actionable-score-threshold 30 \
  --min-trades 5 \
  --output-dir "$OUTPUT_DIR"
