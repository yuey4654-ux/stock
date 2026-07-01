import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


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
    miss = total - hit - partial
    w_total = sum(weight(r["预测类型"]) for r in rows)
    w_hit = sum(weight(r["预测类型"]) for r in rows if r["复盘结果"] == "命中")
    w_adj = sum(
        weight(r["预测类型"])
        * (1 if r["复盘结果"] == "命中" else 0.5 if r["复盘结果"] == "部分命中" else 0)
        for r in rows
    )
    return total, hit, partial, miss, hit / total, (hit + 0.5 * partial) / total, w_hit / w_total, w_adj / w_total


def fmt(value):
    return f"{value * 100:.1f}%"


def main():
    dirs = [
        ROOT / "prediction_tracking" / "historical_backtest_2026_05",
        ROOT / "prediction_tracking" / "historical_backtest_2026_6正式预测前",
    ]
    rows = []
    for directory in dirs:
        for path in directory.glob("*.csv"):
            if "预测与复盘台账" not in path.name:
                continue
            with path.open(encoding="utf-8-sig", newline="") as handle:
                rows.extend(csv.DictReader(handle))

    total = summarize(rows)
    type_lines = []
    for prediction_type in ["核心承接", "稳健观察", "弹性进攻"]:
        stats = summarize([r for r in rows if r["预测类型"] == prediction_type])
        type_lines.append(
            f"| {prediction_type} | {stats[0]} | {stats[1]} | {stats[2]} | {stats[3]} | {fmt(stats[4])} | {fmt(stats[5])} |"
        )

    report = ROOT / "reports" / "规则倒推回测_2026年5月至6月正式预测前汇总.md"
    report.write_text(
        f"""# 2026年5月至6月正式预测前规则倒推汇总

> 独立回测口径：不写入现有每日预测台账，不参与当前真实预测命中率统计。

## 总体结果

| 总数 | 命中 | 部分命中 | 未命中 | 严格命中率 | 调整后命中率 | 严格加权命中率 | 调整后加权命中率 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| {total[0]} | {total[1]} | {total[2]} | {total[3]} | {fmt(total[4])} | {fmt(total[5])} | {fmt(total[6])} | {fmt(total[7])} |

## 分类型结果

| 类型 | 总数 | 命中 | 部分命中 | 未命中 | 严格命中率 | 调整后命中率 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
{chr(10).join(type_lines)}

## 结论

- 5月是当前倒推样本中表现最好的一段，说明规则在趋势延续和热点持续环境中更有效。
- 6月正式预测前转弱，说明只靠趋势结构选股会在分化日明显失真。
- 稳健观察仍是最稳定类型；核心承接需要继续加高位过热过滤；弹性进攻只能小仓或作为非主线观察。
""",
        encoding="utf-8",
    )
    print(report)
    print(total)


if __name__ == "__main__":
    main()
