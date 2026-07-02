import csv
import importlib.util
import statistics
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OPT_PATH = ROOT / "tools" / "optimize_historical_backtest_intraday_timing.py"
OUT = ROOT / "prediction_tracking" / "historical_backtest_2026_ytd" / "规则倒推票_分类型最佳买卖时间.csv"


def load_opt():
    spec = importlib.util.spec_from_file_location("opt", OPT_PATH)
    opt = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(opt)
    return opt


def type_bucket(prediction_type):
    if prediction_type.startswith("稳健观察"):
        return "稳健观察"
    if prediction_type.startswith("核心承接"):
        return "核心承接"
    if prediction_type.startswith("弹性进攻"):
        return "弹性进攻"
    return "其他"


def pct(v):
    return f"{v * 100:.2f}%"


def main():
    opt = load_opt()
    rows = opt.read_rows()
    intraday = {code: opt.fetch_5m(code) for code in sorted({r["代码"] for r in rows})}
    by_code_date = {}
    for code, bars in intraday.items():
        grouped = defaultdict(list)
        for bar in bars:
            grouped[bar["date"]].append(bar)
        for day, day_rows in grouped.items():
            day_rows.sort(key=lambda x: x["time"])
            by_code_date[(code, day)] = day_rows

    usable = []
    for row in rows:
        code = row["代码"]
        target = row["目标日期"]
        buy_rows = by_code_date.get((code, target))
        dates = {day for c, day in by_code_date if c == code}
        sell_date = opt.next_date(dates, target)
        sell_rows = by_code_date.get((code, sell_date)) if sell_date else None
        if buy_rows and sell_rows:
            usable.append((row, buy_rows, sell_date, sell_rows))

    filters = [
        ("全体", lambda r: True),
        ("稳健观察", lambda r: type_bucket(r["预测类型"]) == "稳健观察"),
        ("核心承接", lambda r: type_bucket(r["预测类型"]) == "核心承接"),
        ("弹性进攻", lambda r: type_bucket(r["预测类型"]) == "弹性进攻"),
        ("排名4-5", lambda r: r["排名"] in {"4", "5"}),
        ("前两名", lambda r: r["排名"] in {"1", "2"}),
    ]

    out_rows = []
    for label, filter_fn in filters:
        best = None
        for buy_time in opt.BUY_TIMES:
            for sell_time in opt.SELL_TIMES:
                values = []
                for row, buy_rows, sell_date, sell_rows in usable:
                    if not filter_fn(row):
                        continue
                    buy_price = opt.price_at(buy_rows, buy_time)
                    sell_price = opt.price_at(sell_rows, sell_time)
                    if buy_price and sell_price:
                        values.append(sell_price / buy_price - 1)
                if not values:
                    continue
                avg = sum(values) / len(values)
                rec = {
                    "分类": label,
                    "买入时间": buy_time,
                    "卖出时间": sell_time,
                    "交易数": len(values),
                    "平均收益率": avg,
                    "中位数收益率": statistics.median(values),
                    "胜率": sum(v > 0 for v in values) / len(values),
                    "最大单笔": max(values),
                    "最差单笔": min(values),
                }
                if best is None or rec["平均收益率"] > best["平均收益率"]:
                    best = rec
        if best:
            out_rows.append(best)

    with OUT.open("w", encoding="utf-8-sig", newline="") as handle:
        fields = ["分类", "买入时间", "卖出时间", "交易数", "平均收益率", "中位数收益率", "胜率", "最大单笔", "最差单笔"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in out_rows:
            formatted = row.copy()
            for key in ["平均收益率", "中位数收益率", "胜率", "最大单笔", "最差单笔"]:
                formatted[key] = pct(formatted[key])
            writer.writerow(formatted)

    for row in out_rows:
        print(row["分类"], row["买入时间"], row["卖出时间"], row["交易数"], pct(row["平均收益率"]), pct(row["中位数收益率"]), pct(row["胜率"]))


if __name__ == "__main__":
    main()
