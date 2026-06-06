# AI Trading System

AI-assisted day-trading recommendation engine for US stocks and ETFs.

## MVP v1

- Web dashboard first
- US stocks + ETFs
- Day-trade recommendations
- Moderate risk profile
- Avoid penny stocks
- Massive.com primary data provider
- Free/low-cost fallback data for prototyping
- IBKR paper-account adapter design, no live trading

## Quick start

```bash
cp .env.example .env
docker compose up --build
```

Backend health endpoint:

```bash
curl http://localhost:8000/api/health
```

Expected:

```json
{"status":"ok"}
```
