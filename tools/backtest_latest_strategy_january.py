import csv
import json
import math
import sys
from calendar import monthrange
from collections import defaultdict, deque
from datetime import datetime, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = ROOT / "prediction_tracking" / "historical_backtest_cache"
REPORT_DIR = ROOT / "reports"

YEAR = 2026
MONTH = int(sys.argv[1]) if len(sys.argv) > 1 else 1
START_DATE = datetime.strptime(f"{YEAR}-{MONTH:02d}-01", "%Y-%m-%d").date()
END_DATE = datetime.strptime(f"{YEAR}-{MONTH:02d}-{monthrange(YEAR, MONTH)[1]}", "%Y-%m-%d").date()
OUT_DIR = ROOT / "prediction_tracking" / f"historical_backtest_latest_strategy_{YEAR}_{MONTH:02d}"
BATCH = f"{YEAR}年{MONTH}月最新策略倒推"
OUT_DIR_LABEL = f"prediction_tracking/historical_backtest_latest_strategy_{YEAR}_{MONTH:02d}"


def pct(x):
    return f"{x * 100:.1f}%"


def as_date(value):
    return datetime.strptime(value, "%Y-%m-%d").date()


def ma(values, n):
    return sum(values[-n:]) / n if len(values) >= n else None


def avg(values, n):
    return sum(values[-n:]) / n if len(values) >= n else None


def weight(prediction_type):
    if prediction_type == "核心承接":
        return 1.5
    if prediction_type == "弹性进攻":
        return 0.8
    return 1.0


def summarize(rows):
    total = len(rows)
    hit = sum(r["复盘结果"] == "命中" for r in rows)
    partial = sum(r["复盘结果"] == "部分命中" for r in rows)
    miss = sum(r["复盘结果"] == "未命中" for r in rows)
    w_total = sum(weight(r["预测类型"]) for r in rows)
    w_hit = sum(weight(r["预测类型"]) for r in rows if r["复盘结果"] == "命中")
    w_adj = sum(
        weight(r["预测类型"])
        * (1 if r["复盘结果"] == "命中" else 0.5 if r["复盘结果"] == "部分命中" else 0)
        for r in rows
    )
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


def parse_pct(text):
    return float(str(text).rstrip("%")) / 100


def load_histories():
    histories = {}
    for path in CACHE_DIR.glob("*_2025-10-01_2026-06-20.json"):
        code = path.name.split("_", 1)[0]
        try:
            rows = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(rows, list) or len(rows) < 60:
            continue
        histories[code] = rows
    return histories


def build_history_indexes(histories):
    indexed = {}
    all_dates = set()
    for code, rows in histories.items():
        parsed_rows = []
        by_date = {}
        for r in rows:
            try:
                d = as_date(r["date"])
            except Exception:
                continue
            item = dict(r)
            item["_date"] = d
            parsed_rows.append(item)
            by_date[d] = item
            all_dates.add(d)
        if len(parsed_rows) >= 60:
            indexed[code] = {"rows": parsed_rows, "by_date": by_date}
    return indexed, sorted(all_dates)


def load_universe_names():
    path = CACHE_DIR / "universe.json"
    if not path.exists():
        return {}
    try:
        rows = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return {str(r.get("代码", "")).zfill(6): r.get("名称", "") for r in rows}


