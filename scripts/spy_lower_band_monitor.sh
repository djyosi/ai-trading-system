#!/bin/bash
# SPY Lower Band Monitor — runs every 5 min Mon-Fri during market hours
# Hermes cron job: no_agent=true, delivers output on detection
# Environment: loads .env from backend/

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$REPO_ROOT" || exit 1

# Load .env from backend/
if [ -f backend/.env ]; then
    set -a
    source backend/.env
    set +a
fi

export MASSIVE_API_KEY

exec "$REPO_ROOT/backend/.venv/bin/python3" -m app.ta_screener.lower_band_monitor
