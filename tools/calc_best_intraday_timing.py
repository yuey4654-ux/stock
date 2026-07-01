import csv
import json
import time
from collections import defaultdict
from pathlib import Path
from urllib.request import Request, urlopen

BASE = Path.cwd()
DAILY = BASE / "prediction_tracking" / "daily_predictions.csv"
DETAIL = BASE / "prediction_tracking" / "best_intraday_timing_detail.csv"
SUMMARY = BASE / "prediction_tracking" / "best_intraday_timing_daily.csv"
REPORT = BASE / "reports" / "预测票最佳买卖时间倒推_2026-06-30.md"
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
            data = (payload.get("data") or {}).get(sym) or {}
            bars = data.get("m5") or []
            out = []
            for bar in bars:
                stamp = bar[0]
                out.append(
                    {
                        "date": f"{stamp[:4]}-{stamp[4:6]}-{stamp[6:8]}",
                        "time": f"{stamp[8:10]}:{stamp[10:12]}",
                        "open": float(bar[1]),
                    }
                )
            time.sleep(0.15)
            return out
        except Exception as exc:
            last_error = exc
            time.sleep(0.8 + attempt * 0.8)
    raise last_error


def read_predictions():
    with DAILY.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def build_price_maps(codes):
    maps = {}
    for code in sorted(codes):
        print(f"fetch {code}", flush=True)
        bars = fetch_m5(code)
        by_date = defaultdict(dict)
        dates = []
        for bar in bars:
            by_date[bar["date"]][bar["time"]] = bar["open"]
            if not dates or dates[-1] != bar["date"]:
                dates.append(bar["date"])
        maps[code] = {"by_date": by_date, "dates": dates}
    return maps


def next_trade_date(price_map, buy_date):
    dates = price_map["dates"]
    if buy_date not in dates:
        return None
    idx = dates.index(buy_date)
    return dates[idx + 1] if idx + 1 < len(dates) else None