def market_proxy_by_date(histories):
    # 用有完整样本的大盘股/宽基成分近似市场状态，避免依赖指数缓存。
    rows_by_date = defaultdict(list)
    for code, rows in histories.items():
        if not (code.startswith("000") or code.startswith("600") or code.startswith("601") or code.startswith("002")):
            continue
        for r in rows:
            d = r.get("date")
            if d:
                rows_by_date[d].append(r)
    out = {}
    for d, rows in rows_by_date.items():
        if len(rows) < 500:
            continue
        pct_values = [float(r["pct"]) for r in rows]
        up_count = sum(v > 0 for v in pct_values)
        down_big = sum(v <= -5 for v in pct_values)
        limit_down_like = sum(v <= -9.5 for v in pct_values)
        median = sorted(pct_values)[len(pct_values) // 2]
        out[d] = {
            "median_pct": median,
            "up_ratio": up_count / len(pct_values),
            "down_big_count": down_big,
            "limit_down_like": limit_down_like,
            "sample_count": len(pct_values),
        }
    return out


def classify_market(snapshot_date, market_state):
    state = market_state.get(str(snapshot_date))
    if not state:
        return "正常收紧", "缺少市场宽度快照，按正常收紧处理"
    if state["limit_down_like"] >= 25 or state["down_big_count"] >= 220 or state["up_ratio"] < 0.28:
        return "主线退潮", f"宽度弱：上涨占比{state['up_ratio']:.0%}，大跌样本{state['down_big_count']}，跌停近似{state['limit_down_like']}"
    if state["median_pct"] < -1.2 or state["up_ratio"] < 0.38:
        return "外盘/风险偏好压制", f"市场中位涨跌幅{state['median_pct']:.2f}%，上涨占比{state['up_ratio']:.0%}"
    return "正常收紧", f"市场宽度尚可：中位涨跌幅{state['median_pct']:.2f}%，上涨占比{state['up_ratio']:.0%}"


def prior_policy_context(target_date, snapshot_date, market_mode, market_reason):
    # 历史快照里没有逐日新闻全文，这里只做可追踪的“回溯近似”，不把新闻当硬信号。
    if MONTH == 1:
        month_note = "1月处于年初政策预期、业绩预告与春节前流动性观察窗口，题材更容易分化轮动。"
    elif MONTH == 2:
        month_note = "2月包含春节前后流动性切换与节后风险偏好修复窗口，题材易出现缩量和再扩散交替。"
    else:
        month_note = f"{MONTH}月按当月交易节奏和市场宽度变化做回溯近似，题材优先级仅作为辅助。"
    if market_mode == "主线退潮":
        impact = "风险偏好偏弱，早盘8:30预测应减少正式票，优先观察而非补足数量。"
    elif market_mode == "外盘/风险偏好压制":
        impact = "大盘宽度偏弱，早盘8:30预测只保留低位稳健承接样本。"
    else:
        impact = "市场状态允许少量规则票，但仍需不追高、等承接。"
    return f"历史回溯近似：{month_note} 快照日{snapshot_date} {market_reason}；{impact}"


def score_candidate(history):
    if len(history) < 45:
        return None
    closes = [float(x["close"]) for x in history]
    amounts = [float(x["amount"]) for x in history]
    d = history[-1]
    c = float(d["close"])
    ma5, ma10, ma20, ma30 = ma(closes, 5), ma(closes, 10), ma(closes, 20), ma(closes, 30)
    if not all([ma5, ma10, ma20, ma30]):
        return None
    amt5 = avg(amounts, 5) or 0
    amt20 = avg(amounts, 20) or 1
    high20 = max(float(x["high"]) for x in history[-20:])
    low20 = min(float(x["low"]) for x in history[-20:])
    pct1 = float(d["pct"])
    pct3 = (c / closes[-4] - 1) * 100 if len(closes) >= 4 else 0
    pct10 = (c / closes[-11] - 1) * 100 if len(closes) >= 11 else 0
    vol_ratio = amt5 / amt20 if amt20 else 0
    pos20 = (c - low20) / (high20 - low20) if high20 > low20 else 0.5
    upper_shadow = (float(d["high"]) - max(float(d["open"]), c)) / c if c else 0

    if c < 5 or float(d["amount"]) < 80_000_000:
        return None
    if pct1 > 9.8 or pct1 < -8.5:
        return None

    overheat = pct10 > 20 and not (pct1 <= 2.5 and vol_ratio <= 1.8)
    bad_shadow = upper_shadow > 0.035
    high_close_position = pos20 > 0.85

    score = 0
    score += 18 if c > ma5 > ma10 > ma20 else 0
    score += 10 if c > ma30 else 0
    score += min(max(pct10, -5), 18) * 1.0
    score += min(max(pct3, -4), 10) * 0.8
    score += min(max((vol_ratio - 1) * 10, 0), 14)
    score += min(max(pos20 * 12, 0), 12)
    score -= 12 if pct1 > 6 else 0
    score -= 10 if bad_shadow else 0
    score -= 12 if overheat else 0
    score -= 6 if high_close_position and pct1 < 0 else 0

    # 最新策略：稳健观察优先。核心承接和弹性只作为正常日候选，防守日会被过滤。
    if score >= 48 and c > ma5 > ma10 > ma20 and pct10 >= 6 and vol_ratio >= 1.03 and not overheat:
        pred_type = "核心承接"
        support = max(ma5, c * 0.965)
        trigger = max(c * 1.012, float(d["high"]) * 0.998)
        invalid = min(ma10 * 0.985, c * 0.94)
    elif score >= 39 and c > ma10 and c > ma20 and pct10 >= 1 and pos20 >= 0.52 and not bad_shadow:
        pred_type = "稳健观察"
        support = max(ma10, c * 0.965)
        trigger = max(ma5, c * 1.006)
        invalid = min(ma20 * 0.985, c * 0.93)
        if abs(trigger / support - 1) > 0.055:
            return None
    elif score >= 42 and pct1 >= 2.2 and vol_ratio >= 1.25 and pos20 >= 0.72 and not overheat:
        pred_type = "弹性进攻"
        support = c * 0.965
        trigger = float(d["high"]) * 1.002
        invalid = c * 0.925
        score -= 8
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
        "pct3": round(pct3, 2),
        "pct10": round(pct10, 2),
        "vol_ratio": round(vol_ratio, 2),
        "pos20": round(pos20, 2),
        "overheat": overheat,
    }


