import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "prediction_tracking" / "historical_backtest_latest_strategy_2026_01_05_summary"


def weight(prediction_type):
    if prediction_type == "核心承接":
        return 1.5
    if prediction_type == "弹性进攻":
        return 0.8
    return 1.0


def pct(value):
    return f"{value * 100:.1f}%"


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


def main():
    rows = []
    all_ledger = []
    for month in range(1, 6):
        batch = f"2026年{month}月最新策略倒推"
        ledger = (
            ROOT
            / "prediction_tracking"
            / f"historical_backtest_latest_strategy_2026_{month:02d}"
            / f"{batch}预测与复盘台账.csv"
        )
        if not ledger.exists():
            continue
        with ledger.open("r", encoding="utf-8-sig", newline="") as f:
            data = list(csv.DictReader(f))
        all_ledger.extend(data)
        s = summarize(data)
        rows.append(
            {
                "月份": f"2026-{month:02d}",
                **s,
                "报告文件": f"reports/最新策略倒推回测_2026年{month}月.md",
            }
        )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fields = [
        "月份",
        "总数",
        "命中",
        "部分命中",
        "未命中",
        "严格命中率",
        "调整后命中率",
        "严格加权命中率",
        "调整后加权命中率",
        "报告文件",
    ]
    csv_path = OUT_DIR / "2026年1-5月最新策略倒推总览.csv"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    lines = [
        "# 2026年1-5月最新策略倒推总览",
        "",
        "| " + " | ".join(fields) + " |",
        "| " + " | ".join(["---"] * len(fields)) + " |",
    ]
    for r in rows:
        lines.append("| " + " | ".join(str(r[c]) for c in fields) + " |")

    if all_ledger:
        total = summarize(all_ledger)
        lines += [
            "",
            "## 合计",
            "",
            f"- 总数：{total['总数']}",
            f"- 命中：{total['命中']}",
            f"- 部分命中：{total['部分命中']}",
            f"- 未命中：{total['未命中']}",
            f"- 严格命中率：{total['严格命中率']}",
            f"- 调整后命中率：{total['调整后命中率']}",
            f"- 严格加权命中率：{total['严格加权命中率']}",
            f"- 调整后加权命中率：{total['调整后加权命中率']}",
        ]
    md_path = OUT_DIR / "2026年1-5月最新策略倒推总览.md"
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(csv_path)
    print(md_path)
    for row in rows:
        print(row)


if __name__ == "__main__":
    main()
