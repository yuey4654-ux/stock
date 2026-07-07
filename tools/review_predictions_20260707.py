import csv
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "prediction_tracking" / "daily_predictions.csv"
FULL_SUMMARY = ROOT / "prediction_tracking" / "daily_review_summary.csv"
RULE_SUMMARY = ROOT / "prediction_tracking" / "rule_based_daily_summary.csv"
FULL_MD = ROOT / "prediction_tracking" / "daily_review_summary.md"
RULE_MD = ROOT / "prediction_tracking" / "rule_based_daily_summary.md"
REPORT = ROOT / "reports" / "预测命中复盘_2026-07-07.md"
WORKBENCH = ROOT / "每日交易工作台"

TARGET = "2026/7/7"
TARGET_DASH = "2026-07-07"
PREDICTION_DASH = "2026-07-07"


REVIEWS = {
    "600276": {
        "收盘价": "55.36",
        "涨跌幅": "-2.48%",
        "是否触发": "否",
        "是否失效": "否",
        "复盘结果": "部分命中",
        "复盘备注": "V2.1正式规则票。收盘55.36、-2.48%；低点54.88短暂跌破55.2承接下沿但未破53.3降级线，收盘回到55.2-56.2承接区内；最高56.50未站回57.4确认位，守承接但未转强，记部分命中。",
    },
    "688981": {
        "收盘价": "145.42",
        "涨跌幅": "+0.99%",
        "是否触发": "是",
        "是否失效": "否",
        "复盘结果": "部分命中",
        "复盘备注": "V2.1正式规则票。收盘145.42、+0.99%；低点140.16守住139.0-142.5承接区，盘中最高149.51站上145.8确认位，但收盘略低于145.8，未形成收盘确认，记部分命中。",
    },
    "300059": {
        "收盘价": "20.29",
        "涨跌幅": "-4.20%",
        "是否触发": "否",
        "是否失效": "否",
        "复盘结果": "未命中",
        "复盘备注": "V2.1条件观察票。收盘20.29、-4.20%；低点20.16跌破20.6-21.0承接区，尾盘未站回21.45升级条件，未跌破19.9降级线；条件观察未兑现。",
    },
    "000977": {
        "收盘价": "71.06",
        "涨跌幅": "+1.94%",
        "是否触发": "是",
        "是否失效": "否",
        "复盘结果": "命中",
        "复盘备注": "V2.1条件观察票兑现。收盘71.06、+1.94%；低点68.70守住67.0-68.5承接区上方，盘中最高73.23且收盘站回70.5升级条件，AI服务器条件观察兑现。按全量记命中，但不作为正式规则票放宽依据。",
    },
    "688525": {
        "收盘价": "425.00",
        "涨跌幅": "-6.53%",
        "是否触发": "否",
        "是否失效": "是",
        "复盘结果": "未命中",
        "复盘备注": "V2.1非规则观察票。收盘425.00、-6.53%；最高439.88未站回468，低点416.01跌破435降级线和420深失效位，存储芯片非规则观察失败。",
    },
}


def read_csv(path):
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path, rows, fields):
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(rows)


def is_non_rule(row):
    return row["预测类型"].startswith("非规则")


def is_formal_rule(row):
    return (not is_non_rule(row)) and ("条件观察" not in row["预测类型"])


def weight(row):
    t = row["预测类型"]
    if t.startswith("核心承接"):
        return 1.5
    if t.startswith("弹性进攻"):
        return 0.8
    return 1.0


def summarize(rows):
    total = len(rows)
    hit = sum(r["复盘结果"] == "命中" for r in rows)
    partial = sum(r["复盘结果"] == "部分命中" for r in rows)
    miss = sum(r["复盘结果"] == "未命中" for r in rows)
    w_total = sum(weight(r) for r in rows)
    w_hit = sum(weight(r) for r in rows if r["复盘结果"] == "命中")
    w_adj = sum(weight(r) * (1 if r["复盘结果"] == "命中" else 0.5 if r["复盘结果"] == "部分命中" else 0) for r in rows)
    return {
        "总数": str(total),
        "命中": str(hit),
        "部分命中": str(partial),
        "未命中": str(miss),
        "严格命中率": f"{hit / total * 100:.1f}%" if total else "0.0%",
        "调整后命中率": f"{(hit + 0.5 * partial) / total * 100:.1f}%" if total else "0.0%",
        "严格加权命中率": f"{w_hit / w_total * 100:.1f}%" if w_total else "0.0%",
        "调整后加权命中率": f"{w_adj / w_total * 100:.1f}%" if w_total else "0.0%",
    }


