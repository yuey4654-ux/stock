import csv
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "prediction_tracking" / "daily_predictions.csv"
FULL_SUMMARY = ROOT / "prediction_tracking" / "daily_review_summary.csv"
RULE_SUMMARY = ROOT / "prediction_tracking" / "rule_based_daily_summary.csv"
FULL_MD = ROOT / "prediction_tracking" / "daily_review_summary.md"
RULE_MD = ROOT / "prediction_tracking" / "rule_based_daily_summary.md"
REPORT = ROOT / "reports" / "预测命中复盘_2026-07-02.md"
WORKBENCH = ROOT / "每日交易工作台"


TARGET = "2026/7/2"
TARGET_DASH = "2026-07-02"
PREDICTION_DATE = "2026/7/1"
PREDICTION_DASH = "2026-07-01"


REVIEWS = {
    "000725": {
        "收盘价": "9.10",
        "涨跌幅": "+3.76%",
        "是否触发": "是",
        "是否失效": "是",
        "复盘结果": "未命中",
        "复盘备注": "收盘9.10、+3.76%，高点9.50一度满足突破8.85，但盘中低点7.89跌破8.45降级线和8.30失效线；按失效优先规则，不能记命中。",
    },
    "600584": {
        "收盘价": "95.98",
        "涨跌幅": "-10.00%",
        "是否触发": "否",
        "是否失效": "是",
        "复盘结果": "未命中",
        "复盘备注": "收盘95.98跌停，最高101.00未到103.5-105承接区，且跌破101.5降级线和99失效线，封测稳健观察失败。",
    },
    "000100": {
        "收盘价": "5.92",
        "涨跌幅": "-3.27%",
        "是否触发": "是",
        "是否失效": "是",
        "复盘结果": "未命中",
        "复盘备注": "收盘5.92、-3.27%，盘中高点6.18短暂站上6.15，但低点5.51跌破5.86降级线和5.75失效线，且收盘未守6.10，不能记命中。",
    },
    "002371": {
        "收盘价": "841.82",
        "涨跌幅": "-10.00%",
        "是否触发": "否",
        "是否失效": "是",
        "复盘结果": "未命中",
        "复盘备注": "收盘841.82跌停，最高884.00未到920-930承接区，跌破910降级线和895失效线，核心承接完全失败。",
    },
    "002407": {
        "收盘价": "54.82",
        "涨跌幅": "-0.78%",
        "是否触发": "是",
        "是否失效": "否",
        "复盘结果": "部分命中",
        "复盘备注": "收盘54.82、-0.78%，低点52.48接近52.5-54.0承接区且未跌破51.8放弃线，但收盘未重新站回55，题材承接不够，只记部分命中。",
    },
    "605358": {
        "收盘价": "71.86",
        "涨跌幅": "-9.99%",
        "是否触发": "否",
        "是否失效": "是",
        "复盘结果": "未命中",
        "复盘备注": "收盘71.86跌停，最高75.89未触发80.5，低点跌破76.4放弃线和73.5失效线，第四代半导体观察失败。",
    },
}


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path, rows, fields):
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(rows)


def is_rule(row):
    return not row["预测类型"].startswith("非规则")


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


def upsert_summary(path, row, key="目标日期"):
    rows = read_csv(path) if path.exists() else []
    fields = list(row.keys()) if not rows else list(rows[0].keys())
    rows = [r for r in rows if r.get(key) != row[key]]
    rows.append(row)
    rows.sort(key=lambda r: r[key])
    write_csv(path, rows, fields)
    return rows


def write_md(path, rows):
    fields = list(rows[0].keys()) if rows else []
    md = "| " + " | ".join(fields) + " |\n"
    md += "| " + " | ".join(["---"] * len(fields)) + " |\n"
    for r in rows:
        md += "| " + " | ".join(r.get(f, "") for f in fields) + " |\n"
    path.write_text(md, encoding="utf-8")


