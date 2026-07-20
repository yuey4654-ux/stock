import csv
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "prediction_tracking"
R = ROOT / "reports"
TARGET, ISO, PREDISO = "2026/7/20", "2026-07-20", "2026-07-19"
A_LEDGER = P / "daily_predictions.csv"
H_LEDGER = P / "hk_daily_predictions.csv"

A_REV = {
    "600900": ("28.98", "+3.54%", "是", "否", "命中", "开27.75/高28.98/低27.75/收28.98。低点进入27.70-27.90承接区，收盘明显站上28.05，正式规则票完整兑现。"),
    "601939": ("10.44", "+2.76%", "否", "否", "部分命中", "开9.98/高10.44/低9.94/收10.44。低点较9.95承接下沿低0.01，随后收盘站上10.18；方向与确认正确，但严格路径轻微破位，只记部分命中。"),
    "601088": ("46.14", "+4.98%", "否", "否", "部分命中", "开43.90/高46.14/低43.73/收46.14。煤炭方向与收盘强度兑现，但全天未进入43.25-43.60计划买点，没有标准低吸机会，只记部分命中。"),
    "600938": ("31.87", "+10.01%", "否", "否", "部分命中", "开29.60/高31.87/低29.51/收31.87。油气扩散并涨停，但低点未回踩28.90-29.15；“高开不超过3%”不能单独构成买点，只记部分命中。"),
    "601991": ("6.38", "+10.00%", "是", "是", "未命中", "开5.68/高6.38/低5.45/收6.38。开盘进入5.60-5.72计划区，但盘中触及5.45深失效位后才涨停；按失效优先规则记未命中。"),
}

H_REV = {
    "00941.HK": ("80.800", "+1.06%", "否", "否", "部分命中", "开80.00/高81.40/低80.00/收80.80。收盘站上80.10且相对稳健，但低点未进入79.40-79.75计划买点，正式票仅记部分命中。"),
    "01088.HK": ("43.600", "+2.83%", "否", "否", "部分命中", "开42.98/高43.66/低42.32/收43.60。方向正确并站上42.55，但低点高于41.90-42.20承接区，没有标准低吸机会。"),
    "00883.HK": ("23.900", "+5.19%", "是", "否", "命中", "开23.20/高24.28/低23.20/收23.90。高开约2.11%未超过3%，尾盘站上23.00，油价映射条件兑现。"),
    "00005.HK": ("157.800", "+0.57%", "是", "否", "命中", "开157.00/高157.80/低155.50/收157.80。低点进入155.0-156.2承接区，收盘站上157.4，金融防守条件完整兑现。"),
    "00700.HK": ("477.800", "+3.51%", "是", "否", "命中", "开465.60/高481.80/低465.60/收477.80。全日守住458并尾盘站上468，恒生科技同步反弹2.79%，科技冷却观察条件兑现；仍非正式买入票。"),
}