def review_latest(pred, day, defensive):
    open_gap = (float(day["open"]) / pred["快照收盘价"] - 1) * 100
    high = float(day["high"])
    low = float(day["low"])
    close = float(day["close"])
    open_price = float(day["open"])
    day_pct = float(day["pct"])
    trigger = pred["触发价"]
    support = pred["承接价"]
    invalid = pred["失效价"]
    pred_type = pred["预测类型"]

    triggered = high >= trigger or close >= trigger
    invalidated = low <= invalid or close <= invalid
    downgraded = low <= support * 0.985
    close_above_trigger = close >= trigger
    close_above_support = close >= support
    upper_half = close >= (low + high) / 2
    high_open_failed = open_gap > 3 and close < open_price
    long_upper_shadow = high > max(open_price, close) * 1.035

    result = "未命中"
    if defensive:
        if pred_type == "稳健观察":
            if not invalidated and not downgraded and close_above_trigger and day_pct >= 0 and upper_half:
                result = "命中"
            elif not invalidated and close_above_support and day_pct >= -1.2:
                result = "部分命中"
    elif pred_type == "稳健观察":
        if not invalidated and close_above_support and day_pct >= 0:
            result = "命中" if close_above_trigger and upper_half else "部分命中"
        elif not invalidated and close >= support * 0.995:
            result = "部分命中"
    elif pred_type == "核心承接":
        if not invalidated and close_above_trigger and day_pct > 0 and not high_open_failed:
            result = "命中"
        elif not invalidated and close_above_support and day_pct >= -1 and not high_open_failed:
            result = "部分命中"
    elif pred_type == "弹性进攻":
        if triggered and not invalidated and close_above_trigger and upper_half and not long_upper_shadow and not high_open_failed:
            result = "命中"
        elif triggered and not invalidated and close_above_support and not high_open_failed:
            result = "部分命中"

    note = (
        f"23:00复盘：开盘偏离{open_gap:.2f}%，最高{high:.2f}，最低{low:.2f}，"
        f"收盘{close:.2f}，涨跌幅{day_pct:.2f}%；"
        f"{'触发' if triggered else '未触发'}，{'失效' if invalidated else '未失效'}；"
        f"{'防守口径：需尾盘/收盘确认。' if defensive else '正常收紧口径。'}"
    )
    return triggered, invalidated, result, note


