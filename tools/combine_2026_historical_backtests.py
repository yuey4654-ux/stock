import csv
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKTEST_DIRS = [
    ROOT / "prediction_tracking" / "historical_backtest_2026_01",
    ROOT / "prediction_tracking" / "historical_backtest_2026_02",
    ROOT / "prediction_tracking" / "historical_backtest_2026_03",
    ROOT / "prediction_tracking" / "historical_backtest_2026_04",
    ROOT / "prediction_tracking" / "historical_backtest_2026_05",
    ROOT / "prediction_tracking" / "historical_backtest_2026_6正式预测前",
]
OUT_DIR = ROOT / "prediction_tracking" / "historical_backtest_2026_ytd"
REPORT = ROOT / "reports" / "规则倒推回测_2026年汇总.md"


def weight(prediction_type):
    if prediction_type == "核心承接":
        return 1.5
    if prediction_type == "弹性进攻":
        return 0.8
    return 1.0


def fmt(value):
    return f"{value * 100:.1f}%"


def summarize(rows):
    total = len(rows)
    if total == 0:
        return {
            "总数": 0,
            "命中": 0,
            "部分命中": 0,
            "未命中": 0,
            "严格命中率": "0.0%",
            "调整后命中率": "0.0%",
            "严格加权命中率": "0.0%",
            "调整后加权命中率": "0.0%",
        }
    hit = sum(r["复盘结果"] == "命中" for r in rows)
    partial = sum(r["复盘结果"] == "部分命中" for r in rows)
    miss = total - hit - partial
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
        "严格命中率": fmt(hit / total),
        "调整后命中率": fmt((hit + 0.5 * partial) / total),
        "严格加权命中率": fmt(w_hit / w_total if w_total else 0),
        "调整后加权命中率": fmt(w_adj / w_total if w_total else 0),
    }


def read_ledgers():
    rows = []
    for directory in BACKTEST_DIRS:
        for path in directory.glob("*.csv"):
            if "预测与复盘台账" not in path.name:
                continue
            with path.open(encoding="utf-8-sig", newline="") as handle:
                for row in csv.DictReader(handle):
                    row["来源文件"] = str(path.relative_to(ROOT))
                    rows.append(row)
    rows.sort(key=lambda r: (r["目标日期"], int(r["排名"])))
    return rows


def write_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    rows = read_ledgers()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    if rows:
        fields = list(rows[0].keys())
        write_csv(OUT_DIR / "2026年规则倒推预测与复盘总台账.csv", rows, fields)

    month_rows = []
    by_month = defaultdict(list)
    by_type = defaultdict(list)
    by_rank = defaultdict(list)
    for row in rows:
        by_month[row["目标日期"][:7]].append(row)
        by_type[row["预测类型"]].append(row)
        by_rank[row["排名"]].append(row)

    for month in sorted(by_month):
        month_rows.append({"月份": month, **summarize(by_month[month])})

    type_rows = [{"预测类型": key, **summarize(value)} for key, value in sorted(by_type.items())]
    rank_rows = [{"排名": key, **summarize(value)} for key, value in sorted(by_rank.items(), key=lambda x: int(x[0]))]

    summary_fields = ["月份", "总数", "命中", "部分命中", "未命中", "严格命中率", "调整后命中率", "严格加权命中率", "调整后加权命中率"]
    write_csv(OUT_DIR / "2026年规则倒推月度准确率.csv", month_rows, summary_fields)
    write_csv(OUT_DIR / "2026年规则倒推类型准确率.csv", type_rows, ["预测类型"] + summary_fields[1:])
    write_csv(OUT_DIR / "2026年规则倒推排名准确率.csv", rank_rows, ["排名"] + summary_fields[1:])

    total = summarize(rows)
    month_md = "\n".join(
        f"| {r['月份']} | {r['总数']} | {r['命中']} | {r['部分命中']} | {r['未命中']} | {r['严格命中率']} | {r['调整后命中率']} | {r['严格加权命中率']} | {r['调整后加权命中率']} |"
        for r in month_rows
    )
    type_md = "\n".join(
        f"| {r['预测类型']} | {r['总数']} | {r['命中']} | {r['部分命中']} | {r['未命中']} | {r['严格命中率']} | {r['调整后命中率']} |"
        for r in type_rows
    )
    rank_md = "\n".join(
        f"| {r['排名']} | {r['总数']} | {r['命中']} | {r['部分命中']} | {r['未命中']} | {r['严格命中率']} | {r['调整后命中率']} |"
        for r in rank_rows
    )

    REPORT.write_text(
        f"""# 2026年规则倒推回测汇总

> 统计范围：2026-01-05 至 2026-06-12 的历史倒推票，不包含正式预测台账。

## 总体准确率

| 总数 | 命中 | 部分命中 | 未命中 | 严格命中率 | 调整后命中率 | 严格加权命中率 | 调整后加权命中率 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| {total['总数']} | {total['命中']} | {total['部分命中']} | {total['未命中']} | {total['严格命中率']} | {total['调整后命中率']} | {total['严格加权命中率']} | {total['调整后加权命中率']} |

## 月度准确率

| 月份 | 总数 | 命中 | 部分命中 | 未命中 | 严格命中率 | 调整后命中率 | 严格加权命中率 | 调整后加权命中率 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
{month_md}

## 类型准确率

| 类型 | 总数 | 命中 | 部分命中 | 未命中 | 严格命中率 | 调整后命中率 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
{type_md}

## 排名准确率

| 排名 | 总数 | 命中 | 部分命中 | 未命中 | 严格命中率 | 调整后命中率 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
{rank_md}

## 结论

- 年内倒推总体严格命中率不高，说明“只靠行情结构”的机械规则不适合直接作为无筛选买入系统。
- 稳健观察显著优于核心承接和弹性进攻，更适合成为主仓规则。
- 核心承接需要继续增加高位过热过滤、收盘确认和板块强弱过滤。
- 弹性进攻的稳定性最弱，更适合小仓、非规则或题材确认后的辅助票。
""",
        encoding="utf-8",
    )
    print(REPORT)
    print(total)


if __name__ == "__main__":
    main()
