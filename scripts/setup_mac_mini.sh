#!/usr/bin/env bash
# ============================================================
# AI Trading System — Mac Mini Setup
# הרצה: bash setup_mac_mini.sh
# ============================================================
set -euo pipefail

REPO_URL="https://github.com/djyosi/ai-trading-system.git"
INSTALL_DIR="$HOME/ai-trading-system"

echo "=== 1. התקנת Hermes ==="
echo "הורד מ- https://hermes-agent.nousresearch.com/install"
echo "לחץ Enter כשהתקנת..."
read -r

echo "=== 2. Cloning המערכת ==="
git clone "$REPO_URL" "$INSTALL_DIR"
cd "$INSTALL_DIR/backend"

echo "=== 3. Python environment ==="
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip -q
pip install fastapi uvicorn httpx yfinance python-dotenv -q

echo "=== 4. API Keys ==="
if [ ! -f .env ]; then
    echo "יצירת .env — הדבק את MASSIVE_API_KEY שלך:"
    echo -n "MASSIVE_API_KEY="
    read -r key
    echo "MASSIVE_API_KEY=$key" > .env
    echo "API KEY נשמר"
fi

echo "=== 5. בדיקת מערכת ==="
source .venv/bin/activate
python3 -m pytest -q || echo "⚠️  חלק מהטסטים נכשלו"
python3 -m ruff check app tests || echo "⚠️  lint warnings"

echo "=== 6. הפעלת שרת ==="
echo "מריץ uvicorn ברקע..."
nohup .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 > ~/trading_server.log 2>&1 &
echo "שרת רץ על http://localhost:8000/dashboard"

echo ""
echo "========================================"
echo "  ✅ Setup Complete"
echo "========================================"
echo "  Dashboard: http://localhost:8000/dashboard"
echo "  Server PID: $(lsof -ti :8000)"
echo ""
echo "  להגדרת cron jobs ב-Hermes,"
echo "  פתח צ'אט והפעל את הפקודות הבאות:"
echo "========================================"
