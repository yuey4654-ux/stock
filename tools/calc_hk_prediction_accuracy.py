import csv
from collections import defaultdict
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "prediction_tracking" / "hk_daily_predictions.csv"
OUT_CSV = ROOT / "prediction_tracking" / "hk_daily_review_summary.csv"
OUT_MD = ROOT / "prediction_tracking" / "hk_daily_review_summary.md"


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(rows)


def weight(row: dict) -> float:
    prediction_type = row.get("预测类型", "")
    if prediction_type.startswith("核心承接"):
        return 1.5
    if prediction_type.startswith("弹性"):
        return 0.8
    if prediction_type.startswith("非规则"):
        return 1.0
    return 1.0


def pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def summarize(rows: list[dict]) -> dict:
    total = len(rows)
    hit = sum(row.get("复盘结果") == "命中" for row in rows)
    partial = sum(row.get("复盘结果") == "部分命中" for row in rows)
    miss = sum(row.get("复盘结果") == "未命中" for row in rows)
    w_total = sum(weight(row) for row in rows)
    w_hit = sum(weight(row) for row in rows if row.get("复盘结果") == "命中")
    w_adj = sum(
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
        "严格加权命中率": pct(w_hit / w_total) if w_total else "0.0%",
        "调整后加权命中率": pct(w_adj / w_total) if w_total else "0.0%",
    }


def market_bucket(row: dict) -> str:
    prediction_type = row.get("预测类型", "")
    if prediction_type.startswith("稳健观察"):
        return "稳健观察"
    if prediction_type.startswith("核心承接"):
        return "核心承接"
    if prediction_type.startswith("条件观察"):
        return "条件观察"
    if prediction_type.startswith("弹性"):
        return "弹性观察"
    if prediction_type.startswith("非规则"):
        return "非规则观察"
    return "其他"


def date_sort_key(value: str) -> datetime:
    for pattern in ("%Y/%m/%d", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, pattern)
        except ValueError:
            continue
    return datetime.max


def main() -> None:
    rows = read_csv(LEDGER)
    reviewed = [
        row
        for row in rows
        if row.get("是否计入准确率", "是") == "是" and row.get("复盘结果") in {"命中", "部分命中", "未命中"}
    ]
    pending = [
        row
        for row in rows
        if row.get("是否计入准确率", "是") == "是" and row.get("复盘结果") == "待复盘"
    ]

    groups: list[tuple[str, list[dict]]] = [
        ("港股全量已复盘", reviewed),
        ("港股待复盘", pending),
    ]

    by_type = defaultdict(list)
    by_date = defaultdict(list)
    for row in reviewed:
        by_type[market_bucket(row)].append(row)
        by_date[row.get("目标日期", "")].append(row)

    for label in ["稳健观察", "核心承接", "条件观察", "弹性观察", "非规则观察", "其他"]:
        groups.append((label, by_type[label]))
    for date_key in sorted((k for k in by_date if k), key=date_sort_key):
        groups.append((date_key, by_date[date_key]))

    out_rows = [{"分类": label, **summarize(group_rows)} for label, group_rows in groups]
    fields = [
        "分类",
        "总数",
        "命中",
        "部分命中",
        "未命中",
        "严格命中率",
        "调整后命中率",
        "严格加权命中率",
        "调整后加权命中率",
    ]
    write_csv(OUT_CSV, out_rows, fields)

    lines = [
        "# 港股预测准确率汇总",
        "",
        "| 分类 | 总数 | 命中 | 部分命中 | 未命中 | 严格命中率 | 调整后命中率 | 调整后加权命中率 |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in out_rows:
        lines.append(
            f"| {row['分类']} | {row['总数']} | {row['命中']} | {row['部分命中']} | {row['未命中']} | "
            f"{row['严格命中率']} | {row['调整后命中率']} | {row['调整后加权命中率']} |"
        )
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(OUT_CSV)
    print(OUT_MD)


if __name__ == "__main__":
    main()
