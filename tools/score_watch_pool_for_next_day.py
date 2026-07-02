import csv
import json
import math
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[1]
POOL = ROOT / "prediction_tracking" / "watch_pool_full.csv"
OUT = ROOT / "prediction_tracking" / "next_day_candidate_scores.csv"


def market_prefix(code):
    return "1" if code.startswith(("6", "9")) else "0"


def fetch_kline(code):
    url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
    params = {
        "secid": f"{market_prefix(code)}.{code}",
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
        "klt": "101",
        "fqt": "1",
        "beg": "20260501",
        "end": "20260701",
    }
    try:
        data = requests.get(url, params=params, timeout=12).json().get("data") or {}
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
                }
            )
        return out
    except Exception:
        return []


def avg(values, n):
    return sum(values[-n:]) / n if len(values) >= n else None


def score_row(pool_row, rows):
    if len(rows) < 25:
        return None
    closes = [r["close"] for r in rows]
    amounts = [r["amount"] for r in rows]
    d = rows[-1]
    c = d["close"]
    ma5 = avg(closes, 5)
    ma10 = avg(closes, 10)
    ma20 = avg(closes, 20)
    amt5 = avg(amounts, 5) or 0
    amt20 = avg(amounts, 20) or 1
    high20 = max(r["high"] for r in rows[-20:])
    low20 = min(r["low"] for r in rows[-20:])
    pct3 = (c / rows[-4]["close"] - 1) * 100 if len(rows) >= 4 else 0
    pct5 = (c / rows[-6]["close"] - 1) * 100 if len(rows) >= 6 else 0
    pct10 = (c / rows[-11]["close"] - 1) * 100 if len(rows) >= 11 else 0
    pos20 = (c - low20) / (high20 - low20) if high20 > low20 else 0.5
    vol_ratio = amt5 / amt20 if amt20 else 0
    upper_shadow = (d["high"] - max(d["open"], d["close"])) / c if c else 0
    close_pos = (d["close"] - d["low"]) / (d["high"] - d["low"]) if d["high"] > d["low"] else 0.5

    level = pool_row.get("当前层级", "")
    direction = pool_row.get("方向", "")
    score = 0
    reasons = []
    risks = []

    if "核心执行" in level:
        score += 12
    elif "强势观察" in level:
        score += 10
    elif "轮动观察" in level:
        score += 6
    elif "低权重" in level:
        score += 2
    else:
        score -= 2

    if ma5 and ma10 and ma20 and c > ma10 > ma20:
        score += 18
        reasons.append("中短趋势保持")
    elif ma10 and ma20 and c > ma20:
        score += 10
        reasons.append("守住20日趋势")
    else:
        score -= 12
        risks.append("均线结构偏弱")

    if d["pct"] > 0 and close_pos >= 0.55:
        score += 14
        reasons.append("当日收盘承接尚可")
    elif d["pct"] >= -1 and close_pos >= 0.45:
        score += 8
        reasons.append("小幅震荡未破坏")
    else:
        score -= 10
        risks.append("当日承接偏弱")

    if 0 <= pct10 <= 18:
        score += 14
        reasons.append("10日涨幅未明显过热")
    elif pct10 > 18:
        score -= 14
        risks.append("10日涨幅过热")
    else:
        score -= 4

    if vol_ratio <= 1.8:
        score += 8
    else:
        score -= 8
        risks.append("短期放量偏大")

    if upper_shadow <= 0.025:
        score += 8
    else:
        score -= 10
        risks.append("上影线偏长")

    if 0.45 <= pos20 <= 0.82:
        score += 12
        reasons.append("位置处于趋势中段")
    elif pos20 > 0.82:
        score -= 8
        risks.append("20日位置偏高")
    else:
        score += 2

    hot_bonus = 0
    if any(k in direction for k in ["半导体", "存储", "先进封装", "电子材料", "CPO", "光模块", "PCB", "AI", "液冷", "算力"]):
        hot_bonus += 8
    if any(k in direction for k in ["机器人", "高端制造"]):
        hot_bonus += 4
    score += hot_bonus

    if d["pct"] > 6:
        score -= 12
        risks.append("前一日涨幅超6%，明日只看回踩")
    if d["close"] < d["open"] and d["pct"] > 0:
        score -= 6
        risks.append("高位收低于开盘")

    if "降级" in level:
        score -= 8
    if "低权重" in level:
        score -= 5

    pred_type = "稳健观察"
    if score >= 58 and "核心执行" in level and pct10 <= 18 and d["pct"] <= 6 and upper_shadow <= 0.025:
        pred_type = "核心承接"
    if pct5 > 15 or d["pct"] > 7 or upper_shadow > 0.035:
        pred_type = "非规则观察"

    support_low = max(ma10 or c * 0.96, c * 0.965)
    support_high = max(ma5 or c * 0.98, c * 0.985)
    trigger = max(c * 1.01, ma5 or c)
    invalid = min(ma20 * 0.99 if ma20 else c * 0.94, c * 0.94)

    return {
        "代码": pool_row["代码"],
        "名称": pool_row["名称"],
        "方向": direction,
        "当前层级": level,
        "预测类型": pred_type,
        "评分": round(score, 1),
        "收盘价": round(c, 2),
        "涨跌幅": f"{d['pct']:.2f}%",
        "3日涨幅": round(pct3, 2),
        "5日涨幅": round(pct5, 2),
        "10日涨幅": round(pct10, 2),
        "量比5/20": round(vol_ratio, 2),
        "20日位置": round(pos20, 2),
        "上影线": round(upper_shadow * 100, 2),
        "承接区": f"{support_low:.2f}-{support_high:.2f}",
        "触发位": round(trigger, 2),
        "失效位": round(invalid, 2),
        "理由": "；".join(reasons[:3]),
        "风险": "；".join(risks[:3]),
    }


def main():
    with POOL.open(encoding="utf-8-sig", newline="") as handle:
        pool = list(csv.DictReader(handle))

    results = []
    with ThreadPoolExecutor(max_workers=20) as ex:
        futures = {ex.submit(fetch_kline, row["代码"]): row for row in pool}
        for fut in as_completed(futures):
            row = futures[fut]
            rows = fut.result()
            scored = score_row(row, rows)
            if scored:
                results.append(scored)

    results.sort(key=lambda x: x["评分"], reverse=True)
    fields = [
        "代码",
        "名称",
        "方向",
        "当前层级",
        "预测类型",
        "评分",
        "收盘价",
        "涨跌幅",
        "3日涨幅",
        "5日涨幅",
        "10日涨幅",
        "量比5/20",
        "20日位置",
        "上影线",
        "承接区",
        "触发位",
        "失效位",
        "理由",
        "风险",
    ]
    with OUT.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(results)
    print(json.dumps(results[:30], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
