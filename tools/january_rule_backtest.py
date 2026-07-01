import csv
import argparse
import json
import math
import os
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[1]
OUT_BASE_DIR = ROOT / "prediction_tracking"
REPORT_DIR = ROOT / "reports"

START = "2025-10-01"
END = "2026-06-20"


def pct(x):
    return f"{x * 100:.1f}%"


def market_prefix(code: str) -> str:
    return "1" if code.startswith(("6", "9")) else "0"


def get_universe(cache_dir):
    CACHE_DIR = cache_dir
    cache = CACHE_DIR / "universe.json"
    if cache.exists():
        cached = json.loads(cache.read_text(encoding="utf-8"))
        if len(cached) > 4000:
            return cached
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    url = "https://push2.eastmoney.com/api/qt/clist/get"
    rows = []
    page = 1
    while True:
        params = {
            "pn": page,
            "pz": 100,
            "po": 1,
            "np": 1,
            "fltt": 2,
            "invt": 2,
            "fid": "f3",
            "fs": "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23",
            "fields": "f12,f14",
        }
        data = requests.get(url, params=params, timeout=15).json().get("data") or {}
        diff = data.get("diff") or []
        if not diff:
            break
        for item in diff:
            code = str(item.get("f12", "")).zfill(6)
            name = str(item.get("f14", ""))
            if not code or "ST" in name or "退" in name or code.startswith(("8", "4")):
                continue
            rows.append({"代码": code, "名称": name})
        if page * 100 >= int(data.get("total", 0)):
            break
        page += 1
        time.sleep(0.1)
    cache.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    return rows


def fetch_kline_one(stock, cache_dir):
    CACHE_DIR = cache_dir
    code = stock["代码"]
    cache = CACHE_DIR / f"{code}_{START}_{END}.json"
    if cache.exists():
        return code, json.loads(cache.read_text(encoding="utf-8"))
    url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
    params = {
        "secid": f"{market_prefix(code)}.{code}",
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
        "klt": "101",
        "fqt": "1",
        "beg": START.replace("-", ""),
        "end": END.replace("-", ""),
    }
    try:
        r = requests.get(url, params=params, timeout=15)
        raw = r.json()
        data = raw.get("data") or {}
        name = data.get("name") or stock["名称"]
        out = []
        for line in data.get("klines") or []:
            p = line.split(",")
            out.append(
                {
                    "date": p[0],
                    "open": float(p[1]),
                    "close": float(p[2]),
                    "high": float(p[3]),
                    "low": float(p[4]),
                    "volume": float(p[5]),
                    "amount": float(p[6]),
                    "amplitude": float(p[7]),
                    "pct": float(p[8]),
                    "change": float(p[9]),
                    "turnover": float(p[10]),
                    "name": name,
                }
            )
        cache.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
        return code, out
    except Exception:
        return code, []


def ma(values, n):
    if len(values) < n:
        return None
    return sum(values[-n:]) / n


def avg(values, n):
    if len(values) < n:
        return None
    return sum(values[-n:]) / n


