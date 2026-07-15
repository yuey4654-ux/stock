import csv
import shutil
from collections import defaultdict
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRED = ROOT / "prediction_tracking"
REPORTS = ROOT / "reports"
WORKBENCH = ROOT / "每日交易工作台"

A_LEDGER = PRED / "daily_predictions.csv"
HK_LEDGER = PRED / "hk_daily_predictions.csv"
SUMMARY_CSV = PRED / "since_inception_accuracy_summary.csv"
SUMMARY_MD = PRED / "since_inception_accuracy_summary.md"
DAILY_CSV = PRED / "since_inception_daily_accuracy.csv"
DAILY_MD = PRED / "since_inception_daily_accuracy.md"

REVIEWED_RESULTS = {"命中", "部分命中", "未命中"}


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(rows)


def parse_date(value: str) -> datetime:
    for pattern in ("%Y/%m/%d", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, pattern)
        except ValueError:
            continue
    raise ValueError(f"无法识别日期: {value}")


def iso_date(value: str) -> str:
    return parse_date(value).strftime("%Y-%m-%d")


def is_hk_in_main_ledger(row: dict) -> bool:
    return row.get("代码", "").endswith(".HK") or "港股" in row.get("市场", "")


def is_rule(row: dict) -> bool:
    return not row.get("预测类型", "").startswith("非规则")


def weight(row: dict) -> float:
    kind = row.get("预测类型", "")
    if kind.startswith("核心承接"):
        return 1.5
    if kind.startswith("弹性进攻") or kind.startswith("弹性观察"):
        return 0.8
    return 1.0


def pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def summarize(rows: list[dict]) -> dict:
    total = len(rows)
    hit = sum(row.get("复盘结果") == "命中" for row in rows)
    partial = sum(row.get("复盘结果") == "部分命中" for row in rows)
    miss = sum(row.get("复盘结果") == "未命中" for row in rows)
    weighted_total = sum(weight(row) for row in rows)
    weighted_hit = sum(weight(row) for row in rows if row.get("复盘结果") == "命中")
    weighted_adjusted = sum(
        weight(row) * (1 if row.get("复盘结果") == "命中" else 0.5 if row.get("复盘结果") == "部分命中" else 0)
        for row in rows
    )
    return {
        "总数": str(total),
        "命中": str(hit),
        "部分命中": str(partial),
        "未命中": str(miss),
        "严格命中率": pct(hit / total) if total else "0.0%",
        "调整后命中率": pct((hit + 0.5 * partial) / total) if total else "0.0%",
        "严格加权命中率": pct(weighted_hit / weighted_total) if weighted_total else "0.0%",
        "调整后加权命中率": pct(weighted_adjusted / weighted_total) if weighted_total else "0.0%",
    }


def bucket(row: dict) -> str:
    kind = row.get("预测类型", "")
    for prefix, label in (
        ("核心承接", "核心承接"),
        ("稳健观察", "稳健观察"),
        ("弹性进攻", "弹性进攻"),
        ("弹性观察", "弹性观察"),
        ("条件观察", "条件观察"),
        ("风险降级", "风险降级"),
        ("轮动备选", "轮动备选"),
        ("非规则", "非规则票"),
    ):
        if kind.startswith(prefix):
            return label
    return "其他类型"


def type_count(rows: list[dict], prefix: str) -> tuple[str, str]:
    selected = [row for row in rows if row.get("预测类型", "").startswith(prefix)]
    return str(sum(row.get("复盘结果") == "命中" for row in selected)), str(len(selected))


def other_count(rows: list[dict]) -> tuple[str, str]:
    selected = [
        row for row in rows
        if not any(row.get("预测类型", "").startswith(prefix) for prefix in ("核心承接", "稳健观察", "弹性进攻"))
    ]
    return str(sum(row.get("复盘结果") == "命中" for row in selected)), str(len(selected))


def summary_row(label: str, rows: list[dict], source: str) -> dict:
    dates = sorted({iso_date(row["目标日期"]) for row in rows})
    core_hit, core_total = type_count(rows, "核心承接")
    stable_hit, stable_total = type_count(rows, "稳健观察")
    elastic_hit, elastic_total = type_count(rows, "弹性进攻")
    other_hit, other_total = other_count(rows)
    return {
        "统计口径": label,
        "起始日期": dates[0] if dates else "",
        "截止日期": dates[-1] if dates else "",
        **summarize(rows),
        "核心承接命中": core_hit,
        "核心承接总数": core_total,
        "稳健观察命中": stable_hit,
        "稳健观察总数": stable_total,
        "弹性进攻命中": elastic_hit,
        "弹性进攻总数": elastic_total,
        "其他类型命中": other_hit,
        "其他类型总数": other_total,
        "数据来源": source,
    }


