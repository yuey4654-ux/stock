import csv
import shutil
import subprocess
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
A_REPORT = REPORTS / "预测命中复盘_2026-07-09.md"

HK_LEDGER = PRED / "hk_daily_predictions.csv"
HK_REPORT = REPORTS / "港股预测命中复盘_2026-07-09.md"

TARGET = "2026/7/9"
TARGET_DASH = "2026-07-09"
PREDICTION_DASH = "2026-07-08"


A_REVIEWS = {
    "688981": ("165.58", "+8.86%", "是", "否", "命中", "收盘165.58、+8.86%；低点152.10守住149.5-150.2承接区上方，收盘明显站上153.6触发位。命中，但下午已远离买点，不适合追高。"),
    "603019": ("101.88", "+3.80%", "是", "否", "部分命中", "收盘101.88、+3.80%；盘中最低96.18略破96.7承接下沿，但未触发90.8失效，收盘站上99.1触发位。方向兑现但执行点不够干净，记部分命中。"),
    "002371": ("838.88", "+4.56%", "是", "否", "命中", "收盘838.88、+4.56%；低点815.00守住790-814承接区上方，收盘站上814触发位，设备链兑现。"),
    "600276": ("54.61", "+1.11%", "否", "否", "未命中", "收盘54.61、+1.11%；低点52.85跌破53.1承接下沿，收盘未站回54.8触发位。虽未深失效，但不满足预测触发条件，记未命中。"),
    "002185": ("23.73", "+10.01%", "是", "否", "命中", "收盘23.73、+10.01%；低点21.41守住21.25-21.45区域，收盘站上21.8升级位并封强，先进封装条件观察兑现。"),
    "688019": ("324.98", "+2.81%", "是", "否", "命中", "收盘324.98、+2.81%；低点309.00落在305-311承接区，收盘站上319升级位，半导体材料条件观察兑现。"),
    "688012": ("449.68", "+6.31%", "是", "否", "命中", "收盘449.68、+6.31%；低点430.00高于417-423承接区，收盘站上427升级位，半导体设备条件观察兑现。"),
    "688795": ("743.00", "+11.56%", "是", "否", "命中", "收盘743.00、+11.56%；低点666.66落在656-672承接区，收盘站上673升级位，AI芯片条件观察兑现。"),
    "688802": ("938.00", "+11.66%", "是", "否", "命中", "收盘938.00、+11.66%；低点855.00高于811-828承接区，收盘站上848升级位，AI芯片条件观察兑现。"),
    "002409": ("207.20", "+9.05%", "是", "否", "命中", "收盘207.20、+9.05%；低点194.97基本守住190-195区域，收盘站上195升级位，半导体材料条件观察兑现。"),
    "300604": ("345.89", "+9.04%", "是", "否", "部分命中", "收盘345.89、+9.04%；盘中最低310.49略破312-317承接区下沿，但收盘重新站上320。非规则弹性方向兑现，执行条件不完整，记部分命中。"),
    "300502": ("539.95", "+5.70%", "是", "否", "命中", "收盘539.95、+5.70%；低点509.96落在505-513承接区，收盘站上516触发位，CPO修复样本兑现。"),
}

