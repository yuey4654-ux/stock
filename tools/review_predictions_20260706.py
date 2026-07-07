import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "prediction_tracking" / "daily_predictions.csv"
FULL_SUMMARY = ROOT / "prediction_tracking" / "daily_review_summary.csv"
RULE_SUMMARY = ROOT / "prediction_tracking" / "rule_based_daily_summary.csv"
FULL_MD = ROOT / "prediction_tracking" / "daily_review_summary.md"
RULE_MD = ROOT / "prediction_tracking" / "rule_based_daily_summary.md"
REPORT = ROOT / "reports" / "预测命中复盘_2026-07-06.md"

TARGET = "2026/7/6"
TARGET_DASH = "2026-07-06"
PREDICTION_DATE = "2026/7/6"
PREDICTION_DASH = "2026-07-06"


REVIEWS = {
    "002611": {
        "收盘价": "17.50",
        "涨跌幅": "-3.74%",
        "是否触发": "否",
        "是否失效": "否",
        "复盘结果": "未命中",
        "复盘备注": "2026-07-06收盘17.50、-3.74%；最高18.07未重新站回18.35，低点17.49跌破17.75-17.95承接区但未跌破17.35降级线，机器人承接未兑现。",
    },
    "300277": {
        "收盘价": "14.69",
        "涨跌幅": "-0.81%",
        "是否触发": "是",
        "是否失效": "否",
        "复盘结果": "部分命中",
        "复盘备注": "2026-07-06收盘14.69、-0.81%；低点14.65落在14.55-14.75承接区且未破14.35，盘中最高15.98曾站上14.96/15.05，但收盘跌回14.85下方，只能记守支撑的部分命中。",
    },
    "300433": {
        "收盘价": "51.31",
        "涨跌幅": "-1.27%",
        "是否触发": "是",
        "是否失效": "否",
        "复盘结果": "未命中",
        "复盘备注": "2026-07-06收盘51.31、-1.27%；盘中最高53.28曾站上52.90，但低点50.08跌破50.80-51.60承接区，收盘仍在51.60下方；未跌破50.00降级线，但按冲高回落规则记未命中。",
    },
    "600839": {
        "收盘价": "6.72",
        "涨跌幅": "-1.90%",
        "是否触发": "否",
        "是否失效": "否",
        "复盘结果": "未命中",
        "复盘备注": "2026-07-06收盘6.72、-1.90%；最高6.92仅触及触发位，低点6.70跌破6.78-6.88承接区，收盘未站回6.92；未跌破6.62降级线，但低价AI终端承接失败。",
    },
    "002916": {
        "收盘价": "440.20",
        "涨跌幅": "-3.14%",
        "是否触发": "否",
        "是否失效": "是",
        "复盘结果": "未命中",
        "复盘备注": "非规则票。2026-07-06收盘440.20、-3.14%；最高455.98未重新站回459，低点426.88跌破430放弃线但未破415.8深失效线，PCB/AI服务器高位承接失败。",
    },
}


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(rows)


def is_rule(row: dict) -> bool:
    return not row["预测类型"].startswith("非规则")


def weight(row: dict) -> float:
    prediction_type = row["预测类型"]
    if prediction_type.startswith("核心承接"):
        return 1.5
    if prediction_type.startswith("弹性进攻"):
        return 0.8
    return 1.0


def pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def summarize(rows: list[dict]) -> dict:
    total = len(rows)
    hit = sum(row["复盘结果"] == "命中" for row in rows)
    partial = sum(row["复盘结果"] == "部分命中" for row in rows)
    miss = sum(row["复盘结果"] == "未命中" for row in rows)
    w_total = sum(weight(row) for row in rows)
    w_hit = sum(weight(row) for row in rows if row["复盘结果"] == "命中")
    w_adjusted = sum(
        weight(row)
        * (1 if row["复盘结果"] == "命中" else 0.5 if row["复盘结果"] == "部分命中" else 0)
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
        "调整后加权命中率": pct(w_adjusted / w_total) if w_total else "0.0%",
    }


def type_count(rows: list[dict], prefix: str) -> tuple[str, str]:
    selected = [row for row in rows if row["预测类型"].startswith(prefix)]
    return str(sum(row["复盘结果"] == "命中" for row in selected)), str(len(selected))


def other_count(rows: list[dict]) -> tuple[str, str]:
    selected = [
        row
        for row in rows
        if not (
            row["预测类型"].startswith("核心承接")
            or row["预测类型"].startswith("稳健观察")
            or row["预测类型"].startswith("弹性进攻")
        )
    ]
    return str(sum(row["复盘结果"] == "命中" for row in selected)), str(len(selected))


