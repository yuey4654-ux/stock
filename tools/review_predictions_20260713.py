import csv
import shutil
import subprocess
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRED = ROOT / "prediction_tracking"
REPORTS = ROOT / "reports"
WORKBENCH = ROOT / "每日交易工作台"

TARGET = "2026/7/13"
TARGET_DASH = "2026-07-13"
PREDICTION_DASH = "2026-07-12"

A_LEDGER = PRED / "daily_predictions.csv"
HK_LEDGER = PRED / "hk_daily_predictions.csv"
A_FULL_SUMMARY = PRED / "daily_review_summary.csv"
A_RULE_SUMMARY = PRED / "rule_based_daily_summary.csv"
A_FULL_MD = PRED / "daily_review_summary.md"
A_RULE_MD = PRED / "rule_based_daily_summary.md"
HK_RULE_SUMMARY = PRED / "hk_rule_based_daily_summary.csv"
HK_RULE_MD = PRED / "hk_rule_based_daily_summary.md"
A_REPORT = REPORTS / f"预测命中复盘_{TARGET_DASH}.md"
HK_REPORT = REPORTS / f"港股预测命中复盘_{TARGET_DASH}.md"


A_REVIEWS = {
    "000938": ("38.40", "-0.03%", "否", "否", "未命中", "开38.43/高40.28/低36.50/收38.40。盘中冲高后回落至36.50，未守住37.2-37.8承接区，收盘也未站回38.9；虽未跌破35.8深失效位，但标准触发和收盘确认均失败。"),
    "000063": ("40.04", "-1.21%", "否", "否", "未命中", "开41.00/高42.50/低39.58/收40.04。低点跌出40.0-40.4承接区，收盘未站回41.2；未跌破38.5深失效位，但通信修复没有形成可执行确认。"),
    "600276": ("55.75", "+0.00%", "否", "否", "部分命中", "开55.11/高56.22/低54.78/收55.75。盘中达到56.2触发位附近，但低点短暂跌出55.0-55.4承接区且收盘未站稳56.2；防守方向相对抗跌，按守住大结构但确认不足记部分命中。"),
    "600498": ("51.18", "-10.01%", "否", "是", "未命中", "开56.10/高56.10/低51.18/收51.18。开盘即转弱并收于跌停，跌破54.8深失效位；周末通信网催化没有转化为承接，条件观察失效。"),
    "600601": ("12.18", "-7.59%", "否", "是", "未命中", "开13.00/高13.94/低12.01/收12.18。盘中冲高后大幅回落，跌破12.3深失效位并收在13.1下方，典型冲高回落，条件观察未兑现。"),
    "300475": ("216.80", "-20.00%", "否", "是", "未命中", "开244.90/高253.65/低216.80/收216.80。全天未进入266-269承接区即继续下杀，跌破255深失效位并收于跌停，存储高波动风险完全暴露。"),
    "002185": ("24.13", "-4.66%", "否", "否", "未命中", "开25.07/高26.81/低23.85/收24.13。盘中冲高后跌破24.4降级线，收盘低于25.7确认位；低点略高于23.8深失效位，记未命中但不标记深失效。"),
    "000977": ("85.49", "-4.50%", "否", "是", "未命中", "开91.00/高92.21/低83.80/收85.49。高开冲高后持续回落，跌破85.8深失效位且收盘远低于90.8，AI服务器条件观察失效。"),
    "002422": ("44.80", "+1.66%", "否", "否", "部分命中", "开44.57/高46.22/低44.00/收44.80。方向偏强且收盘站上44.4，但低点没有回到43.0-43.5理想买点，未给标准低吸机会；按方向正确、执行点不完整记部分命中。"),
    "300363": ("18.05", "-2.01%", "否", "否", "部分命中", "开18.12/高18.57/低17.99/收18.05。低点触及17.7-18.0承接区上沿且未失效，但高点未到18.6、收盘也未转强；守住支撑但弹性不足，记部分命中。"),
}