HK_REVIEWS = {
    "09988.HK": ("108.00", "+0.47%", "否", "否", "部分命中", "收盘108.00；低点107.50高于102.5-105承接区，但收盘未站回108.5触发位。守承接但未完成确认，记部分命中。"),
    "00700.HK": ("469.60", "-1.92%", "否", "否", "部分命中", "收盘469.60；低点467.20接近468-474承接区下沿，未跌破462降级线，但收盘未站回482触发位，记部分命中。"),
    "00981.HK": ("83.55", "+10.22%", "是", "否", "命中", "收盘83.55；低点76.65守住73.5-75承接区上方，收盘站上77触发位，港股半导体兑现。"),
    "01810.HK": ("25.00", "-1.19%", "否", "否", "部分命中", "收盘25.00；低点24.48守住24.3-24.8承接区，但收盘未站回25.6升级位，记部分命中。"),
    "01024.HK": ("42.10", "-4.27%", "否", "否", "部分命中", "收盘42.10；低点42.02守住42-43承接区下沿，未跌破40失效位，但未站回44.6升级位，记部分命中。"),
    "03690.HK": ("78.50", "-2.97%", "否", "否", "部分命中", "收盘78.50；低点78.20在78-79.5承接区内，未站回81.5升级位，记部分命中。"),
    "01347.HK": ("201.80", "+8.44%", "是", "否", "命中", "收盘201.80；低点183.40落在178-184承接区，收盘站上190触发位，半导体弹性兑现。"),
    "09880.HK": ("87.70", "-0.68%", "否", "否", "部分命中", "收盘87.70；低点86.15守住85.5-88承接区，未站回91触发位，机器人弹性不足，记部分命中。"),
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


def is_formal_rule(row: dict) -> bool:
    t = row.get("预测类型", "")
    return (not t.startswith("非规则")) and ("条件观察" not in t)


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


def write_md(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = list(rows[0].keys())
    lines = ["| " + " | ".join(fields) + " |", "| " + " | ".join(["---"] * len(fields)) + " |"]
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
        "报告文件": report,
    }


def update_a_share() -> tuple[dict, dict, dict]:
    rows = read_csv(A_LEDGER)
    fields = list(rows[0].keys())
    for row in rows:
        if row.get("目标日期") == TARGET and row.get("代码") in A_REVIEWS:
            close, pct, triggered, invalid, result, note = A_REVIEWS[row["代码"]]
            row.update({
                "收盘价": close,
                "涨跌幅": pct,
                "是否触发": triggered,
                "是否失效": invalid,
                "复盘结果": result,
                "复盘备注": note,
            })
    write_csv(A_LEDGER, rows, fields)

    day_rows = [r for r in rows if r.get("目标日期") == TARGET]
    full_stats = summarize(day_rows)
    old_rule_rows = [r for r in day_rows if not is_non_rule(r)]
    formal_rows = [r for r in day_rows if is_formal_rule(r)]
    old_rule_stats = summarize(old_rule_rows)
    formal_stats = summarize(formal_rows)

    error = "正式稳健票里恒瑞未站回触发位，中科曙光盘中略破承接下沿；其余科技条件观察大多兑现，说明上午强主线有效，但追高风险很高。"
    adjustment = "不触发新增收紧；保留全量样本统计。明日继续要求高开不追、回踩承接、尾盘确认；涨幅过大但远离买点的票只能算命中样本，不能作为追高依据。"
    full_rows = upsert_summary(
        A_FULL_SUMMARY,
        summary_row(day_rows, "策略提醒", "中芯国际; 北方华创; 华天科技; 中微公司; 摩尔线程-U; 沐曦股份-U; 雅克科技; 新易盛", "恒瑞医药", error, adjustment, "reports/预测命中复盘_2026-07-09.md"),
    )
    rule_rows = upsert_summary(
        A_RULE_SUMMARY,
        summary_row(old_rule_rows, "规则调整信号", "中芯国际; 北方华创; 条件观察科技线", "恒瑞医药", error, adjustment, "reports/预测命中复盘_2026-07-09.md"),
    )
    write_md(A_FULL_MD, full_rows)
    write_md(A_RULE_MD, rule_rows)

    A_REPORT.write_text(
        f"""# 预测命中复盘 2026-07-09

## 大A统计

| 口径 | 总数 | 命中 | 部分命中 | 未命中 | 严格命中率 | 调整后命中率 | 调整后加权命中率 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 全量预测票 | {full_stats['总数']} | {full_stats['命中']} | {full_stats['部分命中']} | {full_stats['未命中']} | {full_stats['严格命中率']} | {full_stats['调整后命中率']} | {full_stats['调整后加权命中率']} |
| 非非规则旧口径 | {old_rule_stats['总数']} | {old_rule_stats['命中']} | {old_rule_stats['部分命中']} | {old_rule_stats['未命中']} | {old_rule_stats['严格命中率']} | {old_rule_stats['调整后命中率']} | {old_rule_stats['调整后加权命中率']} |
| 正式规则票 | {formal_stats['总数']} | {formal_stats['命中']} | {formal_stats['部分命中']} | {formal_stats['未命中']} | {formal_stats['严格命中率']} | {formal_stats['调整后命中率']} | {formal_stats['调整后加权命中率']} |

## 逐票复盘

| 排名 | 股票 | 类型 | 收盘/涨跌幅 | 结果 | 复盘要点 |
| ---: | --- | --- | --- | --- | --- |
""" + "\n".join(
            f"| {r['排名']} | {r['名称']} `{r['代码']}` | {r['预测类型']} | {r['收盘价']} / {r['涨跌幅']} | {r['复盘结果']} | {r['复盘备注']} |"
            for r in day_rows
        ) + f"""

## 结论

- 今天大A全量预测票表现很好：科技条件观察大面积兑现，说明昨天扩样方向有效。
- 正式规则票只有 4 只，严格命中率 {formal_stats['严格命中率']}，主要被恒瑞医药拖累；中科曙光方向对但盘中承接不够干净。
- 明天不能因为命中率高就放宽追高：很多票是高开后一路加速，适合复盘记命中，不代表下午还能追。
""",
        encoding="utf-8",
    )
    return full_stats, old_rule_stats, formal_stats


def update_hk() -> tuple[dict, dict, dict]:
    rows = read_csv(HK_LEDGER)
    rows = [r for r in rows if r.get("预测日期") != "预测日期"]
    fields = list(rows[0].keys())
    for row in rows:
        if row.get("目标日期") == TARGET and row.get("代码") in HK_REVIEWS:
            close, pct, triggered, invalid, result, note = HK_REVIEWS[row["代码"]]
            row.update({
                "收盘价": close,
                "涨跌幅": pct,
                "是否触发": triggered,
                "是否失效": invalid,
                "复盘结果": result,
                "复盘备注": note,
            })
    write_csv(HK_LEDGER, rows, fields)

    day_rows = [r for r in rows if r.get("目标日期") == TARGET]
    full_stats = summarize(day_rows)
    formal_rows = [r for r in day_rows if is_formal_rule(r)]
    formal_stats = summarize(formal_rows)
    nonrule_rows = [r for r in day_rows if is_non_rule(r)]
    nonrule_stats = summarize(nonrule_rows)

    subprocess.run(["python", str(ROOT / "tools" / "calc_hk_prediction_accuracy.py")], cwd=ROOT, check=True)

    HK_REPORT.write_text(
        f"""# 港股预测命中复盘 2026-07-09

## 港股统计

| 口径 | 总数 | 命中 | 部分命中 | 未命中 | 严格命中率 | 调整后命中率 | 调整后加权命中率 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 港股全量预测票 | {full_stats['总数']} | {full_stats['命中']} | {full_stats['部分命中']} | {full_stats['未命中']} | {full_stats['严格命中率']} | {full_stats['调整后命中率']} | {full_stats['调整后加权命中率']} |
| 正式/条件非非规则票 | {formal_stats['总数']} | {formal_stats['命中']} | {formal_stats['部分命中']} | {formal_stats['未命中']} | {formal_stats['严格命中率']} | {formal_stats['调整后命中率']} | {formal_stats['调整后加权命中率']} |
| 非规则观察票 | {nonrule_stats['总数']} | {nonrule_stats['命中']} | {nonrule_stats['部分命中']} | {nonrule_stats['未命中']} | {nonrule_stats['严格命中率']} | {nonrule_stats['调整后命中率']} | {nonrule_stats['调整后加权命中率']} |

## 逐票复盘

| 排名 | 股票 | 类型 | 收盘/涨跌幅 | 结果 | 复盘要点 |
| ---: | --- | --- | --- | --- | --- |
""" + "\n".join(
            f"| {r['排名']} | {r['名称']} `{r['代码']}` | {r['预测类型']} | {r['收盘价']} / {r['涨跌幅']} | {r['复盘结果']} | {r['复盘备注']} |"
            for r in day_rows
        ) + f"""

## 结论

- 港股方向没有完全错，但多数互联网票只守住承接，没有完成触发位确认，所以严格命中率低于大A。
- 中芯国际和华虹半导体兑现最好，说明半导体弹性强于互联网平台。
- 港股后续仍要用更硬的收盘确认：高开后不能站回触发位，只能算部分命中，不能算完整命中。
""",
        encoding="utf-8",
    )
    return full_stats, formal_stats, nonrule_stats


def copy_outputs() -> None:
    if not WORKBENCH.exists():
        return
    pairs = [
        (A_LEDGER, WORKBENCH / "03_每日预测台账.csv"),
        (A_FULL_SUMMARY, WORKBENCH / "05_全量复盘统计.csv"),
        (A_FULL_MD, WORKBENCH / "05_全量复盘统计.md"),
        (A_RULE_SUMMARY, WORKBENCH / "04_规则票复盘统计.csv"),
        (A_RULE_MD, WORKBENCH / "04_规则票复盘统计.md"),
        (HK_LEDGER, WORKBENCH / "03A_港股预测台账.csv"),
        (PRED / "hk_daily_review_summary.csv", WORKBENCH / "05A_港股复盘统计.csv"),
        (PRED / "hk_daily_review_summary.md", WORKBENCH / "05A_港股复盘统计.md"),
        (A_REPORT, WORKBENCH / "14_大A预测命中复盘_2026-07-09.md"),
        (HK_REPORT, WORKBENCH / "14A_港股预测命中复盘_2026-07-09.md"),
    ]
    for src, dst in pairs:
        shutil.copyfile(src, dst)


def main() -> None:
    a_full, a_rule, a_formal = update_a_share()
    hk_full, hk_formal, hk_nonrule = update_hk()
    copy_outputs()
    print("A股全量", a_full)
    print("A股正式规则", a_formal)
    print("港股全量", hk_full)
    print("港股非规则", hk_nonrule)
    print(A_REPORT)
    print(HK_REPORT)


if __name__ == "__main__":
    main()
