import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "prediction_tracking" / "strategy_accuracy_comparison_2026_01_05"
REPORT_DIR = ROOT / "reports"


def weight(prediction_type):
    if prediction_type == "核心承接":
        return 1.5
    if prediction_type == "弹性进攻":
        return 0.8
    return 1.0


def ratio(numerator, denominator):
    return numerator / denominator if denominator else 0


def pct(value):
    return f"{value * 100:.1f}%"


def pct_point(value):
    sign = "+" if value > 0 else ""
    return f"{sign}{value * 100:.1f}pct"


def read_csv(path):
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


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
    strict_rate = ratio(hit, total)
    adjusted_rate = ratio(hit + 0.5 * partial, total)
    strict_weighted_rate = ratio(w_hit, w_total)
    adjusted_weighted_rate = ratio(w_adj, w_total)
    return {
        "总数": total,
        "命中": hit,
        "部分命中": partial,
        "未命中": miss,
        "严格命中率_数值": strict_rate,
        "调整后命中率_数值": adjusted_rate,
        "严格加权命中率_数值": strict_weighted_rate,
        "调整后加权命中率_数值": adjusted_weighted_rate,
        "严格命中率": pct(strict_rate),
        "调整后命中率": pct(adjusted_rate),
        "严格加权命中率": pct(strict_weighted_rate),
        "调整后加权命中率": pct(adjusted_weighted_rate),
    }


def previous_ledger_path(month):
    return (
        ROOT
        / "prediction_tracking"
        / f"historical_backtest_2026_{month:02d}"
        / f"2026年{month}月规则倒推预测与复盘台账.csv"
    )


def latest_ledger_path(month):
    return (
        ROOT
        / "prediction_tracking"
        / f"historical_backtest_latest_strategy_2026_{month:02d}"
        / f"2026年{month}月最新策略倒推预测与复盘台账.csv"
    )


def strategy_row(month, strategy_name, ledger_path):
    rows = read_csv(ledger_path)
    s = summarize(rows)
    return {
        "月份": f"2026-{month:02d}",
        "策略": strategy_name,
        "数据源": str(ledger_path.relative_to(ROOT)).replace("\\", "/"),
        **{k: v for k, v in s.items() if not k.endswith("_数值")},
        "_strict": s["严格命中率_数值"],
        "_adjusted": s["调整后命中率_数值"],
        "_strict_weighted": s["严格加权命中率_数值"],
        "_adjusted_weighted": s["调整后加权命中率_数值"],
    }


def compare_row(previous, latest):
    total_delta = latest["总数"] - previous["总数"]
    hit_delta = latest["命中"] - previous["命中"]
    partial_delta = latest["部分命中"] - previous["部分命中"]
    miss_delta = latest["未命中"] - previous["未命中"]
    strict_delta = latest["_strict"] - previous["_strict"]
    adjusted_delta = latest["_adjusted"] - previous["_adjusted"]
    strict_weighted_delta = latest["_strict_weighted"] - previous["_strict_weighted"]
    adjusted_weighted_delta = latest["_adjusted_weighted"] - previous["_adjusted_weighted"]
    return {
        "月份": latest["月份"],
        "旧策略总数": previous["总数"],
        "新策略总数": latest["总数"],
        "出票减少": -total_delta,
        "旧策略命中": previous["命中"],
        "新策略命中": latest["命中"],
        "命中数变化": hit_delta,
        "旧策略部分命中": previous["部分命中"],
        "新策略部分命中": latest["部分命中"],
        "部分命中变化": partial_delta,
        "旧策略未命中": previous["未命中"],
        "新策略未命中": latest["未命中"],
        "未命中变化": miss_delta,
        "旧策略严格命中率": previous["严格命中率"],
        "新策略严格命中率": latest["严格命中率"],
        "严格命中率变化": pct_point(strict_delta),
        "旧策略调整后命中率": previous["调整后命中率"],
        "新策略调整后命中率": latest["调整后命中率"],
        "调整后命中率变化": pct_point(adjusted_delta),
        "旧策略严格加权命中率": previous["严格加权命中率"],
        "新策略严格加权命中率": latest["严格加权命中率"],
        "严格加权变化": pct_point(strict_weighted_delta),
        "旧策略调整后加权命中率": previous["调整后加权命中率"],
        "新策略调整后加权命中率": latest["调整后加权命中率"],
        "调整后加权变化": pct_point(adjusted_weighted_delta),
        "直观结论": "新策略更好" if adjusted_delta > 0 else "旧策略更好" if adjusted_delta < 0 else "持平",
    }


def strip_hidden(row):
    return {k: v for k, v in row.items() if not k.startswith("_")}