HK_REVIEWS = {
    "00388.HK": ("387.60", "+0.68%", "是", "否", "命中", "开383.80/高391.20/低383.80/收387.60。低点落在382-384承接区，收盘站回386，港交所完成标准回踩与确认。"),
    "09988.HK": ("110.70", "+0.45%", "否", "否", "部分命中", "开110.80/高115.10/低110.30/收110.70。方向偏强但低点未进入109-109.8理想买点，收盘又略低于111确认位；执行条件不完整，记部分命中。"),
    "01093.HK": ("8.16", "+0.62%", "否", "否", "部分命中", "开8.11/高8.26/低7.90/收8.16。盘中跌出7.95-8.02承接区后修复，但收盘仍未站上8.18；防守方向尚可，确认不足记部分命中。"),
    "01810.HK": ("25.84", "+0.00%", "否", "否", "部分命中", "开25.84/高26.78/低25.58/收25.84。盘中突破26但收盘跌回确认位下方，且低点未给25.2-25.5标准买点；仅有盘中热度，记部分命中。"),
    "00700.HK": ("457.60", "-0.56%", "否", "否", "未命中", "开463.20/高473.80/低456.20/收457.60。冲高后收盘跌回458-461承接区下方，未站回466；虽未跌破452深失效位，但互联网平台修复确认失败。"),
    "09618.HK": ("113.20", "+2.72%", "是", "否", "命中", "开110.00/高114.50/低109.60/收113.20。低点落在109-109.8承接区，尾盘站稳111上方，京东条件观察兑现。"),
    "00981.HK": ("78.35", "-1.63%", "否", "是", "未命中", "开80.05/高84.80/低76.65/收78.35。盘中冲高后跌破76.8深失效位，收盘也未站回81.5，港股半导体承接再次失败。"),
    "01347.HK": ("172.30", "-7.12%", "否", "是", "未命中", "开185.50/高191.40/低171.00/收172.30。盘中触及191后大幅回落，跌破176深失效位并收在186下方，非规则半导体弹性样本未兑现。"),
}


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
    kind = row.get("预测类型", "")
    if kind.startswith("核心承接"):
        return 1.5
    if kind.startswith("弹性进攻") or kind.startswith("弹性观察"):
        return 0.8
    return 1.0


def summarize(rows: list[dict]) -> dict:
    total = len(rows)
    hit = sum(row.get("复盘结果") == "命中" for row in rows)
    partial = sum(row.get("复盘结果") == "部分命中" for row in rows)
    miss = sum(row.get("复盘结果") == "未命中" for row in rows)
    weighted_total = sum(weight(row) for row in rows)
    weighted_hit = sum(weight(row) for row in rows if row.get("复盘结果") == "命中")
    weighted_adjusted = sum(weight(row) * (1 if row.get("复盘结果") == "命中" else 0.5 if row.get("复盘结果") == "部分命中" else 0) for row in rows)
    return {
        "总数": str(total),
        "命中": str(hit),
        "部分命中": str(partial),
        "未命中": str(miss),
        "严格命中率": f"{hit / total * 100:.1f}%" if total else "0.0%",
        "调整后命中率": f"{(hit + 0.5 * partial) / total * 100:.1f}%" if total else "0.0%",
        "严格加权命中率": f"{weighted_hit / weighted_total * 100:.1f}%" if weighted_total else "0.0%",
        "调整后加权命中率": f"{weighted_adjusted / weighted_total * 100:.1f}%" if weighted_total else "0.0%",
    }


def is_non_rule(row: dict) -> bool:
    return row.get("预测类型", "").startswith("非规则")


def type_count(rows: list[dict], prefix: str) -> tuple[str, str]:
    selected = [row for row in rows if row.get("预测类型", "").startswith(prefix)]
    return str(sum(row.get("复盘结果") == "命中" for row in selected)), str(len(selected))


