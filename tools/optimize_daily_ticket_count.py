import csv
import importlib.util
import statistics
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OPT_PATH = ROOT / "tools" / "optimize_historical_backtest_intraday_timing.py"
OUT = ROOT / "prediction_tracking" / "historical_backtest_2026_ytd" / "规则倒推票_每日买入数量优化.csv"
REPORT = ROOT / "reports" / "规则倒推票_每日买几只收益最高.md"


def load_opt():
    spec = importlib.util.spec_from_file_location("opt", OPT_PATH)
    opt = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(opt)
    return opt


def pct(v):
    return f"{v * 100:.2f}%"


def summarize(values):
    if not values:
        return {
            "交易日数": 0,
            "交易数": 0,
            "平均单票收益率": 0,
            "每日平均收益率": 0,
            "每日中位数收益率": 0,
            "胜率": 0,
            "盈利日占比": 0,
            "最大单日": 0,
            "最差单日": 0,
        }
    trade_returns = [x["收益率"] for x in values]
    by_day = defaultdict(list)
    for x in values:
        by_day[x["目标日期"]].append(x["收益率"])
    daily_returns = [sum(v) / len(v) for v in by_day.values()]
    return {
        "交易日数": len(by_day),
        "交易数": len(values),
        "平均单票收益率": sum(trade_returns) / len(trade_returns),
        "每日平均收益率": sum(daily_returns) / len(daily_returns),
        "每日中位数收益率": statistics.median(daily_returns),
        "胜率": sum(v > 0 for v in trade_returns) / len(trade_returns),
        "盈利日占比": sum(v > 0 for v in daily_returns) / len(daily_returns),
        "最大单日": max(daily_returns),
        "最差单日": min(daily_returns),
    }


def build_usable(opt):
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
    return usable


def is_stable(row):
    return row["预测类型"].startswith("稳健观察")


def scenario_returns(opt, usable, count, buy_time, sell_time, mode):
    by_day = defaultdict(list)
    for row, buy_rows, sell_date, sell_rows in usable:
        if mode == "稳健观察优先" and not is_stable(row):
            continue
        by_day[row["目标日期"]].append((row, buy_rows, sell_date, sell_rows))

    values = []
    for target, items in by_day.items():
        items.sort(key=lambda x: int(x[0]["排名"]))
        picks = items[:count]
        for row, buy_rows, sell_date, sell_rows in picks:
            buy_price = opt.price_at(buy_rows, buy_time)
            sell_price = opt.price_at(sell_rows, sell_time)
            if not buy_price or not sell_price:
                continue
            values.append(
                {
                    "目标日期": target,
                    "代码": row["代码"],
                    "名称": row["名称"],
                    "排名": row["排名"],
                    "预测类型": row["预测类型"],
                    "收益率": sell_price / buy_price - 1,
                }
            )
    return values


def main():
    opt = load_opt()
    usable = build_usable(opt)

    scenarios = [
        ("全体排名-最佳全体时间", "全体排名", "14:15", "13:15"),
        ("全体排名-稳健最佳时间", "全体排名", "09:40", "13:15"),
        ("稳健观察优先", "稳健观察优先", "09:40", "13:15"),
    ]
    out_rows = []
    for scenario_name, mode, buy_time, sell_time in scenarios:
        for count in range(1, 7):
            values = scenario_returns(opt, usable, count, buy_time, sell_time, mode)
            stats = summarize(values)
            out_rows.append(
                {
                    "场景": scenario_name,
                    "每日买入数量": count,
                    "买入时间": buy_time,
                    "卖出时间": sell_time,
                    **stats,
                }
            )

    with OUT.open("w", encoding="utf-8-sig", newline="") as handle:
        fields = [
            "场景",
            "每日买入数量",
            "买入时间",
            "卖出时间",
            "交易日数",
            "交易数",
            "平均单票收益率",
            "每日平均收益率",
            "每日中位数收益率",
            "胜率",
            "盈利日占比",
            "最大单日",
            "最差单日",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in out_rows:
            formatted = row.copy()
            for key in ["平均单票收益率", "每日平均收益率", "每日中位数收益率", "胜率", "盈利日占比", "最大单日", "最差单日"]:
                formatted[key] = pct(formatted[key])
            writer.writerow(formatted)

    def best_for(name):
        rows = [r for r in out_rows if r["场景"] == name]
        return max(rows, key=lambda x: x["每日平均收益率"])

    best_all = best_for("全体排名-最佳全体时间")
    best_stable = best_for("稳健观察优先")

    table_lines = []
    for row in out_rows:
        table_lines.append(
            f"| {row['场景']} | {row['每日买入数量']} | {row['买入时间']} | {row['卖出时间']} | {row['交易日数']} | {row['交易数']} | {pct(row['每日平均收益率'])} | {pct(row['每日中位数收益率'])} | {pct(row['盈利日占比'])} |"
        )

    REPORT.write_text(
        f"""# 规则倒推票每日买入数量优化

## 数据口径

- 使用历史倒推票中可取得5分钟数据的样本。
- 买入方式：每天按预测排名买前 N 只，每只等权。
- 卖出方式：下一交易日固定时间卖出。
- 交易成本暂未计入。

## 核心结论

| 口径 | 最佳每日数量 | 买入时间 | 次日卖出时间 | 每日平均收益率 | 每日中位数收益率 | 盈利日占比 |
| --- | ---: | --- | --- | ---: | ---: | ---: |
| 全体预测票 | {best_all['每日买入数量']} | {best_all['买入时间']} | {best_all['卖出时间']} | {pct(best_all['每日平均收益率'])} | {pct(best_all['每日中位数收益率'])} | {pct(best_all['盈利日占比'])} |
| 稳健观察票 | {best_stable['每日买入数量']} | {best_stable['买入时间']} | {best_stable['卖出时间']} | {pct(best_stable['每日平均收益率'])} | {pct(best_stable['每日中位数收益率'])} | {pct(best_stable['盈利日占比'])} |

## 全部测算结果

| 场景 | 每日买入数量 | 买入时间 | 次日卖出时间 | 交易日数 | 交易数 | 每日平均收益率 | 每日中位数收益率 | 盈利日占比 |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
{chr(10).join(table_lines)}

## 使用建议

- 若继续坚持“所有预测票按排名买”，最佳数量是 {best_all['每日买入数量']} 只，但收益质量不如只筛稳健观察。
- 按最新策略，更建议只买稳健观察票，每天最多买 {best_stable['每日买入数量']} 只，并使用 09:40 买入、次日13:15 卖出作为候选模式。
- 后续仍必须叠加高开不追、跌破失效位不买，否则会把收益重新拉低。
""",
        encoding="utf-8",
    )
    print(REPORT)
    print("best_all", best_all)
    print("best_stable", best_stable)


if __name__ == "__main__":
    main()
