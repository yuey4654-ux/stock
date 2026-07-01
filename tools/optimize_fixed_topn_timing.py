import csv
import json
import time
from collections import defaultdict
from pathlib import Path
from urllib.request import Request, urlopen

BASE = Path.cwd()
DAILY = BASE / "prediction_tracking" / "daily_predictions.csv"
OUT = BASE / "prediction_tracking" / "fixed_topn_timing_optimization.csv"
DAILY_OUT = BASE / "prediction_tracking" / "fixed_topn_timing_best_daily.csv"
REPORT = BASE / "reports" / "固定交易模式_前N只与买卖时间优化_2026-07-01.md"
SHARES = 200


def norm_date(value):
    y, m, d = value.split("/")
    return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"


def symbol(code):
    return ("sh" if code.startswith("6") else "sz") + code


def fetch_m5(code):
    sym = symbol(code)
    url = f"https://ifzq.gtimg.cn/appstock/app/kline/mkline?param={sym},m5,,640"
    last_error = None
    for attempt in range(5):
        try:
            req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urlopen(req, timeout=20) as res:
                payload = json.loads(res.read().decode("utf-8"))
            bars = ((payload.get("data") or {}).get(sym) or {}).get("m5") or []
            out = []
            for bar in bars:
                stamp = bar[0]
                out.append({
                    "date": f"{stamp[:4]}-{stamp[4:6]}-{stamp[6:8]}",
                    "time": f"{stamp[8:10]}:{stamp[10:12]}",
                    "open": float(bar[1]),
                })
            time.sleep(0.12)
            return out
        except Exception as exc:
            last_error = exc
            time.sleep(0.8 + attempt * 0.8)
    raise last_error


def load_predictions():
    with DAILY.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    grouped = defaultdict(list)
    for row in rows:
        if row["市场"] != "A股":
            continue
        if row["复盘结果"] not in {"命中", "部分命中", "未命中"}:
            continue
        grouped[norm_date(row["目标日期"])].append(row)
    for day in grouped:
        grouped[day].sort(key=lambda row: int(row["排名"]))
    return dict(sorted(grouped.items()))


def build_price_maps(codes):
    maps = {}
    for code in sorted(codes):
        print(f"fetch {code}", flush=True)
        by_date = defaultdict(dict)
        dates = []
        for bar in fetch_m5(code):
            by_date[bar["date"]][bar["time"]] = bar["open"]
            if not dates or dates[-1] != bar["date"]:
                dates.append(bar["date"])
        maps[code] = {"by_date": by_date, "dates": dates}
    return maps


def next_date(pmap, day):
    if day not in pmap["dates"]:
        return None
    idx = pmap["dates"].index(day)
    return pmap["dates"][idx + 1] if idx + 1 < len(pmap["dates"]) else None


def candidate_times(grouped, price_maps):
    buy_sets = []
    sell_sets = []
    for day, rows in grouped.items():
        for row in rows:
            code = row["代码"]
            pmap = price_maps[code]
            sell_day = next_date(pmap, day)
            if not sell_day:
                continue
            buy_sets.append(set(pmap["by_date"][day]))
            sell_sets.append(set(pmap["by_date"][sell_day]))
    buys = sorted(t for t in set.intersection(*buy_sets) if "09:35" <= t <= "14:55")
    sells = sorted(t for t in set.intersection(*sell_sets) if "09:35" <= t <= "14:55")
    return buys, sells


def evaluate(grouped, price_maps, top_n, buy_time, sell_time):
    cost = 0.0
    profit = 0.0
    trades = 0
    wins = 0
    losses = 0
    day_stats = defaultdict(lambda: {"cost": 0.0, "profit": 0.0, "trades": 0, "wins": 0, "losses": 0, "sell_date": ""})
    for day, rows in grouped.items():
        selected = rows[:top_n]
        for row in selected:
            code = row["代码"]
            pmap = price_maps[code]
            sell_day = next_date(pmap, day)
            if not sell_day:
                continue
            if buy_time not in pmap["by_date"][day] or sell_time not in pmap["by_date"][sell_day]:
                continue
            buy = pmap["by_date"][day][buy_time]
            sell = pmap["by_date"][sell_day][sell_time]
            item_cost = buy * SHARES
            item_profit = (sell - buy) * SHARES
            cost += item_cost
            profit += item_profit
            trades += 1
            if item_profit > 0:
                wins += 1
            elif item_profit < 0:
                losses += 1
            ds = day_stats[day]
            ds["sell_date"] = sell_day
            ds["cost"] += item_cost
            ds["profit"] += item_profit
            ds["trades"] += 1
            if item_profit > 0:
                ds["wins"] += 1
            elif item_profit < 0:
                ds["losses"] += 1
    day_count = len([d for d, s in day_stats.items() if s["trades"]])
    losing_days = sum(1 for s in day_stats.values() if s["profit"] < 0)
    return {
        "top_n": top_n,
        "buy_time": buy_time,
        "sell_time": sell_time,
        "days": day_count,
        "trades": trades,
        "cost": cost,
        "profit": profit,
        "return": profit / cost if cost else 0,
        "wins": wins,
        "losses": losses,
        "win_rate": wins / trades if trades else 0,
        "losing_days": losing_days,
        "day_stats": day_stats,
    }