def other_count(rows: list[dict]) -> tuple[str, str]:
    selected = [row for row in rows if not any(row.get("预测类型", "").startswith(prefix) for prefix in ("核心承接", "稳健观察", "弹性进攻"))]
    return str(sum(row.get("复盘结果") == "命中" for row in selected)), str(len(selected))


def upsert_summary(path: Path, row: dict, key: str = "目标日期") -> list[dict]:
    rows = read_csv(path)
    fields = list(rows[0].keys()) if rows else list(row.keys())
    rows = [existing for existing in rows if existing.get(key) != row[key]]
    rows.append({field: row.get(field, "") for field in fields})
    rows.sort(key=lambda item: item.get(key, ""))
    write_csv(path, rows, fields)
    return rows


def write_summary_md(path: Path, title: str, rows: list[dict]) -> None:
    fields = list(rows[0].keys())
    lines = [title, "", f"更新日期：{TARGET_DASH}", "", "| " + " | ".join(fields) + " |", "| " + " | ".join(["---"] * len(fields)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(row.get(field, "").replace("|", "／") for field in fields) + " |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def iso_date(value: str) -> str:
    for pattern in ("%Y/%m/%d", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, pattern).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return value


def summary_row(rows: list[dict], signal_key: str, best: str, worst: str, error: str, adjustment: str, report_file: str) -> dict:
    core_hit, core_total = type_count(rows, "核心承接")
    stable_hit, stable_total = type_count(rows, "稳健观察")
    elastic_hit, elastic_total = type_count(rows, "弹性进攻")
    other_hit, other_total = other_count(rows)
    return {
        "目标日期": TARGET_DASH,
        "预测日期": PREDICTION_DASH,
        **summarize(rows),
        "核心承接命中": core_hit,
        "核心承接总数": core_total,
        "稳健观察命中": stable_hit,
        "稳健观察总数": stable_total,
        "弹性进攻命中": elastic_hit,
        "弹性进攻总数": elastic_total,
        "其他类型命中": other_hit,
        "其他类型总数": other_total,
        "最佳预测": best,
        "最差预测": worst,
        "主要误差": error,
        signal_key: "是",
        "下一步规则调整": adjustment,
        "报告文件": report_file,
    }


def update_ledger(path: Path, reviews: dict[str, tuple[str, str, str, str, str, str]]) -> list[dict]:
    rows = read_csv(path)
    fields = list(rows[0].keys())
    updated = set()
    for row in rows:
        if row.get("目标日期") == TARGET and row.get("代码") in reviews:
            close, change, triggered, invalidated, result, note = reviews[row["代码"]]
            row.update({"收盘价": close, "涨跌幅": change, "是否触发": triggered, "是否失效": invalidated, "复盘结果": result, "复盘备注": f"{note} 数据日期：2026-07-13；来源：腾讯行情日线。"})
            updated.add(row["代码"])
    missing = set(reviews) - updated
    if missing:
        raise RuntimeError(f"目标日期记录缺失: {sorted(missing)}")
    write_csv(path, rows, fields)
    return [row for row in rows if row.get("目标日期") == TARGET]


def rebuild_hk_rule_history(current_error: str, current_adjustment: str) -> list[dict]:
    groups: dict[str, list[dict]] = {}
    for row in read_csv(HK_LEDGER):
        if row.get("复盘结果") in {"命中", "部分命中", "未命中"} and not is_non_rule(row):
            groups.setdefault(row.get("目标日期", ""), []).append(row)
    output = []
    for target in sorted(groups, key=lambda value: iso_date(value)):
        rows = groups[target]
        stats = summarize(rows)
        best = [row["名称"] for row in rows if row.get("复盘结果") == "命中"]
        if not best:
            best = [row["名称"] for row in rows if row.get("复盘结果") == "部分命中"]
        worst = [row["名称"] for row in rows if row.get("复盘结果") == "未命中"]
        needs_adjustment = float(stats["严格命中率"].rstrip("%")) < 60 or float(stats["调整后加权命中率"].rstrip("%")) < 65
        target_iso = iso_date(target)
        historical_adjustment = "历史规则样本按逐票结果重算；命中率低于阈值时延续收紧，优先回踩承接和尾盘确认，具体失效条件见当日逐票台账。"
        output.append(summary_row(
            rows,
            "规则调整信号",
            "; ".join(best) if best else "无",
            "; ".join(worst) if worst else "无",
            current_error if target_iso == TARGET_DASH else "历史规则样本按逐票复盘结果重算，具体误差见当日台账复盘备注。",
            current_adjustment if target_iso == TARGET_DASH else historical_adjustment,
            f"reports/港股预测命中复盘_{target_iso}.md",
        ))
        output[-1]["目标日期"] = target_iso
        output[-1]["预测日期"] = iso_date(rows[0].get("预测日期", ""))
        output[-1]["规则调整信号"] = "是" if needs_adjustment else "否"
    fields = list(output[0].keys()) if output else []
    write_csv(HK_RULE_SUMMARY, output, fields)
    write_summary_md(HK_RULE_MD, "# 港股每日预测复盘规则票汇总", output)
    return output


def write_reports(a_rows: list[dict], hk_rows: list[dict], a_stats: dict, a_rule_stats: dict, hk_stats: dict, hk_rule_stats: dict) -> None:
    a_table = "\n".join(f"| {row['排名']} | {row['名称']} `{row['代码']}` | {row['预测类型']} | {row['收盘价']} / {row['涨跌幅']} | {row['是否触发']} | {row['是否失效']} | {row['复盘结果']} | {row['复盘备注']} |" for row in a_rows)
    hk_table = "\n".join(f"| {row['排名']} | {row['名称']} `{row['代码']}` | {row['预测类型']} | {row['收盘价']} / {row['涨跌幅']} | {row['是否触发']} | {row['是否失效']} | {row['复盘结果']} | {row['复盘备注']} |" for row in hk_rows)
    common_context = """## 新闻政策与美股影响

- 预测前置利好集中在新一代通信网/算力网、存储景气和创新药，但7月13日A股实际风险释放更强：沪指跌2.06%、深成指跌3.48%、创业板指跌3.10%，沪深成交约1.10万亿元；通信、算力和高波动科技票没有形成有效扩散。新闻只确定了观察优先级，未替代承接位和失效位。
- 港股恒指涨0.16%、恒生科技指数跌0.96%，交易所和部分互联网消费好于半导体。港股候选方向仍可保留港交所、低位互联网消费和防守医药，但半导体需继续降级。
- 7月13日美股收盘进一步转弱：道指跌0.26%、标普500跌0.79%、纳指跌1.55%、费城半导体指数约跌4.78%；英伟达、AMD、博通分别约跌3.52%、4.21%、3.98%。美元指数约升0.04%，10年美债收益率升约4个基点至4.609%，WTI原油涨约0.96%。这组变量对下一交易日A/H科技和半导体偏利空，规则票应降数量、降仓位并优先稳健观察。
- 国内晚间政策新增康复辅助器具产业扩能提质方案，脑机接口、康养机器人等可进入观察池，但必须等待板块扩散和个股收盘确认；Meta扩建数据中心对算力长期需求偏利好，短线仍不能抵消海外AI估值降温。

数据与新闻来源：[腾讯行情](https://qt.gtimg.cn/)、[财联社7月13日晚间新闻精选转载](https://finance.eastmoney.com/a/202607133804219250.html)、[美股7月13日收盘概览](https://apnews.com/article/84784dd049267a58ac547d8a1c7fcd02)。
"""
    A_REPORT.write_text(f"""# 预测命中复盘 {TARGET_DASH}

## 策略调整提醒

- 已触发。规则票8只为 `0命中 / 1部分命中 / 7未命中`，严格命中率 `{a_rule_stats['严格命中率']}`、调整后加权命中率 `{a_rule_stats['调整后加权命中率']}`，均显著低于60%/65%阈值；通信/算力同类票紫光股份、中兴通讯、烽火通信连续未兑现，且烽火通信、方正科技、香农芯创、浪潮信息出现深失效或明显冲高回落。
- 建议调整：下一交易日A股正式规则票压缩到1-2只，科技/通信/存储全部降为条件观察，只保留低位、防守、回踩后收盘能确认的稳健票；高波动票不抢反包。
- 适用范围：通信网、算力、AI服务器、PCB、存储、先进封装。失效条件：后续连续两日规则票调整后加权命中率回到65%以上，且同类题材不再出现跌破深失效位或冲高回落样本。

## 一句话结论

A股全量10票为 `0命中 / 3部分命中 / 7未命中`，严格命中率 `{a_stats['严格命中率']}`、调整后命中率 `{a_stats['调整后命中率']}`。政策方向有映射，但市场风险释放压倒题材催化，只有恒瑞医药、科伦药业和博腾股份保留了部分防守或承接价值。

{common_context}
## 逐票复盘

| 排名 | 股票 | 类型 | 收盘/涨跌幅 | 触发 | 失效 | 结果 | 复盘要点 |
| ---: | --- | --- | --- | --- | --- | --- | --- |
{a_table}

## 主要误差与明日规则建议

- 主要误差：把周末通信网/算力网政策催化的优先级，外推成了科技硬件隔日承接；实际上指数风险和高位筹码兑现更强，条件观察票也不具备逆势保护。
- 明日规则：正式票只留1-2只稳健观察；若沪深主指数和对应板块开盘30-60分钟不能止跌，所有科技票不升级；触及深失效位的题材至少冷却一个交易日；防守医药也必须站回触发位，不能因相对抗跌直接判命中。
""", encoding="utf-8")
    HK_REPORT.write_text(f"""# 港股预测命中复盘 {TARGET_DASH}

## 策略调整提醒

- 已触发。港股规则票7只为 `2命中 / 3部分命中 / 2未命中`，严格命中率 `{hk_rule_stats['严格命中率']}`、调整后加权命中率 `{hk_rule_stats['调整后加权命中率']}`，低于60%/65%阈值；中芯国际连续两次承接失败，港股半导体需继续降级。
- 建议调整：下一交易日港股规则票压缩至2-3只，优先港交所、低位互联网消费和防守医药；半导体至少等板块止跌、回踩不破并完成尾盘确认后再恢复。
- 适用范围：港股半导体、互联网平台及高波动科技。失效条件：连续两日规则票调整后加权命中率回到65%以上，且中芯国际/华虹宏力不再出现冲高回落和深失效。

## 一句话结论

港股全量8票为 `2命中 / 3部分命中 / 3未命中`，严格命中率 `{hk_stats['严格命中率']}`、调整后命中率 `{hk_stats['调整后命中率']}`。港交所和京东兑现，阿里、石药、小米仅部分兑现，腾讯与两只半导体未命中。

{common_context}
## 逐票复盘

| 排名 | 股票 | 类型 | 收盘/涨跌幅 | 触发 | 失效 | 结果 | 复盘要点 |
| ---: | --- | --- | --- | --- | --- | --- | --- |
{hk_table}

## 主要误差与明日规则建议

- 主要误差：对港股互联网修复的覆盖面估计偏乐观，腾讯冲高后无法守住承接；半导体虽已降为观察，但仍低估了二次下杀幅度。
- 明日规则：港交所、京东一类能给回踩且收盘确认的票优先；阿里/石药需补收盘确认；腾讯未站回466前只观察；中芯国际、华虹宏力不做抢反弹样本。
""", encoding="utf-8")


def copy_outputs() -> None:
    if not WORKBENCH.exists():
        return
    pairs = [
        (A_LEDGER, WORKBENCH / "03_每日预测台账.csv"),
        (HK_LEDGER, WORKBENCH / "03A_港股预测台账.csv"),
        (A_RULE_SUMMARY, WORKBENCH / "04_规则票复盘统计.csv"),
        (A_RULE_MD, WORKBENCH / "04_规则票复盘统计.md"),
        (A_FULL_SUMMARY, WORKBENCH / "05_全量复盘统计.csv"),
        (A_FULL_MD, WORKBENCH / "05_全量复盘统计.md"),
        (PRED / "hk_daily_review_summary.csv", WORKBENCH / "05A_港股复盘统计.csv"),
        (PRED / "hk_daily_review_summary.md", WORKBENCH / "05A_港股复盘统计.md"),
        (HK_RULE_SUMMARY, WORKBENCH / "04A_港股规则票复盘统计.csv"),
        (HK_RULE_MD, WORKBENCH / "04A_港股规则票复盘统计.md"),
        (A_REPORT, WORKBENCH / f"14_大A预测命中复盘_{TARGET_DASH}.md"),
        (HK_REPORT, WORKBENCH / f"14A_港股预测命中复盘_{TARGET_DASH}.md"),
    ]
    for source, destination in pairs:
        shutil.copyfile(source, destination)


def main() -> None:
    a_rows = update_ledger(A_LEDGER, A_REVIEWS)
    hk_rows = update_ledger(HK_LEDGER, HK_REVIEWS)
    a_rule_rows = [row for row in a_rows if not is_non_rule(row)]
    hk_rule_rows = [row for row in hk_rows if not is_non_rule(row)]

    a_error = "周末通信网/算力网政策优先级被过度外推，指数风险释放压倒题材催化；通信、存储、PCB和AI服务器多票跌破承接或深失效。"
    a_adjustment = "触发原因：规则票严格命中率0.0%、调整后加权命中率6.2%，通信/算力同类票连续未兑现。建议调整：下一交易日正式规则票压缩到1-2只，科技方向降为条件观察，触及深失效位的题材冷却一日。适用范围：通信、算力、存储、PCB、先进封装。失效条件：连续两日规则票调整后加权命中率回到65%以上且无深失效/冲高回落样本。"
    full_summary_rows = upsert_summary(A_FULL_SUMMARY, summary_row(a_rows, "策略提醒", "恒瑞医药; 科伦药业; 博腾股份", "烽火通信; 方正科技; 香农芯创; 浪潮信息", a_error, a_adjustment, f"reports/预测命中复盘_{TARGET_DASH}.md"))
    rule_summary_rows = upsert_summary(A_RULE_SUMMARY, summary_row(a_rule_rows, "规则调整信号", "恒瑞医药", "烽火通信; 方正科技; 香农芯创; 浪潮信息", a_error, a_adjustment, f"reports/预测命中复盘_{TARGET_DASH}.md"))
    write_summary_md(A_FULL_MD, "# 每日预测复盘全量汇总", full_summary_rows)
    write_summary_md(A_RULE_MD, "# 每日预测复盘规则票汇总", rule_summary_rows)

    hk_error = "港股互联网修复覆盖面不及预期，腾讯冲高后未守承接；规则票中芯国际再次失效，半导体二次下杀幅度被低估。"
    hk_adjustment = "触发原因：港股规则票严格命中率28.6%、调整后加权命中率50.0%，低于阈值，且中芯国际连续承接失败。建议调整：规则票压缩到2-3只，优先港交所、低位互联网消费和防守医药，半导体继续降级。适用范围：港股半导体、互联网平台和高波动科技。失效条件：连续两日调整后加权命中率回到65%以上且半导体无深失效。"
    rebuild_hk_rule_history(hk_error, hk_adjustment)

    subprocess.run(["python", str(ROOT / "tools" / "calc_hk_prediction_accuracy.py")], cwd=ROOT, check=True)
    write_reports(a_rows, hk_rows, summarize(a_rows), summarize(a_rule_rows), summarize(hk_rows), summarize(hk_rule_rows))
    copy_outputs()
    print("A股全量", summarize(a_rows))
    print("A股规则", summarize(a_rule_rows))
    print("港股全量", summarize(hk_rows))
    print("港股规则", summarize(hk_rule_rows))


if __name__ == "__main__":
    main()