def markdown_table(rows: list[dict], fields: list[str], numeric: set[str] | None = None) -> str:
    numeric = numeric or set()
    aligns = ["---:" if field in numeric else "---" for field in fields]
    lines = ["| " + " | ".join(fields) + " |", "| " + " | ".join(aligns) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(field, "")).replace("|", "／") for field in fields) + " |")
    return "\n".join(lines)


def build_daily_rows(market: str, rows: list[dict]) -> list[dict]:
    by_date: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_date[iso_date(row["目标日期"])].append(row)
    cumulative: list[dict] = []
    output: list[dict] = []
    for target_date in sorted(by_date):
        day_rows = by_date[target_date]
        cumulative.extend(day_rows)
        day_rule = [row for row in day_rows if is_rule(row)]
        cumulative_rule = [row for row in cumulative if is_rule(row)]
        day = summarize(day_rows)
        total = summarize(cumulative)
        rule = summarize(cumulative_rule)
        output.append({
            "目标日期": target_date,
            "市场": market,
            "当日总数": day["总数"],
            "当日命中": day["命中"],
            "当日部分命中": day["部分命中"],
            "当日未命中": day["未命中"],
            "当日严格命中率": day["严格命中率"],
            "当日调整后命中率": day["调整后命中率"],
            "累计总数": total["总数"],
            "累计命中": total["命中"],
            "累计部分命中": total["部分命中"],
            "累计未命中": total["未命中"],
            "累计严格命中率": total["严格命中率"],
            "累计调整后命中率": total["调整后命中率"],
            "累计严格加权命中率": total["严格加权命中率"],
            "累计调整后加权命中率": total["调整后加权命中率"],
            "累计规则票总数": rule["总数"],
            "累计规则票严格命中率": rule["严格命中率"],
            "累计规则票调整后命中率": rule["调整后命中率"],
            "累计规则票调整后加权命中率": rule["调整后加权命中率"],
            "当日规则票总数": str(len(day_rule)),
        })
    return output


