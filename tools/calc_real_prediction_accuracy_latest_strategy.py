import csv
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "prediction_tracking" / "daily_predictions.csv"
REPORT = ROOT / "reports" / "真实预测票准确率_按最新策略口径_2026-07-01.md"
OUT = ROOT / "prediction_tracking" / "real_prediction_accuracy_latest_strategy.csv"


def is_rule(row):
    return not row["预测类型"].startswith("非规则")


def bucket(row):
    prediction_type = row["预测类型"]
    if prediction_type.startswith("稳健观察"):
        return "稳健观察"
    if prediction_type.startswith("核心承接"):
        return "核心承接"
    if prediction_type.startswith("弹性进攻"):
        return "弹性进攻"
    if prediction_type.startswith("非规则"):
        return "非规则票"
    return "其他规则票"


def weight(prediction_type):
    if prediction_type.startswith("核心承接"):
        return 1.5
    if prediction_type.startswith("弹性进攻"):
        return 0.8
    return 1.0


def pct(value):
    return f"{value * 100:.1f}%"


def summarize(rows):
    total = len(rows)
    hit = sum(row["复盘结果"] == "命中" for row in rows)
    partial = sum(row["复盘结果"] == "部分命中" for row in rows)
    miss = sum(row["复盘结果"] == "未命中" for row in rows)
    w_total = sum(weight(row["预测类型"]) for row in rows)
    w_hit = sum(weight(row["预测类型"]) for row in rows if row["复盘结果"] == "命中")
    w_adj = sum(
        weight(row["预测类型"])
        * (1 if row["复盘结果"] == "命中" else 0.5 if row["复盘结果"] == "部分命中" else 0)
        for row in rows
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


def line(label, stats):
    return (
        f"| {label} | {stats['总数']} | {stats['命中']} | {stats['部分命中']} | {stats['未命中']} | "
        f"{stats['严格命中率']} | {stats['调整后命中率']} | {stats['调整后加权命中率']} |"
    )


def main():
    with LEDGER.open(encoding="utf-8-sig", newline="") as handle:
        all_rows = list(csv.DictReader(handle))

    reviewed = [row for row in all_rows if row.get("复盘结果") in {"命中", "部分命中", "未命中"}]
    pending = [row for row in all_rows if row.get("复盘结果") == "待复盘"]

    groups = {
        "全量真实预测": reviewed,
        "规则票": [row for row in reviewed if is_rule(row)],
        "非规则票": [row for row in reviewed if not is_rule(row)],
    }

    type_groups = defaultdict(list)
    date_groups = defaultdict(list)
    period_groups = defaultdict(list)
    for row in reviewed:
        type_groups[bucket(row)].append(row)
        date_groups[row["目标日期"]].append(row)
        period_groups["2026-06-22策略调整前" if row["目标日期"] <= "2026/6/22" else "2026-06-22策略调整后"].append(row)

    csv_rows = []
    for label, rows in groups.items():
        csv_rows.append({"分类": label, **summarize(rows)})
    for label in ["稳健观察", "核心承接", "弹性进攻", "其他规则票", "非规则票"]:
        csv_rows.append({"分类": label, **summarize(type_groups[label])})
    for label in ["2026-06-22策略调整前", "2026-06-22策略调整后"]:
        csv_rows.append({"分类": label, **summarize(period_groups[label])})

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8-sig", newline="") as handle:
        fields = ["分类", "总数", "命中", "部分命中", "未命中", "严格命中率", "调整后命中率", "严格加权命中率", "调整后加权命中率"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(csv_rows)

    overview_md = "\n".join(line(label, summarize(rows)) for label, rows in groups.items())
    type_md = "\n".join(
        line(label, summarize(type_groups[label]))
        for label in ["稳健观察", "核心承接", "弹性进攻", "其他规则票", "非规则票"]
    )
    period_md = "\n".join(line(label, summarize(period_groups[label])) for label in ["2026-06-22策略调整前", "2026-06-22策略调整后"])
    date_md = "\n".join(line(label, summarize(date_groups[label])) for label in sorted(date_groups))

    stable = summarize(type_groups["稳健观察"])
    core = summarize(type_groups["核心承接"])
    nonrule = summarize(type_groups["非规则票"])
    pending_0702 = [row for row in pending if row["目标日期"] == "2026/7/2"]

    REPORT.write_text(
        f"""# 真实预测票准确率 - 按最新策略口径

> 统计范围：`prediction_tracking/daily_predictions.csv` 中已复盘的真实预测票；不包含历史倒推票。

## 总体结果

| 口径 | 总数 | 命中 | 部分命中 | 未命中 | 严格命中率 | 调整后命中率 | 调整后加权命中率 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
{overview_md}

## 按最新策略类型拆分

| 类型 | 总数 | 命中 | 部分命中 | 未命中 | 严格命中率 | 调整后命中率 | 调整后加权命中率 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
{type_md}

## 阶段对比

| 阶段 | 总数 | 命中 | 部分命中 | 未命中 | 严格命中率 | 调整后命中率 | 调整后加权命中率 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
{period_md}

## 每日表现

| 目标日期 | 总数 | 命中 | 部分命中 | 未命中 | 严格命中率 | 调整后命中率 | 调整后加权命中率 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
{date_md}

## 策略解读

- 最新策略真正生成的第一批票是目标日 2026/7/2，目前仍有 {len(pending_0702)} 只待复盘，不纳入本次准确率。
- 已复盘真实票中，稳健观察调整后命中率为 {stable['调整后命中率']}，核心承接为 {core['调整后命中率']}，非规则票为 {nonrule['调整后命中率']}。
- 按最新策略，后续应继续提高稳健观察占比，减少核心承接和非规则高弹性票对整体胜率的拖累。
""",
        encoding="utf-8",
    )
    print(REPORT)
    print(OUT)
    print(summarize(reviewed))


if __name__ == "__main__":
    main()