def main():
    ledger = read_csv(LEDGER)
    fields = list(ledger[0].keys())
    for row in ledger:
        if row["目标日期"] == TARGET and row["代码"] in REVIEWS:
            row.update(REVIEWS[row["代码"]])
    write_csv(LEDGER, ledger, fields)

    day_rows = [r for r in ledger if r["目标日期"] == TARGET]
    rule_rows = [r for r in day_rows if is_rule(r)]

    full = summarize(day_rows)
    rule = summarize(rule_rows)
    core_hit, core_total = type_count(day_rows, "核心承接")
    stable_hit, stable_total = type_count(day_rows, "稳健观察")
    elastic_hit, elastic_total = type_count(day_rows, "弹性进攻")
    other_hit = str(sum(r["复盘结果"] == "命中" for r in day_rows if not (r["预测类型"].startswith("核心承接") or r["预测类型"].startswith("稳健观察") or r["预测类型"].startswith("弹性进攻"))))
    other_total = str(sum(1 for r in day_rows if not (r["预测类型"].startswith("核心承接") or r["预测类型"].startswith("稳健观察") or r["预测类型"].startswith("弹性进攻"))))

    full_row = {
        "目标日期": TARGET_DASH,
        "预测日期": PREDICTION_DASH,
        **full,
        "核心承接命中": core_hit,
        "核心承接总数": core_total,
        "稳健观察命中": stable_hit,
        "稳健观察总数": stable_total,
        "弹性进攻命中": elastic_hit,
        "弹性进攻总数": elastic_total,
        "其他类型命中": other_hit,
        "其他类型总数": other_total,
        "最佳预测": "多氟多",
        "最差预测": "京东方A; 长电科技; TCL科技; 北方华创; 立昂微",
        "主要误差": "新策略选出的稳健观察方向遇到电子/半导体集体杀跌，且盘中多票跌破失效线；京东方A虽收红但先破失效位，不能算有效承接。",
        "策略提醒": "是",
        "下一步规则调整": "稳健观察仍优先，但需增加大盘/板块风险闸门；若主线前一日已有多只跌停或核心票跌破失效线，次日规则票数量降至2-3只，并只选低位承接。",
        "报告文件": "reports/预测命中复盘_2026-07-02.md",
    }

    r_core_hit, r_core_total = type_count(rule_rows, "核心承接")
    r_stable_hit, r_stable_total = type_count(rule_rows, "稳健观察")
    r_elastic_hit, r_elastic_total = type_count(rule_rows, "弹性进攻")
    r_other_hit = str(sum(r["复盘结果"] == "命中" for r in rule_rows if not (r["预测类型"].startswith("核心承接") or r["预测类型"].startswith("稳健观察") or r["预测类型"].startswith("弹性进攻"))))
    r_other_total = str(sum(1 for r in rule_rows if not (r["预测类型"].startswith("核心承接") or r["预测类型"].startswith("稳健观察") or r["预测类型"].startswith("弹性进攻"))))
    rule_row = {
        "目标日期": TARGET_DASH,
        "预测日期": PREDICTION_DASH,
        **rule,
        "核心承接命中": r_core_hit,
        "核心承接总数": r_core_total,
        "稳健观察命中": r_stable_hit,
        "稳健观察总数": r_stable_total,
        "弹性进攻命中": r_elastic_hit,
        "弹性进攻总数": r_elastic_total,
        "其他类型命中": r_other_hit,
        "其他类型总数": r_other_total,
        "最佳预测": "",
        "最差预测": "京东方A; 长电科技; TCL科技; 北方华创",
        "主要误差": "规则票全部未命中，主要因电子/半导体方向开盘后承接失败，稳健票也盘中跌破失效线；核心承接北方华创跌停。",
        "规则调整信号": "是",
        "下一步规则调整": "触发强收紧：下一交易日规则票不超过3只，稳健观察必须同时满足板块不跌破5日线、个股不破前低、开盘30分钟不跌破承接区；核心承接暂停加权。",
        "报告文件": "reports/预测命中复盘_2026-07-02.md",
    }

    full_rows = upsert_summary(FULL_SUMMARY, full_row)
    rule_rows_summary = upsert_summary(RULE_SUMMARY, rule_row)
    write_md(FULL_MD, full_rows)
    write_md(RULE_MD, rule_rows_summary)

    REPORT.write_text(
        f"""# 预测命中复盘 2026-07-02

## 策略调整提醒

是。规则票 4 只全部未命中，严格命中率 0.0%，调整后加权命中率 0.0%，触发强收紧。

触发原因：稳健观察票未能抗住电子/半导体方向集体杀跌；核心承接北方华创跌停；京东方A虽然收红，但盘中跌破失效线，不能视为有效承接。

建议调整：下一交易日规则票不超过 3 只，核心承接暂停加权，稳健观察必须增加“板块不破位 + 开盘30分钟不破承接区”的盘前/盘中闸门。

适用范围：面板、封测、半导体设备、第四代半导体、氟化工/PVDF 等近期高波动方向。

失效条件：后续连续 2 个交易日规则票调整后命中率重新站上 65%，且稳健观察不再盘中跌破失效位。

## 总体结果

| 口径 | 总数 | 命中 | 部分命中 | 未命中 | 严格命中率 | 调整后命中率 | 调整后加权命中率 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 全量 | {full['总数']} | {full['命中']} | {full['部分命中']} | {full['未命中']} | {full['严格命中率']} | {full['调整后命中率']} | {full['调整后加权命中率']} |
| 规则票 | {rule['总数']} | {rule['命中']} | {rule['部分命中']} | {rule['未命中']} | {rule['严格命中率']} | {rule['调整后命中率']} | {rule['调整后加权命中率']} |

## 逐票复盘

| 股票 | 类型 | 收盘/涨跌幅 | 结果 | 复盘要点 |
| --- | --- | --- | --- | --- |
| 京东方A | 稳健观察 | 9.10 / +3.76% | 未命中 | 盘中跌破8.45和8.30失效线，虽收红但不算有效承接。 |
| 长电科技 | 稳健观察 | 95.98 / -10.00% | 未命中 | 跌停，未到承接区，跌破101.5和99。 |
| TCL科技 | 稳健观察 | 5.92 / -3.27% | 未命中 | 盘中短暂触发，但跌破5.86和5.75，收盘未守6.10。 |
| 北方华创 | 核心承接 | 841.82 / -10.00% | 未命中 | 跌停，未触发920-930承接，跌破910和895。 |
| 多氟多 | 非规则博弈 | 54.82 / -0.78% | 部分命中 | 回踩接近52.5-54.0且未破51.8，但收盘未重新站回55。 |
| 立昂微 | 非规则观察 | 71.86 / -9.99% | 未命中 | 跌停，未触发80.5，跌破76.4和73.5。 |

## 主要误差

- 低估了电子/半导体方向隔日分化风险，稳健观察票也出现盘中深破失效线。
- 新策略提高了稳健观察占比，但还缺少“大盘/板块风险闸门”。
- 核心承接在弱势日仍然容易出现大幅补跌，北方华创样本说明核心票不能只看前一日强度。

## 明日规则调整建议

- 规则票数量降至 2-3 只。
- 核心承接暂停作为第一优先级，除非板块和个股同时修复。
- 稳健观察增加盘中确认：开盘30分钟不跌破承接区，且板块指数不继续破位。
- 非规则高波动票只记录，不参与主策略加权判断。
""",
        encoding="utf-8",
    )

    shutil.copyfile(LEDGER, WORKBENCH / "03_每日预测台账.csv")
    shutil.copyfile(RULE_SUMMARY, WORKBENCH / "04_规则票复盘统计.csv")
    shutil.copyfile(RULE_MD, WORKBENCH / "04_规则票复盘统计.md")
    shutil.copyfile(FULL_SUMMARY, WORKBENCH / "05_全量复盘统计.csv")
    shutil.copyfile(FULL_MD, WORKBENCH / "05_全量复盘统计.md")
    print(REPORT)
    print(full_row)
    print(rule_row)


if __name__ == "__main__":
    main()