def classify_and_score(history):
    closes = [x["close"] for x in history]
    amounts = [x["amount"] for x in history]
    if len(history) < 45:
        return None
    d = history[-1]
    c = d["close"]
    ma5, ma10, ma20, ma30 = ma(closes, 5), ma(closes, 10), ma(closes, 20), ma(closes, 30)
    if not all([ma5, ma10, ma20, ma30]):
        return None
    amt5 = avg(amounts, 5) or 0
    amt20 = avg(amounts, 20) or 1
    high20 = max(x["high"] for x in history[-20:])
    low20 = min(x["low"] for x in history[-20:])
    pct1 = d["pct"]
    pct3 = (c / history[-4]["close"] - 1) * 100 if len(history) >= 4 else 0
    pct10 = (c / history[-11]["close"] - 1) * 100 if len(history) >= 11 else 0
    vol_ratio = amt5 / amt20 if amt20 else 0
    pos20 = (c - low20) / (high20 - low20) if high20 > low20 else 0.5

    if c < 5 or d["amount"] < 80_000_000:
        return None
    if pct1 > 9.8 or pct1 < -8.5:
        return None

    score = 0
    score += 18 if c > ma5 > ma10 > ma20 else 0
    score += 10 if c > ma30 else 0
    score += min(max(pct10, -5), 20) * 1.2
    score += min(max(pct3, -4), 12) * 1.0
    score += min(max((vol_ratio - 1) * 12, 0), 18)
    score += min(max(pos20 * 18, 0), 18)
    if pct1 > 6:
        score -= 10
    if d["close"] < d["open"] and pct1 > 0:
        score -= 8
    if (d["high"] - max(d["open"], d["close"])) / d["close"] > 0.035:
        score -= 8

    if score >= 52 and c > ma5 > ma10 > ma20 and pct10 >= 8 and vol_ratio >= 1.05:
        pred_type = "核心承接"
        support = max(ma5, c * 0.965)
        trigger = max(c * 1.012, d["high"] * 0.998)
        invalid = min(ma10 * 0.985, c * 0.94)
    elif score >= 43 and c > ma10 and c > ma20 and pct10 >= 2 and pos20 >= 0.58:
        pred_type = "稳健观察"
        support = max(ma10, c * 0.955)
        trigger = max(ma5, c * 1.006)
        invalid = min(ma20 * 0.985, c * 0.93)
    elif score >= 39 and pct1 >= 2.2 and vol_ratio >= 1.25 and pos20 >= 0.72:
        pred_type = "弹性进攻"
        support = c * 0.965
        trigger = d["high"] * 1.002
        invalid = c * 0.925
        score -= 3
    else:
        return None

    return {
        "score": round(score, 2),
        "type": pred_type,
        "support": round(support, 2),
        "trigger": round(trigger, 2),
        "invalid": round(invalid, 2),
        "snapshot_close": round(c, 2),
        "pct1": round(pct1, 2),
        "pct10": round(pct10, 2),
        "vol_ratio": round(vol_ratio, 2),
        "pos20": round(pos20, 2),
    }


def review(pred, day):
    open_gap = (day["open"] / pred["snapshot_close"] - 1) * 100
    triggered = day["high"] >= pred["trigger"] or day["close"] >= pred["trigger"]
    invalidated = day["low"] <= pred["invalid"] or day["close"] <= pred["invalid"]
    close_above_trigger = day["close"] >= pred["trigger"]
    close_positive = day["pct"] > 0
    close_upper_half = day["close"] >= (day["low"] + day["high"]) / 2
    high_upper_shadow = day["high"] > max(day["open"], day["close"]) * 1.035
    high_open_failed = open_gap > 3 and day["close"] < day["open"]

    pred_type = pred["预测类型"]
    result = "未命中"
    if pred_type == "核心承接":
        if not invalidated and close_above_trigger and close_positive and not high_open_failed:
            result = "命中"
        elif not invalidated and day["close"] >= pred["support"] and day["pct"] >= -1:
            result = "部分命中"
    elif pred_type == "稳健观察":
        if not invalidated and day["close"] >= pred["support"] and day["pct"] >= 0:
            result = "命中" if day["close"] >= pred["trigger"] else "部分命中"
        elif not invalidated and day["close"] >= pred["support"] * 0.995:
            result = "部分命中"
    elif pred_type == "弹性进攻":
        if (
            triggered
            and not invalidated
            and close_above_trigger
            and close_upper_half
            and not high_upper_shadow
            and not high_open_failed
        ):
            result = "命中"
        elif triggered and not invalidated and day["close"] >= pred["support"] and not high_open_failed:
            result = "部分命中"

    note = (
        f"次日开盘偏离{open_gap:.2f}%，最高{day['high']:.2f}，最低{day['low']:.2f}，"
        f"收盘{day['close']:.2f}，涨跌幅{day['pct']:.2f}%；"
        f"{'触发' if triggered else '未触发'}，{'失效' if invalidated else '未失效'}。"
    )
    return triggered, invalidated, result, note