def choose_picks(candidates, mode, recent_summaries):
    if mode == "主线退潮":
        return []
    defensive = mode in {"连续失准防守", "外盘/风险偏好压制"}
    if defensive:
        stable = [c for c in candidates if c["type"] == "稳健观察"]
        stable.sort(key=lambda x: x["score"], reverse=True)
        return stable[:1 if recent_summaries else 2]
    core = sorted([c for c in candidates if c["type"] == "核心承接"], key=lambda x: x["score"], reverse=True)[:1]
    stable = sorted([c for c in candidates if c["type"] == "稳健观察"], key=lambda x: x["score"], reverse=True)[:2]
    elastic = sorted([c for c in candidates if c["type"] == "弹性进攻"], key=lambda x: x["score"], reverse=True)[:0]
    picks = sorted(stable + core + elastic, key=lambda x: (x["type"] != "稳健观察", -x["score"]))
    return picks[:3]


def decide_mode(base_mode, recent_summaries):
    if len(recent_summaries) >= 2:
        last_two = list(recent_summaries)[-2:]
        weak = all(parse_pct(s["严格命中率"]) < 0.60 or parse_pct(s["调整后加权命中率"]) < 0.65 for s in last_two)
        if weak:
            return "连续失准防守"
    return base_mode


def write_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_md_table(path, title, rows, fields):
    lines = [f"# {title}", "", "| " + " | ".join(fields) + " |", "| " + " | ".join(["---"] * len(fields)) + " |"]
    for r in rows:
        lines.append("| " + " | ".join(str(r.get(c, "")).replace("|", "/") for c in fields) + " |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    histories = load_histories()
    indexed_histories, all_dates = build_history_indexes(histories)
    names = load_universe_names()
    market_state = market_proxy_by_date(histories)

    target_dates = [d for d in all_dates if START_DATE <= d <= END_DATE]
    date_pos = {d: i for i, d in enumerate(all_dates)}
    prev_map = {d: all_dates[date_pos[d] - 1] for d in target_dates if date_pos[d] > 0}

    ledger_rows = []
    daily_rows = []
    recent_summaries = deque(maxlen=2)

    for target_dt in target_dates:
        snapshot_dt = prev_map.get(target_dt)
        if not snapshot_dt:
            continue
        base_mode, market_reason = classify_market(snapshot_dt, market_state)
        mode = decide_mode(base_mode, recent_summaries)
        defensive = mode in {"连续失准防守", "外盘/风险偏好压制"}
        policy_context = prior_policy_context(target_dt, snapshot_dt, mode, market_reason)

        candidates = []
        for code, pack in indexed_histories.items():
            rows = pack["rows"]
            by_date = pack["by_date"]
            if snapshot_dt not in by_date or target_dt not in by_date:
                continue
            hist = [x for x in rows if x["_date"] <= snapshot_dt]
            signal = score_candidate(hist)
            if not signal:
                continue
            signal["code"] = code
            signal["name"] = names.get(code) or hist[-1].get("name", "")
            signal["target_day"] = by_date[target_dt]
            candidates.append(signal)

        picks = choose_picks(candidates, mode, recent_summaries)
        day_rows = []
        for rank, p in enumerate(picks, 1):
            row = {
                "回测批次": BATCH,
                "预测生成时间": f"{target_dt} 08:30",
                "复盘时间": f"{target_dt} 23:00",
                "预测日期": str(target_dt),
                "快照交易日": str(snapshot_dt),
                "目标日期": str(target_dt),
                "市场状态": mode,
                "国际国内信息政策与大盘判断": policy_context,
                "排名": rank,
                "代码": p["code"],
                "名称": p["name"],
                "市场": "A股",
                "预测类型": p["type"],
                "评分": p["score"],
                "预测逻辑": (
                    f"最新策略倒推：10日涨幅{p['pct10']}%，3日涨幅{p['pct3']}%，"
                    f"5/20日量比{p['vol_ratio']}，20日位置{p['pos20']}；"
                    f"{'防守模式仅保留稳健观察。' if defensive else '正常收紧模式优先稳健观察。'}"
                ),
                "触发条件": f"09:40后回踩不破{p['support']}，重新站回{p['trigger']}；高开超过3%不追",
                "承接区": f"{p['support']}",
                "失效条件": f"跌破{p['invalid']}视为失效；跌破承接区后尾盘站不回则不记命中",
                "快照收盘价": p["snapshot_close"],
                "触发价": p["trigger"],
                "承接价": p["support"],
                "失效价": p["invalid"],
            }
            triggered, invalidated, result, note = review_latest(row, p["target_day"], defensive)
            row.update(
                {
                    "收盘价": round(float(p["target_day"]["close"]), 2),
                    "涨跌幅": f"{float(p['target_day']['pct']):.2f}%",
                    "是否触发": "是" if triggered else "否",
                    "是否失效": "是" if invalidated else "否",
                    "复盘结果": result,
                    "复盘备注": note,
                }
            )
            ledger_rows.append(row)
            day_rows.append(row)

        s = summarize(day_rows)
        signal = "是" if s["总数"] == 0 or parse_pct(s["严格命中率"]) < 0.60 or parse_pct(s["调整后加权命中率"]) < 0.65 else "否"
        daily = {
            "目标日期": str(target_dt),
            "预测生成时间": f"{target_dt} 08:30",
            "复盘时间": f"{target_dt} 23:00",
            "快照交易日": str(snapshot_dt),
            "市场状态": mode,
            "总数": s["总数"],
            "命中": s["命中"],
            "部分命中": s["部分命中"],
            "未命中": s["未命中"],
            "严格命中率": s["严格命中率"],
            "调整后命中率": s["调整后命中率"],
            "严格加权命中率": s["严格加权命中率"],
            "调整后加权命中率": s["调整后加权命中率"],
            "最佳预测": "；".join(r["名称"] for r in day_rows if r["复盘结果"] in ("命中", "部分命中")) or "无",
            "最差预测": "；".join(r["名称"] for r in day_rows if r["复盘结果"] == "未命中") or "无",
            "主要误差": "无正式规则票，观察日" if not day_rows else "防守/收紧口径下，未满足收盘确认或跌破承接区",
            "策略调整信号": signal,
            "信息政策与大盘备注": policy_context,
        }
        daily_rows.append(daily)
        recent_summaries.append(daily)

    ledger_fields = [
        "回测批次", "预测生成时间", "复盘时间", "预测日期", "快照交易日", "目标日期", "市场状态",
        "国际国内信息政策与大盘判断", "排名", "代码", "名称", "市场", "预测类型", "评分",
        "预测逻辑", "触发条件", "承接区", "失效条件", "快照收盘价", "收盘价", "涨跌幅",
        "触发价", "承接价", "失效价", "是否触发", "是否失效", "复盘结果", "复盘备注",
    ]
    daily_fields = [
        "目标日期", "预测生成时间", "复盘时间", "快照交易日", "市场状态", "总数", "命中",
        "部分命中", "未命中", "严格命中率", "调整后命中率", "严格加权命中率",
        "调整后加权命中率", "最佳预测", "最差预测", "主要误差", "策略调整信号", "信息政策与大盘备注",
    ]
    write_csv(OUT_DIR / f"{BATCH}预测与复盘台账.csv", ledger_rows, ledger_fields)
    write_csv(OUT_DIR / f"{BATCH}每日统计.csv", daily_rows, daily_fields)
    write_md_table(OUT_DIR / f"{BATCH}每日统计.md", f"{BATCH}每日统计", daily_rows, daily_fields)

    by_type = defaultdict(list)
    by_mode = defaultdict(list)
    for r in ledger_rows:
        by_type[r["预测类型"]].append(r)
        by_mode[r["市场状态"]].append(r)
    type_rows = [{"预测类型": k, **summarize(v)} for k, v in sorted(by_type.items())]
    mode_rows = [{"市场状态": k, **summarize(v)} for k, v in sorted(by_mode.items())]
    write_csv(OUT_DIR / f"{BATCH}类型统计.csv", type_rows, ["预测类型"] + list(summarize([]).keys()))
    write_csv(OUT_DIR / f"{BATCH}市场状态统计.csv", mode_rows, ["市场状态"] + list(summarize([]).keys()))

    total = summarize(ledger_rows)
    daily_md = "\n".join(
        f"| {r['目标日期']} | {r['市场状态']} | {r['总数']} | {r['命中']} | {r['部分命中']} | {r['未命中']} | {r['严格命中率']} | {r['调整后命中率']} | {r['策略调整信号']} |"
        for r in daily_rows
    )
    type_md = "\n".join(
        f"| {r['预测类型']} | {r['总数']} | {r['命中']} | {r['部分命中']} | {r['未命中']} | {r['严格命中率']} | {r['调整后命中率']} |"
        for r in type_rows
    )
    mode_md = "\n".join(
        f"| {r['市场状态']} | {r['总数']} | {r['命中']} | {r['部分命中']} | {r['未命中']} | {r['严格命中率']} | {r['调整后命中率']} |"
        for r in mode_rows
    )
    report = REPORT_DIR / f"最新策略倒推回测_{YEAR}年{MONTH}月.md"
    report.write_text(
        f"""# 最新策略倒推回测_{YEAR}年{MONTH}月

> 独立台账：本次结果写入 `{OUT_DIR_LABEL}/`，不写入正式 `daily_predictions.csv`，不参与真实预测统计。

## 回测口径

- 预测时间：每个目标交易日早上 08:30。
- 复盘时间：每个目标交易日晚上 23:00。
- 信息边界：预测只使用目标日前一个交易日及以前的日线数据，模拟盘前判断。
- 新闻/政策/国际信息：由于本地没有逐日新闻快照，采用历史回溯近似，只用于市场状态备注，不替代买点、承接区和失效位。
- 最新策略：连续失准防守模式、稳健观察优先、核心承接/弹性在防守日暂停、允许无正式规则票。

## 总体结果

| 总数 | 命中 | 部分命中 | 未命中 | 严格命中率 | 调整后命中率 | 严格加权命中率 | 调整后加权命中率 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| {total['总数']} | {total['命中']} | {total['部分命中']} | {total['未命中']} | {total['严格命中率']} | {total['调整后命中率']} | {total['严格加权命中率']} | {total['调整后加权命中率']} |

## 每日结果

| 目标日期 | 市场状态 | 总数 | 命中 | 部分命中 | 未命中 | 严格命中率 | 调整后命中率 | 策略调整信号 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
{daily_md}

## 类型统计

| 类型 | 总数 | 命中 | 部分命中 | 未命中 | 严格命中率 | 调整后命中率 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
{type_md}

## 市场状态统计

| 市场状态 | 总数 | 命中 | 部分命中 | 未命中 | 严格命中率 | 调整后命中率 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
{mode_md}

## 结论

- 新策略明显减少出票数量，尤其在连续低命中后允许进入观察/防守，而不是机械补满 3-6 只。
- {MONTH} 月回测的关键不是提高弹性，而是验证“少出票、只做稳健观察、收盘确认”的误判压缩效果。
- 因缺少逐日新闻快照，本报告不能宣称完整复原当日国际国内信息，只能把新闻政策作为回溯备注；若要进一步提高真实性，需要单独建立每日 08:30 新闻快照库。

## 产物

- 台账：`{OUT_DIR_LABEL}/{BATCH}预测与复盘台账.csv`
- 每日统计：`{OUT_DIR_LABEL}/{BATCH}每日统计.csv`
- 类型统计：`{OUT_DIR_LABEL}/{BATCH}类型统计.csv`
- 市场状态统计：`{OUT_DIR_LABEL}/{BATCH}市场状态统计.csv`
""",
        encoding="utf-8",
    )
    print(report)
    print(total)


if __name__ == "__main__":
    main()