def read(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write(path, rows, fields):
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(rows)


def weight(row):
    kind = row["预测类型"]
    if kind.startswith("核心承接"):
        return 1.5
    if kind.startswith(("弹性进攻", "弹性观察")):
        return 0.8
    return 1.0


def stats(rows):
    n = len(rows)
    hit = sum(r["复盘结果"] == "命中" for r in rows)
    partial = sum(r["复盘结果"] == "部分命中" for r in rows)
    miss = sum(r["复盘结果"] == "未命中" for r in rows)
    total_weight = sum(weight(r) for r in rows)
    strict_weight = sum(weight(r) for r in rows if r["复盘结果"] == "命中")
    adjusted_weight = sum(
        weight(r) * (1 if r["复盘结果"] == "命中" else 0.5 if r["复盘结果"] == "部分命中" else 0)
        for r in rows
    )
    return {
        "总数": str(n),
        "命中": str(hit),
        "部分命中": str(partial),
        "未命中": str(miss),
        "严格命中率": f"{hit / n * 100:.1f}%" if n else "0.0%",
        "调整后命中率": f"{(hit + 0.5 * partial) / n * 100:.1f}%" if n else "0.0%",
        "严格加权命中率": f"{strict_weight / total_weight * 100:.1f}%" if total_weight else "0.0%",
        "调整后加权命中率": f"{adjusted_weight / total_weight * 100:.1f}%" if total_weight else "0.0%",
    }


def update_ledger(path, reviews, source):
    rows = read(path)
    fields = list(rows[0])
    seen = set()
    for row in rows:
        if row["目标日期"] == TARGET and row["代码"] in reviews:
            close, change, triggered, invalid, result, note = reviews[row["代码"]]
            row.update({
                "收盘价": close,
                "涨跌幅": change,
                "是否触发": triggered,
                "是否失效": invalid,
                "复盘结果": result,
                "复盘备注": note + f" 数据日期：{ISO}；来源：{source}。",
            })
            seen.add(row["代码"])
    if seen != set(reviews):
        raise RuntimeError(f"台账缺少代码：{set(reviews) - seen}")
    write(path, rows, fields)
    return [r for r in rows if r["目标日期"] == TARGET]


def count_type(rows, prefix):
    selected = [r for r in rows if r["预测类型"].startswith(prefix)]
    return str(sum(r["复盘结果"] == "命中" for r in selected)), str(len(selected))


def summary(rows, signal_field, signal, error, adjustment, report_file):
    core = count_type(rows, "核心承接")
    stable = count_type(rows, "稳健观察")
    elastic = count_type(rows, "弹性进攻")
    other = [r for r in rows if not r["预测类型"].startswith(("核心承接", "稳健观察", "弹性进攻"))]
    return {
        "目标日期": ISO,
        "预测日期": PREDISO,
        **stats(rows),
        "核心承接命中": core[0],
        "核心承接总数": core[1],
        "稳健观察命中": stable[0],
        "稳健观察总数": stable[1],
        "弹性进攻命中": elastic[0],
        "弹性进攻总数": elastic[1],
        "其他类型命中": str(sum(r["复盘结果"] == "命中" for r in other)),
        "其他类型总数": str(len(other)),
        "最佳预测": "; ".join(r["名称"] for r in rows if r["复盘结果"] == "命中") or "无",
        "最差预测": "; ".join(r["名称"] for r in rows if r["复盘结果"] == "未命中") or "无",
        "主要误差": error,
        signal_field: signal,
        "下一步规则调整": adjustment,
        "报告文件": report_file,
    }


def upsert(path, row):
    old = read(path)
    fields = list(old[0])
    old = [r for r in old if r.get("目标日期") != ISO]
    old.append({key: row.get(key, "") for key in fields})
    old.sort(key=lambda r: r.get("目标日期", ""))
    write(path, old, fields)
    return old


def markdown_summary(path, title, rows):
    fields = list(rows[0])
    lines = [title, "", f"更新日期：{ISO}", "", "| " + " | ".join(fields) + " |", "| " + " | ".join(["---"] * len(fields)) + " |"]
    lines.extend("| " + " | ".join(r.get(key, "").replace("|", "／") for key in fields) + " |" for r in rows)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_report(path, market, rows, full, rule, alert, conclusion, errors, next_step):
    table = "\n".join(
        f"| {r['排名']} | {r['名称']} `{r['代码']}` | {r['预测类型']} | {r['收盘价']} / {r['涨跌幅']} | {r['是否触发']} | {r['是否失效']} | {r['复盘结果']} | {r['复盘备注']} |"
        for r in rows
    )
    path.write_text(f"""# {market}预测命中复盘 {ISO}

## 策略调整提醒

{alert}

## 一句话结论

{conclusion}

全量 {full['总数']} 票：`{full['命中']}命中 / {full['部分命中']}部分命中 / {full['未命中']}未命中`，严格命中率 `{full['严格命中率']}`、调整后命中率 `{full['调整后命中率']}`；正式规则票严格命中率 `{rule['严格命中率']}`、调整后加权命中率 `{rule['调整后加权命中率']}`。

## 市场与热点验证

- A股沪指收涨0.85%，深成指跌0.71%，创业板指涨0.42%；油气、电力和煤炭集体走强，中国海油、大唐发电涨停。指数虽修复，但成长方向仍明显分化。
- 港股恒指收涨2.36%，恒生科技涨2.79%；腾讯等互联网权重修复，能源和高股息方向延续相对强势。
- V3判断基本兑现：防守与能源方向优先级正确；但部分标的直接拉升，没有回到计划买点，不能把方向上涨等同于可执行命中。

## 逐票复盘

| 排名 | 股票 | 类型 | 收盘/涨跌幅 | 触发 | 失效 | 结果 | 复盘要点 |
| ---: | --- | --- | --- | --- | --- | --- | --- |
{table}

## 主要误差

{errors}

## 下一步

{next_step}

数据日期：2026-07-20。个股与指数行情采用腾讯收盘快照；市场交叉核验参考财联社、每日经济新闻及公开市场收评。仅作策略复盘，不构成确定性投资建议。
""", encoding="utf-8")


A = update_ledger(A_LEDGER, A_REV, "腾讯A股行情")
H = update_ledger(H_LEDGER, H_REV, "腾讯港股行情")
A_RULE = [r for r in A if not r["预测类型"].startswith("非规则")]
H_RULE = [r for r in H if not r["预测类型"].startswith("非规则")]

a_error = "中国神华、中国海油方向正确但没有进入计划买点，只记部分命中；大唐发电先触及深失效位再涨停，仍记未命中。建设银行轻微跌破承接下沿，也只记部分命中。"
a_adjust = "A股正式规则票长江电力完整命中，结束单日0%状态，但尚不足以扩张票数。下一次仍以1-2只正式票为限，并继续执行公司行动校正与失效优先。"
h_error = "中国移动和中国神华方向正确，但都没有回到计划低吸区；正式票中国移动只能部分命中，说明防守方向选择正确但买点设置偏深。"
h_adjust = "港股正式规则票严格命中率0%、调整后50%，继续保持1只正式票；不得因恒科单日反弹立即恢复科技进攻票。"

a_full_rows = upsert(P / "daily_review_summary.csv", summary(A, "策略提醒", "否", a_error, a_adjust, f"reports/预测命中复盘_{ISO}.md"))
a_rule_rows = upsert(P / "rule_based_daily_summary.csv", summary(A_RULE, "规则调整信号", "否", a_error, a_adjust, f"reports/预测命中复盘_{ISO}.md"))
markdown_summary(P / "daily_review_summary.md", "# 每日预测复盘全量汇总", a_full_rows)
markdown_summary(P / "rule_based_daily_summary.md", "# 每日预测复盘规则票汇总", a_rule_rows)

subprocess.run([sys.executable, str(ROOT / "tools" / "calc_hk_prediction_accuracy.py")], cwd=ROOT, check=True)
h_rule_rows = upsert(P / "hk_rule_based_daily_summary.csv", summary(H_RULE, "规则调整信号", "是", h_error, h_adjust, f"reports/港股预测命中复盘_{ISO}.md"))
markdown_summary(P / "hk_rule_based_daily_summary.md", "# 港股每日预测复盘规则票汇总", h_rule_rows)

write_report(
    R / f"预测命中复盘_{ISO}.md",
    "A股",
    A,
    stats(A),
    stats(A_RULE),
    "未触发进一步降级。正式规则票长江电力完整命中，但仅单日改善，正式票数量暂不扩张。",
    "长江电力完整兑现；能源方向判断正确，但严格执行后不能把所有大涨票算成命中。",
    a_error,
    "继续保留1-2只正式规则票；先确定可成交承接区，再看方向。失效后反包的样本仍按未命中记录。",
)
write_report(
    R / f"港股预测命中复盘_{ISO}.md",
    "港股",
    H,
    stats(H),
    stats(H_RULE),
    "维持收紧。唯一正式票中国移动仅部分命中，严格命中率0%、调整后50%。",
    "能源、金融和互联网修复方向兑现，但正式票没有给到计划低吸区。",
    h_error,
    "正式规则票继续限制为1只；科技至少再观察一个交易日的板块承接与收盘确认。",
)

subprocess.run([sys.executable, str(ROOT / "tools" / "calc_accuracy_since_inception.py")], cwd=ROOT, check=True)

print("A全量", stats(A), "A规则", stats(A_RULE))
print("港股全量", stats(H), "港股规则", stats(H_RULE))