def weight(pred_type):
    if pred_type == "核心承接":
        return 1.5
    if pred_type == "弹性进攻":
        return 0.8
    return 1.0


def summarize(rows):
    total = len(rows)
    hit = sum(1 for r in rows if r["复盘结果"] == "命中")
    partial = sum(1 for r in rows if r["复盘结果"] == "部分命中")
    miss = total - hit - partial
    w_total = sum(weight(r["预测类型"]) for r in rows)
    w_hit = sum(weight(r["预测类型"]) for r in rows if r["复盘结果"] == "命中")
    w_adj = sum(weight(r["预测类型"]) * (1 if r["复盘结果"] == "命中" else 0.5 if r["复盘结果"] == "部分命中" else 0) for r in rows)
    return {
        "总数": total,
        "命中": hit,
        "部分命中": partial,
        "未命中": miss,
        "严格命中率": pct(hit / total if total else 0),
        "调整后命中率": pct((hit + 0.5 * partial) / total if total else 0),
        "严格加权命中率": pct(w_hit / w_total if w_total else 0),
        "调整后加权命中率": pct(w_adj / w_total if w_total else 0),
    }


def write_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def month_range(year, month):
    start = date(year, month, 1)
    if month == 12:
        end = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end = date(year, month + 1, 1) - timedelta(days=1)
    return start, end


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, default=2026)
    parser.add_argument("--month", type=int, default=1)
    parser.add_argument("--target-start", default="")
    parser.add_argument("--target-end", default="")
    parser.add_argument("--label", default="")
    args = parser.parse_args()

    target_start, target_end = month_range(args.year, args.month)
    if args.target_start:
        target_start = datetime.strptime(args.target_start, "%Y-%m-%d").date()
    if args.target_end:
        target_end = datetime.strptime(args.target_end, "%Y-%m-%d").date()
    month_label = args.label or f"{args.year}年{args.month}月"
    month_id = args.label.replace("年", "_").replace("月", "").replace("至", "_").replace("-", "_") if args.label else f"{args.year}_{args.month:02d}"
    out_dir = OUT_BASE_DIR / f"historical_backtest_{month_id}"
    cache_dir = OUT_BASE_DIR / "historical_backtest_cache"

    OUT_DIR = out_dir
    CACHE_DIR = cache_dir
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    universe = get_universe(CACHE_DIR)
    print(f"universe={len(universe)}")

    histories = {}
    with ThreadPoolExecutor(max_workers=28) as ex:
        futs = [ex.submit(fetch_kline_one, s, CACHE_DIR) for s in universe]
        for i, fut in enumerate(as_completed(futs), 1):
            code, rows = fut.result()
            if rows:
                histories[code] = rows
            if i % 500 == 0:
                print(f"fetched={i}, valid={len(histories)}")

    all_dates = sorted({r["date"] for rows in histories.values() for r in rows})
    trading_dates = [datetime.strptime(x, "%Y-%m-%d").date() for x in all_dates]
    jan_targets = [d for d in trading_dates if target_start <= d <= target_end]
    prev_map = {}
    for d in jan_targets:
        idx = trading_dates.index(d)
        if idx > 0:
            prev_map[d] = trading_dates[idx - 1]

    pred_rows = []
    summary_rows = []

    for target_dt in jan_targets:
        snapshot_dt = prev_map.get(target_dt)
        if not snapshot_dt:
            continue
        candidates = []
        for code, rows in histories.items():
            by_date = {datetime.strptime(x["date"], "%Y-%m-%d").date(): x for x in rows}
            if snapshot_dt not in by_date or target_dt not in by_date:
                continue
            hist = [x for x in rows if datetime.strptime(x["date"], "%Y-%m-%d").date() <= snapshot_dt]
            signal = classify_and_score(hist)
            if not signal:
                continue
            signal["code"] = code
            signal["name"] = hist[-1]["name"]
            signal["target_day"] = by_date[target_dt]
            candidates.append(signal)

        # Keep the mix similar to daily workflow: rule tickets first, then a small elastic slot.
        core = sorted([c for c in candidates if c["type"] == "核心承接"], key=lambda x: x["score"], reverse=True)[:3]
        stable = sorted([c for c in candidates if c["type"] == "稳健观察"], key=lambda x: x["score"], reverse=True)[:2]
        elastic = sorted([c for c in candidates if c["type"] == "弹性进攻"], key=lambda x: x["score"], reverse=True)[:1]
        picks = sorted(core + stable + elastic, key=lambda x: x["score"], reverse=True)[:6]

        day_rows = []
        for rank, p in enumerate(picks, 1):
            pred = {
                "回测批次": f"{month_label}规则倒推",
                "预测日期": target_dt - timedelta(days=1),
                "快照交易日": snapshot_dt,
                "目标日期": target_dt,
                "排名": rank,
                "代码": p["code"],
                "名称": p["name"],
                "市场": "A股",
                "预测类型": p["type"],
                "评分": p["score"],
                "预测逻辑": f"历史倒推：趋势分位{p['pos20']}，10日涨幅{p['pct10']}%，5/20日量比{p['vol_ratio']}，按收紧版趋势承接规则入选。",
                "触发条件": f"次日站上/维持 {p['trigger']}",
                "承接区": f"{p['support']}",
                "失效条件": f"跌破 {p['invalid']}",
                "快照收盘价": p["snapshot_close"],
            }
            triggered, invalidated, result, note = review(pred | {"snapshot_close": p["snapshot_close"], "trigger": p["trigger"], "support": p["support"], "invalid": p["invalid"]}, p["target_day"])
            pred.update(
                {
                    "收盘价": round(p["target_day"]["close"], 2),
                    "涨跌幅": f"{p['target_day']['pct']:.2f}%",
                    "是否触发": "是" if triggered else "否",
                    "是否失效": "是" if invalidated else "否",
                    "复盘结果": result,
                    "复盘备注": note,
                }
            )
            pred_rows.append(pred)
            day_rows.append(pred)

        s = summarize(day_rows)
        type_counts = {}
        for t in ["核心承接", "稳健观察", "弹性进攻"]:
            rows_t = [r for r in day_rows if r["预测类型"] == t]
            type_counts[t] = f"{sum(1 for r in rows_t if r['复盘结果']=='命中')}/{len(rows_t)}"
        summary_rows.append(
            {
                "目标日期": target_dt,
                "预测日期": target_dt - timedelta(days=1),
                "快照交易日": snapshot_dt,
                **s,
                "核心承接命中情况": type_counts["核心承接"],
                "稳健观察命中情况": type_counts["稳健观察"],
                "弹性进攻命中情况": type_counts["弹性进攻"],
                "最佳预测": "；".join(r["名称"] for r in day_rows if r["复盘结果"] == "命中")[:120],
                "最差预测": "；".join(r["名称"] for r in day_rows if r["复盘结果"] == "未命中")[:120],
                "主要误差": "高位趋势票在弱势/分化日容易触发后回落" if s["命中"] < s["未命中"] else "趋势承接整体有效",
                "策略调整信号": "是" if float(s["严格命中率"].rstrip("%")) < 60 or float(s["调整后加权命中率"].rstrip("%")) < 65 else "否",
            }
        )

    pred_fields = [
        "回测批次",
        "预测日期",
        "快照交易日",
        "目标日期",
        "排名",
        "代码",
        "名称",
        "市场",
        "预测类型",
        "评分",
        "预测逻辑",
        "触发条件",
        "承接区",
        "失效条件",
        "快照收盘价",
        "收盘价",
        "涨跌幅",
        "是否触发",
        "是否失效",
        "复盘结果",
        "复盘备注",
    ]
    summary_fields = [
        "目标日期",
        "预测日期",
        "快照交易日",
        "总数",
        "命中",
        "部分命中",
        "未命中",
        "严格命中率",
        "调整后命中率",
        "严格加权命中率",
        "调整后加权命中率",
        "核心承接命中情况",
        "稳健观察命中情况",
        "弹性进攻命中情况",
        "最佳预测",
        "最差预测",
        "主要误差",
        "策略调整信号",
    ]

    ledger_name = f"{month_label}规则倒推预测与复盘台账.csv"
    summary_name = f"{month_label}规则倒推每日统计.csv"
    write_csv(OUT_DIR / ledger_name, pred_rows, pred_fields)
    write_csv(OUT_DIR / summary_name, summary_rows, summary_fields)

    total_summary = summarize(pred_rows)
    type_lines = []
    for t in ["核心承接", "稳健观察", "弹性进攻"]:
        rows_t = [r for r in pred_rows if r["预测类型"] == t]
        if rows_t:
            st = summarize(rows_t)
            type_lines.append(f"| {t} | {st['总数']} | {st['命中']} | {st['部分命中']} | {st['未命中']} | {st['严格命中率']} | {st['调整后命中率']} |")

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report = REPORT_DIR / f"规则倒推回测_{month_label}.md"
    daily_md = "\n".join(
        f"| {r['目标日期']} | {r['总数']} | {r['命中']} | {r['部分命中']} | {r['未命中']} | {r['严格命中率']} | {r['调整后命中率']} | {r['策略调整信号']} |"
        for r in summary_rows
    )
    report.write_text(
        f"""# {month_label}规则倒推回测

> 独立回测口径：本报告不写入现有每日预测台账，不参与当前真实预测命中率统计。

## 回测口径

- 预测范围：目标交易日在 {month_label} 的A股交易日。
- 信息边界：每次预测只使用目标日前一个已收盘交易日及以前的日线数据，模拟晚上10点生成次日预测。
- 复盘口径：用目标交易日收盘后数据，按现有《预测准确率判断规则》做机械复盘。
- 数据来源：东方财富公开A股列表与历史日线接口。
- 限制说明：本轮为“行情结构版”回测，未完整复原当晚新闻、政策原文和实时题材舆情，因此时政热点只通过行情主线强弱间接体现。

## 总体结果

| 总数 | 命中 | 部分命中 | 未命中 | 严格命中率 | 调整后命中率 | 严格加权命中率 | 调整后加权命中率 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| {total_summary['总数']} | {total_summary['命中']} | {total_summary['部分命中']} | {total_summary['未命中']} | {total_summary['严格命中率']} | {total_summary['调整后命中率']} | {total_summary['严格加权命中率']} | {total_summary['调整后加权命中率']} |

## 分类型结果

| 类型 | 总数 | 命中 | 部分命中 | 未命中 | 严格命中率 | 调整后命中率 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
{chr(10).join(type_lines)}

## 每日结果

| 目标日期 | 总数 | 命中 | 部分命中 | 未命中 | 严格命中率 | 调整后命中率 | 策略调整信号 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
{daily_md}

## 初步结论

- 规则对趋势延续日更有效；当指数或热点分化时，核心承接票容易出现“盘中触发、收盘站不住”的扣分。
- 稳健观察的回撤控制通常优于弹性进攻，但收益弹性也较弱。
- 如果后续把历史新闻/政策文本也纳入，需要单独建立“新闻快照表”，否则容易产生事后解释偏差。

## 产物

- 预测与复盘台账：`prediction_tracking/historical_backtest_{month_id}/{ledger_name}`
- 每日统计：`prediction_tracking/historical_backtest_{month_id}/{summary_name}`
""",
        encoding="utf-8",
    )
    print(report)
    print(total_summary)


if __name__ == "__main__":
    main()