def main() -> None:
    main_rows = [row for row in read_csv(A_LEDGER) if row.get("复盘结果") in REVIEWED_RESULTS]
    a_rows = [row for row in main_rows if not is_hk_in_main_ledger(row)]
    hk_rows = [row for row in read_csv(HK_LEDGER) if row.get("复盘结果") in REVIEWED_RESULTS]

    # Early HK predictions also exist in the main ledger. The standalone HK ledger is authoritative.
    combined_rows = a_rows + hk_rows
    scopes = [
        ("A股全量", a_rows, "daily_predictions.csv（剔除港股代码）"),
        ("A股规则票", [row for row in a_rows if is_rule(row)], "daily_predictions.csv（预测类型不以非规则开头）"),
        ("A股非规则票", [row for row in a_rows if not is_rule(row)], "daily_predictions.csv（预测类型以非规则开头）"),
        ("港股全量", hk_rows, "hk_daily_predictions.csv"),
        ("港股规则票", [row for row in hk_rows if is_rule(row)], "hk_daily_predictions.csv（预测类型不以非规则开头）"),
        ("港股非规则票", [row for row in hk_rows if not is_rule(row)], "hk_daily_predictions.csv（预测类型以非规则开头）"),
        ("A股+港股全量", combined_rows, "纯A股记录 + 港股独立台账，按市场去重"),
        ("A股+港股规则票", [row for row in combined_rows if is_rule(row)], "两市场预测类型不以非规则开头"),
    ]
    summary_rows = [summary_row(label, rows, source) for label, rows, source in scopes]
    summary_fields = list(summary_rows[0].keys())
    write_csv(SUMMARY_CSV, summary_rows, summary_fields)

    daily_rows = (
        build_daily_rows("A股", a_rows)
        + build_daily_rows("港股", hk_rows)
        + build_daily_rows("A股+港股", combined_rows)
    )
    daily_rows.sort(key=lambda row: (row["目标日期"], {"A股": 0, "港股": 1, "A股+港股": 2}[row["市场"]]))
    daily_fields = list(daily_rows[0].keys())
    write_csv(DAILY_CSV, daily_rows, daily_fields)

    numeric_summary = {"总数", "命中", "部分命中", "未命中", "核心承接命中", "核心承接总数", "稳健观察命中", "稳健观察总数", "弹性进攻命中", "弹性进攻总数", "其他类型命中", "其他类型总数"}
    SUMMARY_MD.write_text(
        "# 从首次预测开始的累计准确率\n\n"
        f"更新日期：{max(iso_date(row['目标日期']) for row in combined_rows)}\n\n"
        + markdown_table(summary_rows, summary_fields, numeric_summary)
        + "\n",
        encoding="utf-8",
    )
    DAILY_MD.write_text(
        "# 从首次预测开始的按日累计准确率\n\n"
        f"更新日期：{max(iso_date(row['目标日期']) for row in combined_rows)}\n\n"
        + markdown_table(daily_rows, daily_fields, {field for field in daily_fields if "数" in field or "命中" in field and "率" not in field})
        + "\n",
        encoding="utf-8",
    )

    type_rows = []
    for market, rows in (("A股", a_rows), ("港股", hk_rows), ("A股+港股", combined_rows)):
        groups: dict[str, list[dict]] = defaultdict(list)
        for row in rows:
            groups[bucket(row)].append(row)
        for label in ("稳健观察", "核心承接", "弹性进攻", "弹性观察", "条件观察", "风险降级", "轮动备选", "非规则票", "其他类型"):
            if groups[label]:
                type_rows.append({"市场": market, "预测类型": label, **summarize(groups[label])})

    overall_fields = ["统计口径", "起始日期", "截止日期", "总数", "命中", "部分命中", "未命中", "严格命中率", "调整后命中率", "严格加权命中率", "调整后加权命中率"]
    type_fields = ["市场", "预测类型", "总数", "命中", "部分命中", "未命中", "严格命中率", "调整后命中率", "调整后加权命中率"]
    combined = summarize(combined_rows)
    combined_rule = summarize([row for row in combined_rows if is_rule(row)])
    a_stats = summarize(a_rows)
    hk_stats = summarize(hk_rows)
    end_date = max(iso_date(row["目标日期"]) for row in combined_rows)
    report = REPORTS / f"预测票累计准确率_{end_date}.md"
    report.write_text(
        f"""# 预测票累计准确率 {end_date}

## 一句话结论

从 2026-06-15 开始至 {end_date}，去重后共复盘 {combined['总数']} 只真实预测票：{combined['命中']} 命中、{combined['部分命中']} 部分命中、{combined['未命中']} 未命中；严格命中率 {combined['严格命中率']}，调整后命中率 {combined['调整后命中率']}。规则票调整后命中率为 {combined_rule['调整后命中率']}，仍低于65%的稳定目标。

## 累计总表

{markdown_table(summary_rows, overall_fields, {'总数', '命中', '部分命中', '未命中'})}

## 按类型拆分

{markdown_table(type_rows, type_fields, {'总数', '命中', '部分命中', '未命中'})}

## 统计说明

- A股累计：{a_stats['总数']} 只，严格命中率 {a_stats['严格命中率']}，调整后命中率 {a_stats['调整后命中率']}。
- 港股累计：{hk_stats['总数']} 只，严格命中率 {hk_stats['严格命中率']}，调整后命中率 {hk_stats['调整后命中率']}。
- 早期 A 主台账中的 11 条港股记录与港股独立台账重叠；累计统计以港股独立台账为准，不重复相加。
- 严格命中率 = 命中 / 总数；调整后命中率 =（命中 + 0.5 × 部分命中）/ 总数。规则票仅排除预测类型以“非规则”开头的记录。
- 本报告只统计真实预测台账中已复盘记录，不包含历史倒推回测样本。
""",
        encoding="utf-8",
    )

    if WORKBENCH.exists():
        for source, destination in (
            (SUMMARY_CSV, WORKBENCH / "05B_预测票累计准确率.csv"),
            (SUMMARY_MD, WORKBENCH / "05B_预测票累计准确率.md"),
            (DAILY_CSV, WORKBENCH / "05C_预测票按日累计准确率.csv"),
            (DAILY_MD, WORKBENCH / "05C_预测票按日累计准确率.md"),
            (report, WORKBENCH / f"15_预测票累计准确率_{end_date}.md"),
        ):
            shutil.copyfile(source, destination)

    print(report)
    for row in summary_rows:
        print(row["统计口径"], row["总数"], row["严格命中率"], row["调整后命中率"])


if __name__ == "__main__":
    main()