def upsert_summary(path: Path, row: dict, key: str = "目标日期") -> list[dict]:
    rows = read_csv(path) if path.exists() else []
    fields = list(rows[0].keys()) if rows else list(row.keys())
    rows = [existing for existing in rows if existing.get(key) != row[key]]
    rows.append(row)
    rows.sort(key=lambda existing: existing[key])
    write_csv(path, rows, fields)
    return rows


def write_md(path: Path, rows: list[dict]) -> None:
    fields = list(rows[0].keys()) if rows else []
    lines = [
        "| " + " | ".join(fields) + " |",
        "| " + " | ".join(["---"] * len(fields)) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(row.get(field, "") for field in fields) + " |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_summary_row(
    rows: list[dict],
    summary: dict,
    signal_key: str,
    signal_value: str,
    worst_predictions: str,
) -> dict:
    core_hit, core_total = type_count(rows, "核心承接")
    stable_hit, stable_total = type_count(rows, "稳健观察")
    elastic_hit, elastic_total = type_count(rows, "弹性进攻")
    other_hit, other_total = other_count(rows)
    return {
        "目标日期": TARGET_DASH,
        "预测日期": PREDICTION_DASH,
        **summary,
        "核心承接命中": core_hit,
        "核心承接总数": core_total,
        "稳健观察命中": stable_hit,
        "稳健观察总数": stable_total,
        "弹性进攻命中": elastic_hit,
        "弹性进攻总数": elastic_total,
        "其他类型命中": other_hit,
        "其他类型总数": other_total,
        "最佳预测": "汽轮科技",
        "最差预测": worst_predictions,
        "主要误差": "低估了7月6日科技高位与机器人/PCB回落压力；稳健观察票虽有盘中触发，但多数收盘跌回承接区或确认位下方，说明买点确认仍不够严格。",
        signal_key: signal_value,
        "下一步规则调整": "触发原因：规则票严格命中率0.0%、调整后加权命中率12.5%，均低于阈值。建议调整：下一交易日规则票压缩至1-2只，只选板块指数不破位且个股收盘能确认的低位承接；机器人、AI终端、PCB高位票仅观察不追。适用范围：机器人、消费电子、PCB/AI服务器等高波动方向。失效条件：后续连续两日规则票调整后加权命中率回到65%以上，且无盘中触发后收盘跌回承接区样本。",
        "报告文件": "reports/预测命中复盘_2026-07-06.md",
    }