def type_count(rows, prefix):
    selected = [r for r in rows if r["预测类型"].startswith(prefix)]
    return str(sum(r["复盘结果"] == "命中" for r in selected)), str(len(selected))


def other_count(rows):
    selected = [
        r
        for r in rows
        if not (
            r["预测类型"].startswith("核心承接")
            or r["预测类型"].startswith("稳健观察")
            or r["预测类型"].startswith("弹性进攻")
        )
    ]
    return str(sum(r["复盘结果"] == "命中" for r in selected)), str(len(selected))


def upsert_summary(path, row, key="目标日期"):
    rows = read_csv(path)
    fields = list(rows[0].keys()) if rows else list(row.keys())
    rows = [r for r in rows if r.get(key) != row[key]]
    rows.append(row)
    rows.sort(key=lambda r: r[key])
    write_csv(path, rows, fields)
    return rows


def write_md(path, rows):
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = list(rows[0].keys())
    lines = ["| " + " | ".join(fields) + " |", "| " + " | ".join(["---"] * len(fields)) + " |"]
    for r in rows:
        lines.append("| " + " | ".join(r.get(f, "") for f in fields) + " |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def summary_row(rows, rule_signal_key):
    s = summarize(rows)
    core_hit, core_total = type_count(rows, "核心承接")
    stable_hit, stable_total = type_count(rows, "稳健观察")
    elastic_hit, elastic_total = type_count(rows, "弹性进攻")
    other_hit, other_total = other_count(rows)
    return {
        "目标日期": TARGET_DASH,
        "预测日期": PREDICTION_DASH,
        **s,
        "核心承接命中": core_hit,
        "核心承接总数": core_total,
        "稳健观察命中": stable_hit,
        "稳健观察总数": stable_total,
        "弹性进攻命中": elastic_hit,
        "弹性进攻总数": elastic_total,
        "其他类型命中": other_hit,
        "其他类型总数": other_total,
        "最佳预测": "浪潮信息; 中芯国际",
        "最差预测": "东方财富; 佰维存储",
        "主要误差": "V2.1正式规则票方向较稳但收盘确认不足；条件观察票浪潮信息兑现，东方财富失败；非规则存储高波动票跌破深失效。",
        rule_signal_key: "是",
        "下一步规则调整": "继续保留V2.1分层出票：正式规则票2-3只，条件观察票1-2只；医药和半导体正式票必须收盘站回确认位才算命中，存储等高波动票不参与主策略放宽。",
        "报告文件": "reports/预测命中复盘_2026-07-07.md",
    }


def main():
    ledger = read_csv(LEDGER)
    fields = list(ledger[0].keys())
    for row in ledger:
        if row["目标日期"] == TARGET and row["代码"] in REVIEWS:
            row.update(REVIEWS[row["代码"]])
    write_csv(LEDGER, ledger, fields)

    day_rows = [r for r in ledger if r["目标日期"] == TARGET]
    legacy_rule_rows = [r for r in day_rows if not is_non_rule(r)]
    formal_rule_rows = [r for r in day_rows if is_formal_rule(r)]

    full = summarize(day_rows)
    legacy_rule = summarize(legacy_rule_rows)
    formal_rule = summarize(formal_rule_rows)

    full_rows = upsert_summary(FULL_SUMMARY, summary_row(day_rows, "策略提醒"))
    rule_rows_summary = upsert_summary(RULE_SUMMARY, summary_row(legacy_rule_rows, "规则调整信号"))
    write_md(FULL_MD, full_rows)
    write_md(RULE_MD, rule_rows_summary)

    REPORT.write_text(
        f"""# 预测命中复盘_2026-07-07

## V2.1 分层复盘

- 正式规则票：恒瑞医药、中芯国际，2只均为部分命中。
- 条件观察票：东方财富未兑现，浪潮信息兑现。
- 非规则观察票：佰维存储未命中并跌破深失效。

## 信息前置快照复核

- 盘前判断偏向医药稳健、半导体修复、AI服务器条件观察，整体方向比 7月6日更收敛。
- 医药和半导体正式票守住了承接或大部分承接，但收盘确认不足，没有形成严格命中。
- AI服务器条件观察中，浪潮信息满足回踩不破和收盘站回升级条件，验证了 V2.1 保留覆盖票的价值。

## 总命中率

| 口径 | 总数 | 命中 | 部分命中 | 未命中 | 严格命中率 | 调整后命中率 | 调整后加权命中率 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 全量覆盖票 | {full['总数']} | {full['命中']} | {full['部分命中']} | {full['未命中']} | {full['严格命中率']} | {full['调整后命中率']} | {full['调整后加权命中率']} |
| 规则票旧口径 | {legacy_rule['总数']} | {legacy_rule['命中']} | {legacy_rule['部分命中']} | {legacy_rule['未命中']} | {legacy_rule['严格命中率']} | {legacy_rule['调整后命中率']} | {legacy_rule['调整后加权命中率']} |
| V2.1正式规则票 | {formal_rule['总数']} | {formal_rule['命中']} | {formal_rule['部分命中']} | {formal_rule['未命中']} | {formal_rule['严格命中率']} | {formal_rule['调整后命中率']} | {formal_rule['调整后加权命中率']} |

## 逐票复盘

| 排名 | 股票 | 层级 | 收盘/涨跌幅 | 结果 | 复盘要点 |
| ---: | --- | --- | --- | --- | --- |
| 1 | 恒瑞医药 | 正式规则票 | 55.36 / -2.48% | 部分命中 | 收盘回到承接区，但未站回57.4确认位。 |
| 2 | 中芯国际 | 正式规则票 | 145.42 / +0.99% | 部分命中 | 低点守承接区，盘中触发，收盘略低于145.8确认位。 |
| 3 | 东方财富 | 条件观察 | 20.29 / -4.20% | 未命中 | 跌破承接区，尾盘未站回21.45，条件观察未兑现。 |
| 4 | 浪潮信息 | 条件观察 | 71.06 / +1.94% | 命中 | 守住承接区并收盘站回70.5，条件观察兑现。 |
| 5 | 佰维存储 | 非规则观察 | 425.00 / -6.53% | 未命中 | 未触发468，跌破435和420深失效。 |

## 主要结论

- V2.1 分层机制比 V2 更合理：正式票没有大幅失效，条件观察票保留了浪潮信息这类机会。
- 正式规则票仍缺严格命中，说明“收盘确认位”可以继续保留，不能放松。
- 非规则高波动票佰维存储失败，说明存储/高弹性半导体仍不适合进入正式规则票。

## 明日规则调整建议

- 继续 V2.1，不回退。
- 正式规则票保持 2-3 只，条件观察票保留 1-2 只。
- 医药、半导体若只守支撑不收回确认位，仍最多部分命中。
- AI服务器方向可继续保留条件观察，但高开超过 3% 不追。
""",
        encoding="utf-8",
    )

    shutil.copyfile(LEDGER, WORKBENCH / "03_每日预测台账.csv")
    shutil.copyfile(RULE_SUMMARY, WORKBENCH / "04_规则票复盘统计.csv")
    shutil.copyfile(RULE_MD, WORKBENCH / "04_规则票复盘统计.md")
    shutil.copyfile(FULL_SUMMARY, WORKBENCH / "05_全量复盘统计.csv")
    shutil.copyfile(FULL_MD, WORKBENCH / "05_全量复盘统计.md")
    print(REPORT)
    print(full)
    print(legacy_rule)
    print(formal_rule)


if __name__ == "__main__":
    main()
