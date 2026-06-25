"""Historical signal backtest — 7-day forward return for each screen type."""

import asyncio
import json

from httpx import AsyncClient

from app.core.config import settings
from app.ta_screener.indicators import compute_indicators
from app.ta_screener import SCREENS


def safe_get(ind, k):
    v = ind.get(k)
    return v if v is not None else 0


def eval_cond(cond, ind):
    import operator as op
    ops = {"<=": op.le, ">=": op.ge, ">": op.gt, "<": op.lt, "==": op.eq, "!=": op.ne}
    for sym, fn in sorted(ops.items(), key=lambda x: -len(x[0])):
        if sym not in cond:
            continue
        parts = cond.split(sym)
        if len(parts) != 2:
            continue
        lhs = safe_get(ind, parts[0].strip())
        rhs_s = parts[1].strip()
        rhs_parts = rhs_s.split("*")
        if len(rhs_parts) == 2:
            try:
                rhs = safe_get(ind, rhs_parts[1].strip()) * float(rhs_parts[0].strip())
            except Exception:
                return False
        else:
            try:
                rhs = float(rhs_s)
            except Exception:
                rhs = safe_get(ind, rhs_s)
        return fn(lhs, rhs)
    return False


def check(ind, sname):
    s = SCREENS.get(sname)
    return s and not ind.get("error") and all(eval_cond(c, ind) for c in s["conditions"])


async def main():
    tickers = json.load(open("tmp/research_tickers.json"))
    api_key = settings.massive_api_key or ""
    st = {}

    async with AsyncClient(base_url=settings.massive_base_url, timeout=30) as c:
        for idx, ticker in enumerate(tickers[:150]):
            try:
                resp = await c.get(
                    f"/v2/aggs/ticker/{ticker}/range/1/day/2026-01-01/2026-06-24",
                    params={"adjusted": "true", "sort": "asc", "limit": 50000, "apiKey": api_key},
                )
                if resp.status_code != 200:
                    continue
                raw = resp.json().get("results", [])
                if len(raw) < 50:
                    continue
                step = max(1, len(raw) // 20)
                for day in range(45, len(raw) - 7, step):
                    window = raw[day - 40 : day]
                    future = raw[day : day + 7]
                    if len(future) < 5:
                        continue
                    candles = [
                        {"timestamp_ms": x["t"], "open": x["o"], "high": x["h"], "low": x["l"], "close": x["c"], "volume": x["v"]}
                        for x in window
                    ]
                    ind = compute_indicators(candles)
                    if ind.get("error"):
                        continue
                    for sname in SCREENS:
                        if check(ind, sname):
                            if sname not in st:
                                st[sname] = {"n": 0, "w": 0, "ret": 0.0}
                            ret = (future[-1]["c"] - future[0]["c"]) / future[0]["c"] * 100
                            st[sname]["n"] += 1
                            st[sname]["ret"] += ret
                            if ret > 0:
                                st[sname]["w"] += 1
            except Exception:
                pass
            if (idx + 1) % 30 == 0:
                print(f"{idx+1}/150...", flush=True)

    print()
    print(f"{'SCREEN':30s}  {'SIG':>5s}  {'W%':>6s}  {'AVG%':>8s}  {'1W RET':>8s}")
    print("-" * 62)
    for sname, s in sorted(st.items(), key=lambda x: -x[1]["n"]):
        if s["n"] < 5:
            continue
        wr = round(s["w"] / s["n"] * 100, 1)
        avg = round(s["ret"] / s["n"], 2)
        bar = "#" * max(1, int(wr / 10))
        print(f"{sname:30s}  {s['n']:>5d}  {wr:>5.1f}%  {avg:>+7.2f}%  ->+7d  {bar}")


if __name__ == "__main__":
    asyncio.run(main())
