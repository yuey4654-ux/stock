import csv
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRED = ROOT / "prediction_tracking"
REPORTS = ROOT / "reports"
WORKBENCH = ROOT / "每日交易工作台"

A_LEDGER = PRED / "daily_predictions.csv"
A_FULL_SUMMARY = PRED / "daily_review_summary.csv"
A_RULE_SUMMARY = PRED / "rule_based_daily_summary.csv"
A_FULL_MD = PRED / "daily_review_summary.md"
A_RULE_MD = PRED / "rule_based_daily_summary.md"
A_REPORT = REPORTS / "预测命中复盘_2026-07-10.md"

TARGET = "2026/7/10"
TARGET_DASH = "2026-07-10"
PREDICTION_DASH = "2026-07-09"

A_REVIEWS = {
    "688981": (
        "163.02",
        "-5.77%",
        "否",
        "否",
        "未命中",
        "收盘163.02，-5.77%；低点162.58跌破164-169承接区，收盘也低于169与173.5确认位，虽未破160降级/155深失效，但半导体权重承接失败。数据：腾讯行情快照，开173.00/高176.34/低162.58/收163.02。"
    ),
    "002371": (
        "801.00",
        "-8.81%",
        "否",
        "否",
        "未命中",
        "收盘801.00，-8.81%；低点800.99已跌破820降级线，收盘远低于880确认位，设备龙头从高位补跌。虽未放量跌破800深失效，但按规则只能记未命中。数据：腾讯行情快照，开886.46/高905.00/低800.99/收801.00。"
    ),
    "000063": (
        "40.53",
        "+0.50%",
        "否",
        "否",
        "部分命中",
        "收盘40.53，+0.50%；低点39.63高于38.8-39.5理想回踩区，尾盘站回40.5，方向没错但没有给到标准低吸买点，按执行口径只能记部分命中。数据：腾讯行情快照，开39.80/高43.00/低39.63/收40.53。"
    ),
    "002463": (
        "129.44",
        "-5.72%",
        "否",
        "否",
        "未命中",
        "收盘129.44，-5.72%；低点129.20跌破132-135承接区，收盘也未站回138确认位，PCB承接明显失败。虽未破128降级线，但不满足触发条件。数据：腾讯行情快照，开137.60/高141.89/低129.20/收129.44。"
    ),
    "000977": (
        "89.52",
        "+4.11%",
        "否",
        "否",
        "部分命中",
        "收盘89.52，+4.11%；高开至92.00且全天最低89.00，没有回踩82.5-84.5承接区，不符合高开不追与分歧承接规则。方向强于预期，但缺少可执行买点，只记部分命中。数据：腾讯行情快照，开92.00/高94.38/低89.00/收89.52。"
    ),
    "600584": (
        "101.11",
        "-2.33%",
        "否",
        "否",
        "部分命中",
        "收盘101.11，-2.33%；高开到108.88后回落，低点与收盘都在99-101.5承接区上沿附近，但尾盘没能站回104升级位。先进封装还有承接但确认不足，记部分命中。数据：腾讯行情快照，开108.88/高113.87/低101.11/收101.11。"
    ),
    "688012": (
        "434.51",
        "-7.86%",
        "否",
        "否",
        "未命中",
        "收盘434.51，-7.86%；低点434.00跌破438降级线，收盘同样未站回475升级位，设备链高位兑现压力显著。虽未跌破423深失效位，但按规则属于未命中。数据：腾讯行情快照，开471.59/高492.05/低434.00/收434.51。"
    ),
    "002185": (
        "25.31",
        "+6.66%",
        "否",
        "否",
        "部分命中",
        "收盘25.31，+6.66%；直接高开至26.10且低点25.10远高于22.7-23.2承接区，没有给到开板分歧买点。方向延续很强，但不满足高开不追规则，只记部分命中。数据：腾讯行情快照，开26.10/高26.10/低25.10/收25.31。"
    ),
    "688008": (
        "268.06",
        "-6.21%",
        "否",
        "否",
        "未命中",
        "收盘268.06，-6.21%；低点267.99跌破270-279承接区下沿，收盘也低于286升级位，AI芯片高波动样本回撤明显。虽未破260降级线，但条件观察未兑现。数据：腾讯行情快照，开291.51/高297.96/低267.99/收268.06。"
    ),
    "300502": (
        "523.05",
        "-4.12%",
        "否",
        "否",
        "未命中",
        "收盘523.05，-4.12%；高开到564.00后一路回落，低点520.58跌破525-538承接区，收盘也低于538，只能记未命中。CPO修复在科技退潮下没有形成有效承接。数据：腾讯行情快照，开564.00/高570.98/低520.58/收523.05。"
    ),
    "688347": (
        "369.87",
        "-7.65%",
        "否",
        "否",
        "未命中",
        "收盘369.87，-7.65%；低点368.00跌破380-392承接区，收盘也未站回405，半导体高弹性非规则样本明显走弱。数据：腾讯行情快照，开393.03/高407.98/低368.00/收369.87。"
    ),
    "300394": (
        "271.12",
        "-0.14%",
        "否",
        "否",
        "部分命中",
        "收盘271.12，-0.14%；高开281.00后回落，低点270.91仍高于258-266理想承接区，没给到标准回踩买点，也未站回273。弹性样本守住大体结构但执行条件不足，记部分命中。数据：腾讯行情快照，开281.00/高291.80/低270.91/收271.12。"
    ),
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
    t = row.get("预测类型", "")
    if t.startswith("核心承接"):
        return 1.5
    if t.startswith("弹性进攻") or t.startswith("弹性观察"):
        return 0.8
    return 1.0


def summarize(rows: list[dict]) -> dict:
    total = len(rows)
    hit = sum(r.get("复盘结果") == "命中" for r in rows)
    partial = sum(r.get("复盘结果") == "部分命中" for r in rows)
    miss = sum(r.get("复盘结果") == "未命中" for r in rows)
    w_total = sum(weight(r) for r in rows)
    w_hit = sum(weight(r) for r in rows if r.get("复盘结果") == "命中")
    w_adj = sum(
        weight(r) * (1 if r.get("复盘结果") == "命中" else 0.5 if r.get("复盘结果") == "部分命中" else 0)
        for r in rows
    )
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


def is_non_rule(row: dict) -> bool:
    return row.get("预测类型", "").startswith("非规则")


def type_count(rows: list[dict], prefix: str) -> tuple[str, str]:
    selected = [r for r in rows if r.get("预测类型", "").startswith(prefix)]
    return str(sum(r.get("复盘结果") == "命中" for r in selected)), str(len(selected))


def other_count(rows: list[dict]) -> tuple[str, str]:
    selected = [
        r
        for r in rows
        if not (
            r.get("预测类型", "").startswith("核心承接")
            or r.get("预测类型", "").startswith("稳健观察")
            or r.get("预测类型", "").startswith("弹性进攻")
        )
    ]
    return str(sum(r.get("复盘结果") == "命中" for r in selected)), str(len(selected))


def upsert_summary(path: Path, row: dict, key: str = "目标日期") -> list[dict]:
    rows = read_csv(path)
    fields = list(rows[0].keys()) if rows else list(row.keys())
    rows = [r for r in rows if r.get(key) != row[key]]
    rows.append(row)
    rows.sort(key=lambda r: r[key])
    write_csv(path, rows, fields)
    return rows


def write_summary_md(path: Path, title: str, update_date: str, rows: list[dict]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = list(rows[0].keys())
    lines = [
        title,
        "",
        f"更新日期：{update_date}",
        "",
        "| " + " | ".join(fields) + " |",
        "| " + " | ".join(["---"] * len(fields)) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(row.get(f, "") for f in fields) + " |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def summary_row(rows: list[dict], signal_key: str, best: str, worst: str, error: str, adjustment: str, report: str) -> dict:
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
        signal_key: "否" if "不触发" in adjustment else "是",
        "下一步规则调整": adjustment,
        "报告文件": "reports/预测命中复盘_2026-07-10.md",
    }


def update_a_share() -> tuple[dict, dict]:
    rows = read_csv(A_LEDGER)
    fields = list(rows[0].keys())
    for row in rows:
        if row.get("目标日期") == TARGET and row.get("代码") in A_REVIEWS and row.get("复盘结果") == "待复盘":
            close, pct, triggered, invalid, result, note = A_REVIEWS[row["代码"]]
            row.update(
                {
                    "收盘价": close,
                    "涨跌幅": pct,
                    "是否触发": triggered,
                    "是否失效": invalid,
                    "复盘结果": result,
                    "复盘备注": note,
                }
            )
    write_csv(A_LEDGER, rows, fields)

    day_rows = [r for r in rows if r.get("目标日期") == TARGET]
    full_rows = day_rows
    rule_rows = [r for r in day_rows if not is_non_rule(r)]

    full_stats = summarize(full_rows)
    rule_stats = summarize(rule_rows)

    error = (
        "主要误差不是题材方向，而是节奏：7月9日科技高潮后，7月10日半导体/先进封装/PCB/CPO大量高开或冲高回落，"
        "正式稳健票几乎都没给到干净承接；条件观察票也多数只有方向热度，没有收盘确认。"
    )
    adjustment = (
        "触发原因：规则票10只中0命中、4部分命中、6未命中，严格命中率0.0%，调整后加权命中率20.0%，均低于60%/65%阈值。"
        "建议调整：下一交易日规则票压缩到1-2只，只保留稳健观察，半导体设备/材料、先进封装、AI服务器、PCB、CPO先等板块分歧后再看收盘确认；"
        "高开超过3%且不回踩的一律不作为可执行命中。适用范围：半导体、先进封装、AI服务器、PCB、CPO相关规则票。"
        "失效条件：后续连续两日规则票调整后加权命中率回到65%以上，且不再出现权重股跌破承接区后收盘无法修复的样本。"
    )

    full_summary_rows = upsert_summary(
        A_FULL_SUMMARY,
        summary_row(
            full_rows,
            "策略提醒",
            "中兴通讯; 浪潮信息; 长电科技; 华天科技; 天孚通信",
            "中芯国际; 北方华创; 沪电股份; 中微公司; 澜起科技; 新易盛; 华虹宏力",
            error,
            adjustment,
            "reports/预测命中复盘_2026-07-10.md",
        ),
    )
    rule_summary_rows = upsert_summary(
        A_RULE_SUMMARY,
        summary_row(
            rule_rows,
            "规则调整信号",
            "中兴通讯; 浪潮信息; 长电科技; 华天科技",
            "中芯国际; 北方华创; 沪电股份; 中微公司; 澜起科技; 新易盛",
            error,
            adjustment,
            "reports/预测命中复盘_2026-07-10.md",
        ),
    )

    write_summary_md(A_FULL_MD, "# 每日预测复盘全量汇总", TARGET_DASH, full_summary_rows)
    write_summary_md(A_RULE_MD, "# 每日预测复盘规则票汇总", TARGET_DASH, rule_summary_rows)

    A_REPORT.write_text(
        f"""# 预测命中复盘_2026-07-10

## 一句话结论

今天是典型的“高潮次日去兑现”：全量12票0命中、5部分命中、7未命中，严格命中率0.0%，调整后命中率20.8%；规则票10票0命中、4部分命中、6未命中，严格命中率0.0%，调整后命中率20.0%。

## 策略调整提醒

- 已触发。规则票严格命中率0.0%、调整后加权命中率20.0%，同时半导体、先进封装、PCB/CPO多只样本出现高开后不给买点或冲高回落，说明7月9日的科技高潮不能直接外推到7月10日。
- 建议下一交易日把正式规则票压缩到1-2只，只保留稳健观察；半导体设备/材料、先进封装、AI服务器、PCB、CPO优先等分歧后收盘确认。
- 失效条件：后续连续两日规则票调整后加权命中率回到65%以上，且权重票不再出现跌破承接区后收盘无法修复的样本。

## 新闻政策与美股影响

- 财联社早间新闻精选显示，7月10日盘前的正面产业催化仍集中在科技：华为联合产业伙伴发起近封装光学项目、证监会同意燧原科技科创板IPO注册、兆易创新上半年净利润预增约1099%，并提到美光将把美国本土投资总额提升到2500亿美元以上。这些信息抬升了半导体、先进封装和算力硬件的热点优先级，但没有替代分歧承接和收盘确认。来源：[财联社7月10日早间新闻精选](https://www.cls.cn/detail/2422290)
- 财联社收评与焦点复盘显示，7月10日A股实际走成“高开后兑现”：沪指跌1%，深成指跌2.29%，创业板指跌4.37%，科创50跌5.53%；两市成交额3.39万亿元，较前一交易日放量4748亿元，92股涨停但91股炸板，封板率只有50%。半导体、锂电、元器件、玻璃基板领跌，创新药、医疗信息化、风电设备逆势活跃。来源：[财联社焦点复盘](https://www.cls.cn/detail/2423004)、[财联社盘中快讯](https://www.cls.cn/detail/2422715)
- 海外方面，7月9日美股三大指数收涨，纳指涨1.3%；7月10日美股继续偏强，标普500涨0.42%，纳指涨0.29%，费城半导体指数涨0.06%，NVDA涨4.03%，META涨5.97%，AAPL跌0.28%，VIX回落至15.03，美元指数100.76，10年美债收益率4.56%，WTI原油71.41美元。美股风险偏好并没有明显转弱，但A股科技线在前一日爆量大涨后选择先兑现，说明外盘利好只能决定热点优先级，不能替代A股自身的买点和承接确认。来源：[MarketWatch 7月9日收盘综述](https://www.marketwatch.com/livecoverage/stock-market-today-dow-s-p-500-nasdaq-heightened-tensions-us-iran)、[Reuters/Investing 7月10日美股综述](https://www.investing.com/news/stock-market-news/sp-500-nasdaq-futures-slip-as-investors-eye-sk-hynix-listing-middle-east-risks-4785654)
- 对下一交易日规则票的影响：利好映射仍偏向半导体、先进封装、AI服务器，但由于A股当天已经验证“高开和题材热度不能替代买点”，下一交易日必须降仓降数量，优先稳健观察，条件观察票只在回踩承接后再看尾盘确认。

## 总体命中率

| 口径 | 总数 | 命中 | 部分命中 | 未命中 | 严格命中率 | 调整后命中率 | 严格加权命中率 | 调整后加权命中率 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 全量 | {full_stats['总数']} | {full_stats['命中']} | {full_stats['部分命中']} | {full_stats['未命中']} | {full_stats['严格命中率']} | {full_stats['调整后命中率']} | {full_stats['严格加权命中率']} | {full_stats['调整后加权命中率']} |
| 规则票 | {rule_stats['总数']} | {rule_stats['命中']} | {rule_stats['部分命中']} | {rule_stats['未命中']} | {rule_stats['严格命中率']} | {rule_stats['调整后命中率']} | {rule_stats['严格加权命中率']} | {rule_stats['调整后加权命中率']} |

## 逐票复盘

| 排名 | 股票 | 类型 | 收盘/涨跌幅 | 触发 | 失效 | 结果 | 备注 |
| ---: | --- | --- | --- | --- | --- | --- | --- |
""" + "\n".join(
            f"| {r['排名']} | {r['名称']}({r['代码']}) | {r['预测类型']} | {r['收盘价']} / {r['涨跌幅']} | {r['是否触发']} | {r['是否失效']} | {r['复盘结果']} | {r['复盘备注']} |"
            for r in day_rows
        ) + """

## 主要误差

- 最大误差在于把“7月9日科技高潮”延续成“7月10日继续稳健承接”。中芯国际、北方华创、沪电股份、中微公司这类权重/龙头并没有给到理想回踩后的收盘确认，反而在放量下走出权重补跌。
- 条件观察票里，浪潮信息、华天科技属于方向强但没有买点；长电科技属于守住承接但没收回确认位；澜起科技、新易盛则是高波动分支直接失去承接。
- 非规则票同样没有提供放宽依据。华虹宏力高弹性样本直接回落，天孚通信虽没破结构，但也没有给出标准执行位。

## 明日规则调整建议

1. 规则票数量降到1-2只，先看稳健观察，不再因为前一日科技大涨就扩样到10只规则票。
2. 半导体、先进封装、AI服务器、PCB、CPO统一执行更硬的“高开不追+回踩承接+尾盘确认”；高开超过3%且不回踩的票，最多记部分命中，不能当成可执行样本。
3. 若盘前外部变量继续偏正面，但A股主线权重早盘30-60分钟内跌破承接区，条件观察票全部降级，不做盘中放宽。
4. 可把逆势分支留作备选观察，如创新药、医疗信息化等，但只有板块扩散和个股承接同时确认后才考虑回到正式规则票。
""",
        encoding="utf-8",
    )

    return full_stats, rule_stats


def copy_outputs() -> None:
    if not WORKBENCH.exists():
        return
    pairs = [
        (A_LEDGER, WORKBENCH / "03_每日预测台账.csv"),
        (A_FULL_SUMMARY, WORKBENCH / "05_全量复盘统计.csv"),
        (A_FULL_MD, WORKBENCH / "05_全量复盘统计.md"),
        (A_RULE_SUMMARY, WORKBENCH / "04_规则票复盘统计.csv"),
        (A_RULE_MD, WORKBENCH / "04_规则票复盘统计.md"),
        (A_REPORT, WORKBENCH / "14_大A预测命中复盘_2026-07-10.md"),
    ]
    for src, dst in pairs:
        shutil.copyfile(src, dst)


def main() -> None:
    full_stats, rule_stats = update_a_share()
    copy_outputs()
    print("A股全量", full_stats)
    print("A股规则票", rule_stats)
    print(A_REPORT)


if __name__ == "__main__":
    main()
