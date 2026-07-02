import csv
import json
import statistics
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "prediction_tracking" / "historical_backtest_2026_ytd" / "2026年规则倒推预测与复盘总台账.csv"
OUT_DIR = ROOT / "prediction_tracking" / "historical_backtest_2026_ytd"
REPORT = ROOT / "reports" / "规则倒推票最佳买卖时间_5分钟真实数据.md"
CACHE = OUT_DIR / "intraday_5m_cache"

BUY_TIMES = [
    "09:35",
    "09:40",
    "09:45",
    "09:50",
    "09:55",
    "10:00",
    "10:15",
    "10:30",
    "10:45",
    "11:00",
    "11:15",
    "11:30",
    "13:05",
    "13:15",
    "13:30",
    "13:45",
    "14:00",
    "14:15",
    "14:30",
    "14:45",
    "14:55",
]
SELL_TIMES = BUY_TIMES[:]


def market_prefix(code):
    return "1" if code.startswith(("6", "9")) else "0"


def fetch_5m(code):
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f"{code}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
    params = {
        "secid": f"{market_prefix(code)}.{code}",
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
        "klt": "5",
        "fqt": "1",
        "beg": "0",
        "end": "20500000",
    }
    try:
        data = requests.get(url, params=params, timeout=12).json().get("data") or {}
        rows = []
        for line in data.get("klines") or []:
            p = line.split(",")
            dt = p[0]
            rows.append(
                {
                    "datetime": dt,
                    "date": dt[:10],
                    "time": dt[11:16],
                    "open": float(p[1]),
                    "close": float(p[2]),
                    "high": float(p[3]),
                    "low": float(p[4]),
                }
            )
        path.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
        return rows
    except Exception:
        return []


def read_rows():
    with LEDGER.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def price_at(day_rows, target_time):
    if not day_rows:
        return None
    exact = [r for r in day_rows if r["time"] == target_time]
    if exact:
        return exact[0]["close"]
    later = [r for r in day_rows if r["time"] >= target_time]
    if later:
        return later[0]["close"]
    return day_rows[-1]["close"]


def next_date(available_dates, target_date):
    dates = sorted(d for d in available_dates if d > target_date)
    return dates[0] if dates else None


def summarize_returns(values):
    if not values:
        return {}
    wins = sum(v > 0 for v in values)
    return {
        "交易数": len(values),
        "平均收益率": sum(values) / len(values),
        "中位数收益率": statistics.median(values),
        "胜率": wins / len(values),
        "最大单笔": max(values),
        "最差单笔": min(values),
    }


def fmt_pct(v):
    return f"{v * 100:.2f}%"