def write_report(full: dict, rule: dict) -> None:
    report = f"""# 预测命中复盘 2026-07-06

数据日期：2026-07-06 收盘；行情来源：东方财富日线接口；新闻来源：财联社、证券时报、新浪财经/每日经济新闻、MarketWatch/Investopedia/NYSE。

## 策略调整提醒

- 规则调整信号：是。
- 触发原因：规则票 4 只，命中 0 只、部分命中 1 只、未命中 3 只；严格命中率 0.0%，调整后加权命中率 12.5%，明显低于 60%/65% 阈值。
- 建议调整：下一交易日规则票压缩到 1-2 只，必须同时满足板块不破位、个股回踩承接区不破、尾盘能站回确认位；机器人、AI终端、PCB 高位票只进观察池，不作为放宽主策略依据。
- 适用范围：机器人/高端制造、AI终端、PCB/AI服务器等高波动方向。
- 失效条件：后续连续两日规则票调整后加权命中率回到 65% 以上，且不再出现“盘中触发、收盘跌回承接区”的样本。

## 新闻政策与美股影响

- 国内政策/监管：7月6日起 A 股交易新规实施，主板 ST、*ST 涨跌幅限制由 5% 调至 10%；央行开展 10000 亿元买断式逆回购，流动性对市场不是主要利空。
- 财联社与产业快讯：周末/盘前信息偏向 AI材料涨价、PCB/功率器件成本上升、创新药审评通道等，利好映射集中在创新药、部分 AI材料和半导体材料，但不能替代承接买点。
- 海外隔夜：美股因 7月3日独立日补休休市，最近一日为 7月2日；道指涨约 1.1%，但纳指跌 0.8%，费城半导体指数跌 5.44%，AI芯片链对 A 股科技高位票形成压制。
- A股盘面：沪指 -0.06%，深成指 -1.16%，创业板指 -1.77%；成交额约 3.09-3.11 万亿元。医药、银行、煤炭、猪肉偏强，机器人、PCB、元件、小金属等回落，和今天预测票方向不匹配。
- 对规则票影响：机器人/AI终端/PCB 的热点优先级下调，下一交易日预测应降数量、降弹性，只保留低位稳健观察，且禁止高开不回踩追入。

## 总体命中率

| 口径 | 总数 | 命中 | 部分命中 | 未命中 | 严格命中率 | 调整后命中率 | 调整后加权命中率 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 全量预测 | {full['总数']} | {full['命中']} | {full['部分命中']} | {full['未命中']} | {full['严格命中率']} | {full['调整后命中率']} | {full['调整后加权命中率']} |
| 规则票 | {rule['总数']} | {rule['命中']} | {rule['部分命中']} | {rule['未命中']} | {rule['严格命中率']} | {rule['调整后命中率']} | {rule['调整后加权命中率']} |

## 逐票复盘

| 代码 | 名称 | 类型 | 收盘/涨跌幅 | 结果 | 复盘要点 |
| --- | --- | --- | ---: | --- | --- |
| 002611 | 东方精工 | 稳健观察 | 17.50 / -3.74% | 未命中 | 最高18.07未站回18.35，低点跌破承接区但未破降级线，机器人承接未兑现。 |
| 300277 | 汽轮科技 | 稳健观察 | 14.69 / -0.81% | 部分命中 | 低点守住14.55-14.75承接区，盘中一度站上确认位，但收盘跌回14.85下方，只算守支撑。 |
| 300433 | 蓝思科技 | 稳健观察 | 51.31 / -1.27% | 未命中 | 盘中站上52.90后回落，收盘在51.60下方，属于触发后确认失败。 |
| 600839 | 四川长虹 | 稳健观察 | 6.72 / -1.90% | 未命中 | 最高仅触及6.92，低点跌破承接区，低价AI终端没有形成有效承接。 |
| 002916 | 深南电路 | 非规则观察-PCB/AI服务器 | 440.20 / -3.14% | 未命中 | 最高未到459确认位，低点426.88跌破430放弃线，高位PCB观察失败。 |

## 主要误差

- 低估了费城半导体大跌后对 A 股科技高位票的压力，PCB、机器人、AI终端的承接质量弱于盘前预期。
- 稳健观察仍过早接受盘中站上确认位，收盘确认不足；汽轮科技是唯一守住支撑样本，但没有转强。
- 非规则高位票深南电路跌破放弃线，说明强者承接不能只看前一日强度，必须等回踩后重新站回确认位。

## 明日规则调整建议

- 规则票数量降至 1-2 只，优先选择低位、板块当日不破 5 日线、尾盘仍能站回确认位的标的。
- 机器人、AI终端、PCB/AI服务器先降为观察，不把盘中冲高视为有效触发。
- 买点必须从“盘中触发”收紧为“回踩不破 + 收盘确认”；高开超过 3% 继续不追。
- 若美股科技或半导体继续转弱，下一交易日预测应继续降仓降数量，优先医药、银行、煤炭等当日有承接的稳健方向。
"""
    REPORT.parent.mkdir(exist_ok=True)
    REPORT.write_text(report, encoding="utf-8")


def main() -> None:
    ledger = read_csv(LEDGER)
    fields = list(ledger[0].keys())
    for row in ledger:
        if row["目标日期"] == TARGET and row["代码"] in REVIEWS and row["复盘结果"] == "待复盘":
            row.update(REVIEWS[row["代码"]])
    write_csv(LEDGER, ledger, fields)

    day_rows = [row for row in ledger if row["目标日期"] == TARGET]
    rule_rows = [row for row in day_rows if is_rule(row)]
    full = summarize(day_rows)
    rule = summarize(rule_rows)

    full_row = build_summary_row(day_rows, full, "策略提醒", "是", "深南电路; 东方精工; 蓝思科技; 四川长虹")
    rule_row = build_summary_row(rule_rows, rule, "规则调整信号", "是", "东方精工; 蓝思科技; 四川长虹")

    full_rows = upsert_summary(FULL_SUMMARY, full_row)
    rule_summary_rows = upsert_summary(RULE_SUMMARY, rule_row)
    write_md(FULL_MD, full_rows)
    write_md(RULE_MD, rule_summary_rows)
    write_report(full, rule)

    print(f"updated {LEDGER}")
    print(f"updated {FULL_SUMMARY}")
    print(f"updated {RULE_SUMMARY}")
    print(f"wrote {REPORT}")


if __name__ == "__main__":
    main()