def write_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_md_table(path, title, rows, fields):
    lines = [
        f"# {title}",
        "",
        "| " + " | ".join(fields) + " |",
        "| " + " | ".join(["---"] * len(fields)) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(field, "")).replace("|", "/") for field in fields) + " |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    strategy_rows = []
    comparison_rows = []
    previous_all = []
    latest_all = []

    for month in range(1, 6):
        previous_path = previous_ledger_path(month)
        latest_path = latest_ledger_path(month)
        previous_rows = read_csv(previous_path)
        latest_rows = read_csv(latest_path)
        previous_all.extend(previous_rows)
        latest_all.extend(latest_rows)

        previous = strategy_row(month, "旧策略：规则倒推", previous_path)
        latest = strategy_row(month, "最新策略：连续失准防守", latest_path)
        strategy_rows.extend([strip_hidden(previous), strip_hidden(latest)])
        comparison_rows.append(compare_row(previous, latest))

    previous_total = {"月份": "2026-01至2026-05", "策略": "旧策略：规则倒推", "数据源": "1-5月旧策略逐票台账合计"}
    previous_total.update({k: v for k, v in summarize(previous_all).items() if not k.endswith("_数值")})
    latest_total_hidden = summarize(latest_all)
    latest_total = {"月份": "2026-01至2026-05", "策略": "最新策略：连续失准防守", "数据源": "1-5月最新策略逐票台账合计"}
    latest_total.update({k: v for k, v in latest_total_hidden.items() if not k.endswith("_数值")})

    previous_total_for_compare = {
        **previous_total,
        "_strict": summarize(previous_all)["严格命中率_数值"],
        "_adjusted": summarize(previous_all)["调整后命中率_数值"],
        "_strict_weighted": summarize(previous_all)["严格加权命中率_数值"],
        "_adjusted_weighted": summarize(previous_all)["调整后加权命中率_数值"],
    }
    latest_total_for_compare = {
        **latest_total,
        "_strict": latest_total_hidden["严格命中率_数值"],
        "_adjusted": latest_total_hidden["调整后命中率_数值"],
        "_strict_weighted": latest_total_hidden["严格加权命中率_数值"],
        "_adjusted_weighted": latest_total_hidden["调整后加权命中率_数值"],
    }
    total_compare = compare_row(previous_total_for_compare, latest_total_for_compare)
    total_compare["月份"] = "2026-01至2026-05合计"

    strategy_rows.extend([previous_total, latest_total])
    comparison_rows.append(total_compare)

    strategy_fields = [
        "月份",
        "策略",
        "总数",
        "命中",
        "部分命中",
        "未命中",
        "严格命中率",
        "调整后命中率",
        "严格加权命中率",
        "调整后加权命中率",
        "数据源",
    ]
    comparison_fields = [
        "月份",
        "旧策略总数",
        "新策略总数",
        "出票减少",
        "旧策略命中",
        "新策略命中",
        "命中数变化",
        "旧策略部分命中",
        "新策略部分命中",
        "部分命中变化",
        "旧策略未命中",
        "新策略未命中",
        "未命中变化",
        "旧策略严格命中率",
        "新策略严格命中率",
        "严格命中率变化",
        "旧策略调整后命中率",
        "新策略调整后命中率",
        "调整后命中率变化",
        "旧策略严格加权命中率",
        "新策略严格加权命中率",
        "严格加权变化",
        "旧策略调整后加权命中率",
        "新策略调整后加权命中率",
        "调整后加权变化",
        "直观结论",
    ]

    write_csv(OUT_DIR / "2026年1-5月新旧策略命中率明细台账.csv", strategy_rows, strategy_fields)
    write_csv(OUT_DIR / "2026年1-5月新旧策略命中率对比台账.csv", comparison_rows, comparison_fields)
    write_md_table(
        OUT_DIR / "2026年1-5月新旧策略命中率对比台账.md",
        "2026年1-5月新旧策略命中率对比台账",
        comparison_rows,
        comparison_fields,
    )

    report = REPORT_DIR / "新旧策略命中率对比_2026年1-5月.md"
    summary_fields = [
        "月份",
        "旧策略总数",
        "新策略总数",
        "旧策略严格命中率",
        "新策略严格命中率",
        "严格命中率变化",
        "旧策略调整后命中率",
        "新策略调整后命中率",
        "调整后命中率变化",
        "直观结论",
    ]
    lines = [
        "# 新旧策略命中率对比_2026年1-5月",
        "",
        "> 统计来源：逐票台账重新计算。旧策略读取 `prediction_tracking/historical_backtest_2026_01` 至 `_05`；最新策略读取 `prediction_tracking/historical_backtest_latest_strategy_2026_01` 至 `_05`。本报告不修改正式预测台账。",
        "",
        "## 最直观对比",
        "",
        "| " + " | ".join(summary_fields) + " |",
        "| " + " | ".join(["---"] * len(summary_fields)) + " |",
    ]
    for row in comparison_rows:
        lines.append("| " + " | ".join(str(row[field]) for field in summary_fields) + " |")

    lines += [
        "",
        "## 结论",
        "",
        f"- 1-5月合计旧策略：{total_compare['旧策略总数']}条，严格命中率{total_compare['旧策略严格命中率']}，调整后命中率{total_compare['旧策略调整后命中率']}。",
        f"- 1-5月合计新策略：{total_compare['新策略总数']}条，严格命中率{total_compare['新策略严格命中率']}，调整后命中率{total_compare['新策略调整后命中率']}。",
        f"- 新策略相对旧策略：出票减少{total_compare['出票减少']}条，严格命中率变化{total_compare['严格命中率变化']}，调整后命中率变化{total_compare['调整后命中率变化']}。",
        "- 直观判断：按 1-5 月历史倒推，旧策略胜率更高；新策略主要价值是显著减少出票和降低暴露，但不是提高命中率。",
        "",
        "## 产物",
        "",
        "- 明细台账：`prediction_tracking/strategy_accuracy_comparison_2026_01_05/2026年1-5月新旧策略命中率明细台账.csv`",
        "- 对比台账：`prediction_tracking/strategy_accuracy_comparison_2026_01_05/2026年1-5月新旧策略命中率对比台账.csv`",
        "- Markdown对比：`prediction_tracking/strategy_accuracy_comparison_2026_01_05/2026年1-5月新旧策略命中率对比台账.md`",
    ]
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(report)
    print(OUT_DIR / "2026年1-5月新旧策略命中率对比台账.csv")
    print(total_compare)


if __name__ == "__main__":
    main()
