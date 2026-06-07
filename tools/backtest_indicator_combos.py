from __future__ import annotations

import csv
import json
import math
import statistics
import sys
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path


START = "20250601"
END = "20260531"
OUT_DIR = Path(r"C:\Users\Administrator\Documents\股票分析\indicator_backtest")


UNIVERSE = {
    "A股高流动性样本": [
        "300750.SZ", "600519.SH", "000858.SZ", "601318.SH", "600036.SH",
        "002594.SZ", "600030.SH", "601899.SH", "000333.SZ", "002475.SZ",
        "300059.SZ", "601012.SH", "600887.SH", "600276.SH", "000651.SZ",
        "600900.SH", "601888.SH", "000625.SZ", "002415.SZ", "300760.SZ",
        "603259.SH", "600309.SH", "601166.SH", "600438.SH", "002714.SZ",
    ],
    "港股高流动性样本": [
        "00700.HK", "09988.HK", "03690.HK", "01810.HK", "01211.HK",
        "01024.HK", "09868.HK", "09618.HK", "02020.HK", "02318.HK",
        "01347.HK", "00883.HK", "00941.HK", "00388.HK", "09961.HK",
    ],
}


@dataclass
class Bar:
    date: str
    open: float
    close: float
    high: float
    low: float
    volume: float
    amount: float
    pct: float
    turnover: float | None = None


def secid(symbol: str) -> str:
    code, market = symbol.split(".")
    if market == "SH":
        return f"1.{code}"
    if market == "SZ":
        return f"0.{code}"
    if market == "HK":
        return f"116.{code}"
    raise ValueError(symbol)


def fetch_kline(symbol: str) -> list[Bar]:
    OUT_DIR.mkdir(exist_ok=True)
    cache_path = OUT_DIR / f"{symbol.replace('.', '_')}.json"
    if cache_path.exists():
        raw = json.loads(cache_path.read_text(encoding="utf-8"))
        klines = (raw.get("data") or {}).get("klines") or []
        return parse_klines(klines)

    params = {
        "secid": secid(symbol),
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
        "klt": "101",
        "fqt": "1",
        "beg": START,
        "end": END,
    }
    url = "https://push2his.eastmoney.com/api/qt/stock/kline/get?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    last_exc = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                raw = json.loads(resp.read().decode("utf-8"))
            break
        except Exception as exc:
            last_exc = exc
            time.sleep(0.8 + attempt * 0.8)
    else:
        raise last_exc
    cache_path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
    klines = (raw.get("data") or {}).get("klines") or []
    return parse_klines(klines)


def parse_klines(klines: list[str]) -> list[Bar]:
    bars: list[Bar] = []
    for line in klines:
        parts = line.split(",")
        if len(parts) < 11:
            continue
        turnover = None
        try:
            turnover = float(parts[10]) if parts[10] else None
        except ValueError:
            turnover = None
        bars.append(
            Bar(
                date=parts[0],
                open=float(parts[1]),
                close=float(parts[2]),
                high=float(parts[3]),
                low=float(parts[4]),
                volume=float(parts[5]),
                amount=float(parts[6]),
                pct=float(parts[8]),
                turnover=turnover,
            )
        )
    return bars


def sma(values: list[float], n: int, i: int) -> float | None:
    if i + 1 < n:
        return None
    return sum(values[i + 1 - n : i + 1]) / n


def ema_series(values: list[float], n: int) -> list[float]:
    out = []
    alpha = 2 / (n + 1)
    last = values[0]
    for value in values:
        last = value * alpha + last * (1 - alpha)
        out.append(last)
    return out


def rsi_series(values: list[float], n: int = 14) -> list[float | None]:
    rsis: list[float | None] = [None] * len(values)
    gains = [0.0]
    losses = [0.0]
    for i in range(1, len(values)):
        chg = values[i] - values[i - 1]
        gains.append(max(chg, 0.0))
        losses.append(max(-chg, 0.0))
    for i in range(n, len(values)):
        avg_gain = sum(gains[i + 1 - n : i + 1]) / n
        avg_loss = sum(losses[i + 1 - n : i + 1]) / n
        if avg_loss == 0:
            rsis[i] = 100.0
        else:
            rs = avg_gain / avg_loss
            rsis[i] = 100 - 100 / (1 + rs)
    return rsis


def max_drawdown(returns: list[float]) -> float:
    equity = 1.0
    peak = 1.0
    mdd = 0.0
    for ret in returns:
        equity *= 1 + ret
        peak = max(peak, equity)
        mdd = min(mdd, equity / peak - 1)
    return mdd