def main():
    rows = read_rows()
    codes = sorted({r["代码"] for r in rows})
    intraday = {}
    with ThreadPoolExecutor(max_workers=20) as ex:
        futures = {ex.submit(fetch_5m, code): code for code in codes}
        for fut in as_completed(futures):
            code = futures[fut]
            intraday[code] = fut.result()

    by_code_date = {}
    coverage_start = None
    coverage_end = None
    for code, bars in intraday.items():
        grouped = defaultdict(list)
        for b in bars:
            grouped[b["date"]].append(b)
        for date, day_rows in grouped.items():
            day_rows.sort(key=lambda x: x["time"])
            by_code_date[(code, date)] = day_rows
        if bars:
            dates = sorted({b["date"] for b in bars})
            if coverage_start is None or dates[0] < coverage_start:
                coverage_start = dates[0]
            if coverage_end is None or dates[-1] > coverage_end:
                coverage_end = dates[-1]

    usable = []
    skipped = []
    for r in rows:
        code = r["代码"]
        target = r["目标日期"]
        day_rows = by_code_date.get((code, target))
        available_dates = {d for c, d in by_code_date if c == code}
        sell_date = next_date(available_dates, target)
        sell_rows = by_code_date.get((code, sell_date)) if sell_date else None
        if not day_rows or not sell_rows:
            skipped.append(r)
            continue
        usable.append((r, day_rows, sell_date, sell_rows))

    combos = []
    detail_best = []
    for buy_time in BUY_TIMES:
        for sell_time in SELL_TIMES:
            rets = []
            details = []
            for r, buy_rows, sell_date, sell_rows in usable:
                buy_price = price_at(buy_rows, buy_time)
                sell_price = price_at(sell_rows, sell_time)
                if not buy_price or not sell_price:
                    continue
                ret = sell_price / buy_price - 1
                rets.append(ret)
                details.append(
                    {
                        "目标日期": r["目标日期"],
                        "卖出日期": sell_date,
                        "代码": r["代码"],
                        "名称": r["名称"],
                        "预测类型": r["预测类型"],
                        "排名": r["排名"],
                        "买入时间": buy_time,
                        "买入价": round(buy_price, 4),
                        "卖出时间": sell_time,
                        "卖出价": round(sell_price, 4),
                        "收益率": ret,
                    }
                )
            stats = summarize_returns(rets)
            if not stats:
                continue
            combos.append({"买入时间": buy_time, "卖出时间": sell_time, **stats})

    combos.sort(key=lambda x: x["平均收益率"], reverse=True)
    best = combos[0] if combos else None

    # Build detail for best combo.
    if best:
        for r, buy_rows, sell_date, sell_rows in usable:
            buy_price = price_at(buy_rows, best["买入时间"])
            sell_price = price_at(sell_rows, best["卖出时间"])
            detail_best.append(
                {
                    "目标日期": r["目标日期"],
                    "卖出日期": sell_date,
                    "代码": r["代码"],
                    "名称": r["名称"],
                    "预测类型": r["预测类型"],
                    "排名": r["排名"],
                    "买入时间": best["买入时间"],
                    "买入价": round(buy_price, 4),
                    "卖出时间": best["卖出时间"],
                    "卖出价": round(sell_price, 4),
                    "收益率": sell_price / buy_price - 1,
                }
            )

    combo_fields = ["买入时间", "卖出时间", "交易数", "平均收益率", "中位数收益率", "胜率", "最大单笔", "最差单笔"]
    with (OUT_DIR / "规则倒推票_5分钟买卖时间优化.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=combo_fields)
        writer.writeheader()
        for row in combos:
            out = row.copy()
            for k in ["平均收益率", "中位数收益率", "胜率", "最大单笔", "最差单笔"]:
                out[k] = fmt_pct(out[k])
            writer.writerow(out)

    detail_fields = ["目标日期", "卖出日期", "代码", "名称", "预测类型", "排名", "买入时间", "买入价", "卖出时间", "卖出价", "收益率"]
    with (OUT_DIR / "规则倒推票_最佳时间逐笔收益.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=detail_fields)
        writer.writeheader()
        for row in detail_best:
            out = row.copy()
            out["收益率"] = fmt_pct(out["收益率"])
            writer.writerow(out)

    top10 = "\n".join(
        f"| {r['买入时间']} | {r['卖出时间']} | {r['交易数']} | {fmt_pct(r['平均收益率'])} | {fmt_pct(r['中位数收益率'])} | {fmt_pct(r['胜率'])} |"
        for r in combos[:10]
    )

    REPORT.write_text(
        f"""# 规则倒推票最佳买卖时间回测

## 数据说明

- 标的范围：2026年历史倒推票总台账。
- 精确分钟线覆盖：约 {coverage_start} 至 {coverage_end}，实际可计算交易 {len(usable)} 笔。
- 未覆盖交易：{len(skipped)} 笔，主要是1月至5月中旬的分钟线历史数据接口不再提供，未纳入精确分钟优化。
- 回测方式：目标日按固定时间买入，下一交易日按固定时间卖出；所有票统一时间，不做个股择时。

## 最佳固定时间

| 买入时间 | 次日卖出时间 | 交易数 | 平均收益率 | 中位数收益率 | 胜率 |
| --- | --- | ---: | ---: | ---: | ---: |
| {best['买入时间'] if best else ''} | {best['卖出时间'] if best else ''} | {best['交易数'] if best else 0} | {fmt_pct(best['平均收益率']) if best else '0.00%'} | {fmt_pct(best['中位数收益率']) if best else '0.00%'} | {fmt_pct(best['胜率']) if best else '0.00%'} |

## 前10组时间

| 买入时间 | 次日卖出时间 | 交易数 | 平均收益率 | 中位数收益率 | 胜率 |
| --- | --- | ---: | ---: | ---: | ---: |
{top10}

## 使用建议

- 这个结果是5分钟真实成交时间的精确回测，但只覆盖接口可拿到的近端样本，不代表1-4月精确分钟表现。
- 如果用于后续固定模式，优先使用“最佳固定时间”作为候选，再结合高开不追和失效位过滤。
- 后续真实预测票继续积累后，应每周重新滚动验证一次，避免单段行情过拟合。
""",
        encoding="utf-8",
    )
    print(REPORT)
    print(json.dumps(best, ensure_ascii=False, indent=2))
    print(f"usable={len(usable)}, skipped={len(skipped)}, coverage={coverage_start}~{coverage_end}")


if __name__ == "__main__":
    main()