def main():
    rows = [
        row
        for row in read_predictions()
        if row["市场"] == "A股"
        and row["复盘结果"] in {"命中", "部分命中", "未命中"}
    ]
    codes = {row["代码"] for row in rows}
    price_maps = build_price_maps(codes)

    grouped = defaultdict(list)
    skipped = []
    for row in rows:
        buy_date = norm_date(row["目标日期"])
        pmap = price_maps.get(row["代码"])
        if not pmap or buy_date not in pmap["by_date"]:
            skipped.append((row, "无买入日分钟线"))
            continue
        sell_date = next_trade_date(pmap, buy_date)
        if not sell_date or sell_date not in pmap["by_date"]:
            skipped.append((row, "无下一交易日分钟线"))
            continue
        grouped[buy_date].append((row, sell_date))

    summaries = []
    details = []
    for buy_date in sorted(grouped):
        items = grouped[buy_date]
        common_buy_times = None
        common_sell_times = None
        for row, sell_date in items:
            pmap = price_maps[row["代码"]]
            buy_times = set(pmap["by_date"][buy_date])
            sell_times = set(pmap["by_date"][sell_date])
            common_buy_times = buy_times if common_buy_times is None else common_buy_times & buy_times
            common_sell_times = sell_times if common_sell_times is None else common_sell_times & sell_times
        buy_times = sorted(t for t in common_buy_times if "09:35" <= t <= "14:55")
        sell_times = sorted(t for t in common_sell_times if "09:35" <= t <= "14:55")
        best = None
        for bt in buy_times:
            for st in sell_times:
                cost = 0.0
                profit = 0.0
                wins = 0
                losses = 0
                for row, sell_date in items:
                    pmap = price_maps[row["代码"]]
                    buy_price = pmap["by_date"][buy_date][bt]
                    sell_price = pmap["by_date"][sell_date][st]
                    item_profit = (sell_price - buy_price) * SHARES
                    cost += buy_price * SHARES
                    profit += item_profit
                    if item_profit > 0:
                        wins += 1
                    elif item_profit < 0:
                        losses += 1
                ret = profit / cost if cost else 0
                if best is None or profit > best["profit"]:
                    best = {
                        "buy_time": bt,
                        "sell_time": st,
                        "cost": cost,
                        "profit": profit,
                        "return": ret,
                        "wins": wins,
                        "losses": losses,
                    }
        if not best:
            continue
        sell_date = items[0][1]
        summaries.append(
            {
                "目标日期": buy_date,
                "卖出日期": sell_date,
                "票数": str(len(items)),
                "最佳买入时间": best["buy_time"],
                "最佳卖出时间": best["sell_time"],
                "买入金额": f"{best['cost']:.2f}",
                "收益": f"{best['profit']:.2f}",
                "收益率": f"{best['return'] * 100:.2f}%",
                "盈利票": str(best["wins"]),
                "亏损票": str(best["losses"]),
            }
        )
        for row, sell_date in items:
            pmap = price_maps[row["代码"]]
            buy_price = pmap["by_date"][buy_date][best["buy_time"]]
            sell_price = pmap["by_date"][sell_date][best["sell_time"]]
            profit = (sell_price - buy_price) * SHARES
            details.append(
                {
                    "目标日期": buy_date,
                    "卖出日期": sell_date,
                    "最佳买入时间": best["buy_time"],
                    "最佳卖出时间": best["sell_time"],
                    "代码": row["代码"],
                    "名称": row["名称"],
                    "预测类型": row["预测类型"],
                    "买入价": f"{buy_price:.2f}",
                    "卖出价": f"{sell_price:.2f}",
                    "收益": f"{profit:.2f}",
                    "收益率": f"{profit / (buy_price * SHARES) * 100:.2f}%",
                }
            )

    summary_fields = ["目标日期", "卖出日期", "票数", "最佳买入时间", "最佳卖出时间", "买入金额", "收益", "收益率", "盈利票", "亏损票"]
    detail_fields = ["目标日期", "卖出日期", "最佳买入时间", "最佳卖出时间", "代码", "名称", "预测类型", "买入价", "卖出价", "收益", "收益率"]
    with SUMMARY.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=summary_fields)
        writer.writeheader()
        writer.writerows(summaries)
    with DETAIL.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=detail_fields)
        writer.writeheader()
        writer.writerows(details)

    total_cost = sum(float(row["买入金额"]) for row in summaries)
    total_profit = sum(float(row["收益"]) for row in summaries)
    lines = [
        "# 预测票最佳买卖时间倒推_2026-06-30",
        "",
        "口径：只统计 A 股正式预测台账；每天所有预测票统一在同一个 5 分钟时间点买入，下一交易日统一在同一个 5 分钟时间点卖出；成交价按该 5 分钟 K 线开盘价；每只 200 股；不考虑手续费、滑点、涨跌停无法成交。",
        "",
        "重要提醒：这是事后倒推的最优时间点，不能直接当成未来固定公式，只能用来观察你的预测票更容易在什么时段给出高收益。",
        "",
        "## 总体结果",
        "",
        f"- 已完成交易日：{len(summaries)} 天。",
        f"- 累计买入金额：{total_cost:.2f} 元。",
        f"- 最优时间组合下累计收益：{total_profit:.2f} 元。",
        f"- 最优时间组合下累计收益率：{(total_profit / total_cost * 100 if total_cost else 0):.2f}%。",
        "",
        "## 每日最佳时间",
        "",
        "| 目标日期 | 卖出日期 | 票数 | 最佳买入 | 最佳卖出 | 买入金额 | 收益 | 收益率 | 盈利票 | 亏损票 |",
        "| --- | --- | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in summaries:
        lines.append(
            f"| {row['目标日期']} | {row['卖出日期']} | {row['票数']} | {row['最佳买入时间']} | {row['最佳卖出时间']} | {row['买入金额']} | {row['收益']} | {row['收益率']} | {row['盈利票']} | {row['亏损票']} |"
        )
    lines.extend(
        [
            "",
            "## 文件",
            "",
            f"- 每日最佳时间汇总：`{SUMMARY.as_posix()}`",
            f"- 逐票明细：`{DETAIL.as_posix()}`",
            f"- 跳过记录：{len(skipped)} 条，主要为港股、未复盘票、或尚无下一交易日分钟线。",
        ]
    )
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")
    print(f"days={len(summaries)} details={len(details)} skipped={len(skipped)} profit={total_profit:.2f}")


if __name__ == "__main__":
    main()