def indicators(bars: list[Bar]) -> dict[str, list[float | None]]:
    close = [b.close for b in bars]
    high = [b.high for b in bars]
    low = [b.low for b in bars]
    volume = [b.volume for b in bars]
    ma5 = [sma(close, 5, i) for i in range(len(bars))]
    ma10 = [sma(close, 10, i) for i in range(len(bars))]
    ma20 = [sma(close, 20, i) for i in range(len(bars))]
    ma60 = [sma(close, 60, i) for i in range(len(bars))]
    vol20 = [sma(volume, 20, i) for i in range(len(bars))]
    rsi14 = rsi_series(close, 14)
    ema12 = ema_series(close, 12)
    ema26 = ema_series(close, 26)
    dif = [a - b for a, b in zip(ema12, ema26)]
    dea = ema_series(dif, 9)
    macd_hist = [2 * (d - e) for d, e in zip(dif, dea)]
    hi20 = [max(high[i - 19 : i + 1]) if i >= 19 else None for i in range(len(bars))]
    lo20 = [min(low[i - 19 : i + 1]) if i >= 19 else None for i in range(len(bars))]
    return {
        "ma5": ma5,
        "ma10": ma10,
        "ma20": ma20,
        "ma60": ma60,
        "vol20": vol20,
        "rsi14": rsi14,
        "dif": dif,
        "dea": dea,
        "macd_hist": macd_hist,
        "hi20": hi20,
        "lo20": lo20,
    }


def signal_breakout(bars: list[Bar], ind: dict[str, list[float | None]], i: int) -> bool:
    if i < 61:
        return False
    b = bars[i]
    ma20, ma60, vol20, hi20 = ind["ma20"][i], ind["ma60"][i], ind["vol20"][i], ind["hi20"][i - 1]
    rsi = ind["rsi14"][i]
    if None in (ma20, ma60, vol20, hi20, rsi):
        return False
    recent5 = bars[i].close / bars[i - 5].close - 1
    return (
        b.close > hi20
        and b.close > ma20 > ma60
        and b.volume > vol20 * 1.5
        and 45 <= rsi <= 75
        and recent5 < 0.18
    )


def signal_pullback(bars: list[Bar], ind: dict[str, list[float | None]], i: int) -> bool:
    if i < 65:
        return False
    b = bars[i]
    prev = bars[i - 1]
    ma10, ma20, ma60, vol20 = ind["ma10"][i], ind["ma20"][i], ind["ma60"][i], ind["vol20"][i]
    rsi = ind["rsi14"][i]
    if None in (ma10, ma20, ma60, vol20, rsi):
        return False
    prior_strength = bars[i - 1].close / bars[i - 20].close - 1
    pullback_ok = prev.low <= ma10 * 1.02 or prev.low <= ma20 * 1.02
    reclaim = b.close > b.open and b.close > ma10 and b.close > prev.high * 0.995
    return (
        ma10 > ma20 > ma60
        and prior_strength > 0.08
        and prior_strength < 0.35
        and pullback_ok
        and reclaim
        and b.volume >= vol20 * 0.9
        and 45 <= rsi <= 70
    )


def signal_macd_rsi(bars: list[Bar], ind: dict[str, list[float | None]], i: int) -> bool:
    if i < 61:
        return False
    ma20, ma60 = ind["ma20"][i], ind["ma60"][i]
    rsi, rsi_prev = ind["rsi14"][i], ind["rsi14"][i - 1]
    if None in (ma20, ma60, rsi, rsi_prev):
        return False
    return (
        bars[i].close > ma20 > ma60
        and ind["dif"][i] > ind["dea"][i]
        and ind["dif"][i - 1] <= ind["dea"][i - 1]
        and rsi_prev < 50 <= rsi <= 70
    )


def signal_combo(bars: list[Bar], ind: dict[str, list[float | None]], i: int) -> bool:
    if not signal_pullback(bars, ind, i):
        return False
    b = bars[i]
    vol20 = ind["vol20"][i]
    if vol20 is None:
        return False
    return ind["dif"][i] > ind["dea"][i] and b.volume > vol20 and b.pct < 7


STRATEGIES = {
    "平台突破": signal_breakout,
    "强势回踩": signal_pullback,
    "MACD+RSI趋势过滤": signal_macd_rsi,
    "综合高约束组合": signal_combo,
}


def run_strategy(symbol: str, bars: list[Bar], name: str, fn, hold_days=5, stop_pct=0.06, take_pct=0.12):
    ind = indicators(bars)
    trades = []
    for i in range(len(bars) - hold_days - 1):
        if not fn(bars, ind, i):
            continue
        entry = bars[i + 1].open
        if entry <= 0:
            continue
        exit_price = bars[i + 1 + hold_days].close
        exit_date = bars[i + 1 + hold_days].date
        reason = f"{hold_days}日持有"
        stop = entry * (1 - stop_pct)
        take = entry * (1 + take_pct)
        for j in range(i + 1, min(i + 2 + hold_days, len(bars))):
            if bars[j].low <= stop:
                exit_price = stop
                exit_date = bars[j].date
                reason = "止损"
                break
            if bars[j].high >= take:
                exit_price = take
                exit_date = bars[j].date
                reason = "止盈"
                break
        ret = exit_price / entry - 1 - 0.002
        trades.append(
            {
                "symbol": symbol,
                "strategy": name,
                "signal_date": bars[i].date,
                "entry_date": bars[i + 1].date,
                "exit_date": exit_date,
                "entry": round(entry, 4),
                "exit": round(exit_price, 4),
                "return": ret,
                "reason": reason,
                "hold_days": hold_days,
                "stop_pct": stop_pct,
                "take_pct": take_pct,
            }
        )
    return trades