def main():
    grouped = load_predictions()
    max_n = max(len(rows) for rows in grouped.values())
    codes = {row["代码"] for rows in grouped.values() for row in rows}
    price_maps = build_price_maps(codes)
    buy_times, sell_times = candidate_times(grouped, price_maps)

    results = []
    best = None
    for n in range(1, max_n + 1):
        for bt in buy_times:
            for st in sell_times:
                res = evaluate(grouped, price_maps, n, bt, st)
                if not res["trades"]:
                    continue
                results.append(res)
                if best is None or res["profit"] > best["profit"]:
                    best = res

    rows = []
    for res in sorted(results, key=lambda x: x["profit"], reverse=True):
        rows.append({
            "前N只": str(res["top_n"]),
            "买入时间": res["buy_time"],
            "卖出时间": res["sell_time"],
            "交易日数": str(res["days"]),
            "单票交易数": str(res["trades"]),
            "买入金额": f"{res['cost']:.2f}",
            "收益": f"{res['profit']:.2f}",
            "收益率": f"{res['return'] * 100:.2f}%",
            "胜率": f"{res['win_rate'] * 100:.1f}%",
            "亏损天数": str(res["losing_days"]),
        })
    fields = ["前N只", "买入时间", "卖出时间", "交易日数", "单票交易数", "买入金额", "收益", "收益率", "胜率", "亏损天数"]
    with OUT.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    daily_rows = []
    for day in sorted(best["day_stats"]):
        s = best["day_stats"][day]
        if not s["trades"]:
            continue
        daily_rows.append({
            "目标日期": day,
            "卖出日期": s["sell_date"],
            "前N只": str(best["top_n"]),
            "买入时间": best["buy_time"],
            "卖出时间": best["sell_time"],
            "交易数": str(s["trades"]),
            "买入金额": f"{s['cost']:.2f}",
            "收益": f"{s['profit']:.2f}",
            "收益率": f"{s['profit'] / s['cost'] * 100:.2f}%" if s["cost"] else "0.00%",
            "盈利票": str(s["wins"]),
            "亏损票": str(s["losses"]),
        })
    daily_fields = ["目标日期", "卖出日期", "前N只", "买入时间", "卖出时间", "交易数", "买入金额", "收益", "收益率", "盈利票", "亏损票"]
    with DAILY_OUT.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=daily_fields)
        writer.writeheader()
        writer.writerows(daily_rows)

    top_by_n = {}
    for res in results:
        n = res["top_n"]
        if n not in top_by_n or res["profit"] > top_by_n[n]["profit"]:
            top_by_n[n] = res

    lines = [
        "# 固定交易模式_前N只与买卖时间优化_2026-07-01",
        "",
        "口径：只统计 A 股已复盘预测票；每天买排名前 N 只，每只 200 股；统一固定买入时间，下一交易日统一固定卖出时间；成交价按 5 分钟 K 线开盘价；不计手续费、滑点和涨跌停无法成交。",
        "",
        "## 最优固定模式",
        "",
        f"- 买前 {best['top_n']} 只。",
        f"- 固定买入时间：{best['buy_time']}。",
        f"- 固定卖出时间：次日 {best['sell_time']}。",
        f"- 交易日数：{best['days']} 天，单票交易数：{best['trades']} 笔。",
        f"- 累计买入金额：{best['cost']:.2f} 元。",
        f"- 累计收益：{best['profit']:.2f} 元。",
        f"- 累计收益率：{best['return'] * 100:.2f}%。",
        f"- 单票胜率：{best['win_rate'] * 100:.1f}%，亏损天数：{best['losing_days']} 天。",
        "",
        "## 每个 N 的最优结果",
        "",
        "| 前N只 | 买入时间 | 卖出时间 | 收益 | 收益率 | 胜率 | 亏损天数 |",
        "| ---: | --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for n in sorted(top_by_n):
        res = top_by_n[n]
        lines.append(f"| {n} | {res['buy_time']} | {res['sell_time']} | {res['profit']:.2f} | {res['return'] * 100:.2f}% | {res['win_rate'] * 100:.1f}% | {res['losing_days']} |")
    lines.extend([
        "",
        "## 最优模式每日表现",
        "",
        "| 目标日期 | 卖出日期 | 交易数 | 买入金额 | 收益 | 收益率 | 盈利票 | 亏损票 |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ])
    for row in daily_rows:
        lines.append(f"| {row['目标日期']} | {row['卖出日期']} | {row['交易数']} | {row['买入金额']} | {row['收益']} | {row['收益率']} | {row['盈利票']} | {row['亏损票']} |")
    lines.extend([
        "",
        "## 文件",
        "",
        f"- 全部组合排序：`{OUT.as_posix()}`",
        f"- 最优模式每日明细：`{DAILY_OUT.as_posix()}`",
    ])
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")
    print(f"best_n={best['top_n']} buy={best['buy_time']} sell={best['sell_time']} profit={best['profit']:.2f} return={best['return']*100:.2f}%")


if __name__ == "__main__":
    main()