def summarize(trades: list[dict]) -> dict:
    returns = [t["return"] for t in trades]
    wins = [r for r in returns if r > 0]
    losses = [r for r in returns if r <= 0]
    if not trades:
        return {
            "trades": 0,
            "win_rate": None,
            "avg_return": None,
            "avg_win": None,
            "avg_loss": None,
            "profit_factor": None,
            "max_drawdown": None,
        }
    avg_win = statistics.mean(wins) if wins else 0
    avg_loss = statistics.mean(losses) if losses else 0
    profit_factor = sum(wins) / abs(sum(losses)) if losses and sum(losses) != 0 else None
    return {
        "trades": len(trades),
        "win_rate": len(wins) / len(trades),
        "avg_return": statistics.mean(returns),
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "profit_factor": profit_factor,
        "max_drawdown": max_drawdown(returns),
    }


def main() -> int:
    OUT_DIR.mkdir(exist_ok=True)
    all_trades = []
    failures = []
    bars_by_symbol = {}
    universe = UNIVERSE
    if "--a-only" in sys.argv:
        universe = {"A股高流动性样本": UNIVERSE["A股高流动性样本"]}
    for group, symbols in universe.items():
        for symbol in symbols:
            try:
                bars = fetch_kline(symbol)
                if len(bars) < 120:
                    failures.append((symbol, "数据不足"))
                    continue
                bars_by_symbol[symbol] = bars
                for name, fn in STRATEGIES.items():
                    for trade in run_strategy(symbol, bars, name, fn):
                        trade["group"] = group
                        all_trades.append(trade)
                time.sleep(0.45)
            except Exception as exc:
                failures.append((symbol, repr(exc)))

    summary_rows = []
    for strategy in STRATEGIES:
        trades = [t for t in all_trades if t["strategy"] == strategy]
        row = {"strategy": strategy, **summarize(trades)}
        summary_rows.append(row)

    for group in universe:
        for strategy in STRATEGIES:
            trades = [t for t in all_trades if t["strategy"] == strategy and t["group"] == group]
            row = {"strategy": f"{group}-{strategy}", **summarize(trades)}
            summary_rows.append(row)

    with (OUT_DIR / "trades.csv").open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(all_trades[0].keys()) if all_trades else ["empty"])
        writer.writeheader()
        writer.writerows(all_trades)
    with (OUT_DIR / "summary.csv").open("w", newline="", encoding="utf-8-sig") as f:
        fieldnames = ["strategy", "trades", "win_rate", "avg_return", "avg_win", "avg_loss", "profit_factor", "max_drawdown"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(summary_rows)
    with (OUT_DIR / "failures.json").open("w", encoding="utf-8") as f:
        json.dump(failures, f, ensure_ascii=False, indent=2)

    optimized_rows = []
    for strategy_name in ["强势回踩", "综合高约束组合"]:
        fn = STRATEGIES[strategy_name]
        for hold_days in [3, 5, 8, 10]:
            for stop_pct in [0.04, 0.06, 0.08]:
                for take_pct in [0.06, 0.08, 0.10, 0.12]:
                    trades = []
                    for group, symbols in universe.items():
                        for symbol in symbols:
                            bars = bars_by_symbol.get(symbol)
                            if not bars:
                                continue
                            for trade in run_strategy(symbol, bars, strategy_name, fn, hold_days, stop_pct, take_pct):
                                trade["group"] = group
                                trades.append(trade)
                    stats = summarize(trades)
                    optimized_rows.append(
                        {
                            "strategy": strategy_name,
                            "hold_days": hold_days,
                            "stop_pct": stop_pct,
                            "take_pct": take_pct,
                            **stats,
                        }
                    )
    optimized_rows.sort(key=lambda r: ((r["win_rate"] or 0), (r["profit_factor"] or 0), r["trades"]), reverse=True)
    with (OUT_DIR / "optimized_summary.csv").open("w", newline="", encoding="utf-8-sig") as f:
        fieldnames = ["strategy", "hold_days", "stop_pct", "take_pct", "trades", "win_rate", "avg_return", "avg_win", "avg_loss", "profit_factor", "max_drawdown"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(optimized_rows)

    print(json.dumps({"summary": summary_rows, "optimized_top10": optimized_rows[:10], "failures": failures[:10], "trade_count": len(all_trades)}, ensure_ascii=False, indent=2))
    return 0 if all_trades else 2


if __name__ == "__main__":
    raise SystemExit(main())
