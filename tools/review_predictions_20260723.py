import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "prediction_tracking"
R = ROOT / "reports"
LEDGER = P / "daily_predictions.csv"
ISO = "2026-07-23"
PREDISO = "2026-07-22"
NEXTISO = "2026-07-24"
REPORT_REL = f"reports/预测命中复盘_{ISO}.md"

REVIEWS = {
    "600025": ("10.17", "-0.49%", "否", "否", "部分命中", "开10.15/高10.28/低10.12/收10.17。低点进入10.05-10.15承接区且未破9.98降级线，但14:30后未站回10.23；只守承接未转强。"),
    "601088": ("45.32", "-0.26%", "否", "否", "部分命中", "开45.40/高45.70/低44.67/收45.32。回踩进入44.60-45.00计划区且未失效，但收盘较45.35确认位低0.03，条件观察未完成尾盘确认。"),
    "600938": ("32.99", "+1.85%", "否", "否", "部分命中", "开32.80/高33.30/低32.40/收32.99。油气方向和收盘强度正确，但全天未回到31.60-32.00计划买点；新闻映射不能替代可执行回踩。"),
    "603019": ("97.82", "-4.24%", "否", "否", "未命中", "开103.60/高104.14/低97.16/收97.82。高开后随半导体回落，跌破98.50承接下沿且未站回102.80，虽未触及97.00降级线，仍属承接与收盘确认失败。"),
    "000977": ("87.96", "-2.77%", "否", "否", "未命中", "开93.00/高96.37/低87.36/收87.96。盘中再度冲高回落，低点跌破87.80承接下沿，尾盘远低于91.50确认位；高风险观察未兑现。"),
}

NEXT_ROWS = [
    {
        "预测日期": ISO, "目标日期": NEXTISO, "排名": "1", "代码": "600406", "名称": "国电南瑞", "市场": "A股",
        "预测类型": "稳健观察",
        "预测逻辑": "7月23日收24.37、涨2.61%，电网设备受特高压招标与板块扩散支撑，且在科技分化日保持相对强度。",
        "触发条件": "回踩23.80-24.10不破，14:30后重新站回24.35；高开超过3%不追。",
        "失效条件": "跌破23.55降级，放量跌破23.30失效；电网设备板块弱于沪指或只剩个股独涨则不触发。",
        "收盘价": "", "涨跌幅": "", "是否触发": "", "是否失效": "", "复盘结果": "待复盘",
        "复盘备注": "2026-07-24唯一正式规则票；首次试错不超过计划最大仓位的1/3。数据基准：腾讯行情2026-07-23。",
    },
    {
        "预测日期": ISO, "目标日期": NEXTISO, "排名": "2", "代码": "601088", "名称": "中国神华", "市场": "A股",
        "预测类型": "非规则条件观察-煤炭高股息",
        "预测逻辑": "7月23日收45.32、跌0.26%，回踩计划区后基本守住但差尾盘确认；油价高位仍给煤炭相对强度支持。",
        "触发条件": "回踩44.65-45.00不破，14:30后站回45.45；高开超过3%不追。",
        "失效条件": "跌破44.35降级，放量跌破43.90失效；煤炭板块无扩散或油价快速回落则放弃。",
        "收盘价": "", "涨跌幅": "", "是否触发": "", "是否失效": "", "复盘结果": "待复盘",
        "复盘备注": "非规则条件观察；今日仅部分命中，未完成尾盘确认前不得升级。数据基准：腾讯行情2026-07-23。",
    },
    {
        "预测日期": ISO, "目标日期": NEXTISO, "排名": "3", "代码": "600938", "名称": "中国海油", "市场": "A股",
        "预测类型": "非规则高风险观察-油价映射",
        "预测逻辑": "7月23日收32.99、涨1.85%，油价高位带来映射，但连续上涨后消息溢价与冲高回落风险偏高。",
        "触发条件": "回踩32.20-32.55不破，尾盘重新站回33.00；高开超过3%不追。",
        "失效条件": "跌破31.90降级，放量跌破31.55失效；布油回落或油气板块无扩散则放弃。",
        "收盘价": "", "涨跌幅": "", "是否触发": "", "是否失效": "", "复盘结果": "待复盘",
        "复盘备注": "非规则油价映射票；新闻不替代买点，观察仓位低于正式票。数据基准：腾讯行情2026-07-23。",
    },
]


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
    adjusted_weight = sum(weight(r) * (1 if r["复盘结果"] == "命中" else 0.5 if r["复盘结果"] == "部分命中" else 0) for r in rows)
    return {
        "总数": str(n), "命中": str(hit), "部分命中": str(partial), "未命中": str(miss),
        "严格命中率": f"{hit / n * 100:.1f}%" if n else "0.0%",
        "调整后命中率": f"{(hit + 0.5 * partial) / n * 100:.1f}%" if n else "0.0%",
        "严格加权命中率": f"{strict_weight / total_weight * 100:.1f}%" if total_weight else "0.0%",
        "调整后加权命中率": f"{adjusted_weight / total_weight * 100:.1f}%" if total_weight else "0.0%",
    }


def count_type(rows, prefix):
    selected = [r for r in rows if r["预测类型"].startswith(prefix)]
    return str(sum(r["复盘结果"] == "命中" for r in selected)), str(len(selected))


def summary(rows, signal_field):
    core, stable, elastic = count_type(rows, "核心承接"), count_type(rows, "稳健观察"), count_type(rows, "弹性进攻")
    other = [r for r in rows if not r["预测类型"].startswith(("核心承接", "稳健观察", "弹性进攻"))]
    error = "华能水电和中国神华均回踩承接区但差尾盘确认；中国海油方向正确却没有计划买点；科技观察票继续出现高开或冲高后收盘失守。"
    adjustment = "触发原因：唯一正式规则票仅部分命中，严格命中率0%、调整后加权命中率50%，低于60%/65%阈值。建议：7月24日继续仅1只正式稳健票，科技/半导体暂停正式票，买点必须回踩不破并尾盘确认。适用范围：A股正式规则票及科技高波动候选。失效条件：连续两日规则票调整后加权命中率高于65%，且无盘中破位或冲高回落样本。"
    return {
        "目标日期": ISO, "预测日期": PREDISO, **stats(rows),
        "核心承接命中": core[0], "核心承接总数": core[1],
        "稳健观察命中": stable[0], "稳健观察总数": stable[1],
        "弹性进攻命中": elastic[0], "弹性进攻总数": elastic[1],
        "其他类型命中": str(sum(r["复盘结果"] == "命中" for r in other)), "其他类型总数": str(len(other)),
        "最佳预测": "; ".join(r["名称"] for r in rows if r["复盘结果"] in ("命中", "部分命中")) or "无",
        "最差预测": "; ".join(r["名称"] for r in rows if r["复盘结果"] == "未命中") or "无",
        "主要误差": error, signal_field: "是", "下一步规则调整": adjustment, "报告文件": REPORT_REL,
    }


def upsert(path, row):
    rows = read(path)
    fields = list(rows[0])
    rows = [r for r in rows if r["目标日期"] != ISO]
    rows.append({key: row.get(key, "") for key in fields})
    rows.sort(key=lambda r: r["目标日期"])
    write(path, rows, fields)
    return rows


def markdown_summary(path, title, rows):
    fields = list(rows[0])
    lines = [title, "", f"更新日期：{ISO}", "", "| " + " | ".join(fields) + " |", "| " + " | ".join(["---"] * len(fields)) + " |"]
    lines.extend("| " + " | ".join(r.get(key, "").replace("|", "／") for key in fields) + " |" for r in rows)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


rows = read(LEDGER)
fields = list(rows[0])
seen = set()
for row in rows:
    if row["目标日期"] == ISO and row["代码"] in REVIEWS and row["复盘结果"] == "待复盘":
        close, change, triggered, invalidated, result, note = REVIEWS[row["代码"]]
        row.update({"收盘价": close, "涨跌幅": change, "是否触发": triggered, "是否失效": invalidated, "复盘结果": result,
                    "复盘备注": note + " 数据日期：2026-07-23；来源：腾讯A股收盘行情。"})
        seen.add(row["代码"])
if seen != set(REVIEWS):
    raise RuntimeError(f"待复盘记录不完整：{set(REVIEWS) - seen}")
rows = [r for r in rows if r["目标日期"] != NEXTISO]
rows.extend(NEXT_ROWS)
write(LEDGER, rows, fields)

today = [r for r in rows if r["目标日期"] == ISO]
rule = [r for r in today if not r["预测类型"].startswith("非规则")]
full_stats, rule_stats = stats(today), stats(rule)
full_rows = upsert(P / "daily_review_summary.csv", summary(today, "策略提醒"))
rule_rows = upsert(P / "rule_based_daily_summary.csv", summary(rule, "规则调整信号"))
markdown_summary(P / "daily_review_summary.md", "# 每日预测复盘全量汇总", full_rows)
markdown_summary(P / "rule_based_daily_summary.md", "# 每日预测复盘规则票汇总", rule_rows)

table = "\n".join(
    f"| {r['排名']} | {r['名称']} `{r['代码']}` | {r['预测类型']} | {r['收盘价']} / {r['涨跌幅']} | {r['是否触发']} | {r['是否失效']} | {r['复盘结果']} | {r['复盘备注']} |"
    for r in today
)
next_table = "\n".join(
    f"| {r['排名']} | {r['名称']} `{r['代码']}` | {r['预测类型']} | {r['触发条件']} | {r['失效条件']} |" for r in NEXT_ROWS
)
(R / f"预测命中复盘_{ISO}.md").write_text(f"""# A股预测命中复盘 {ISO}

## 策略调整提醒

**继续收紧。** 唯一正式规则票华能水电仅部分命中，规则票严格命中率 `0.0%`、调整后加权命中率 `50.0%`，低于 `60%/65%` 阈值。7月24日正式规则票仍限制为1只，科技/半导体不进入正式票。

- 触发原因：正式规则票未完成尾盘确认；科技观察票继续出现冲高回落和承接失败。
- 建议调整：仅保留低波动、电网政策催化且能回踩确认的稳健票；高开超过3%不追。
- 适用范围：A股正式规则票，尤其科技、半导体和高波动成长方向。
- 失效条件：连续两日规则票调整后加权命中率高于65%，且无盘中破位或冲高回落样本。

## 一句话结论

全量5票为 `0命中 / 3部分命中 / 2未命中`，严格命中率 `0.0%`、调整后命中率 `30.0%`；正式规则票为 `0命中 / 1部分命中 / 0未命中`，调整后加权命中率 `50.0%`。

## 新闻政策与美股影响

- 财联社重要快讯与国内政策/产业：盘面继续围绕电力、电网设备、有色和锂电轮动；国家电网第三批特高压及输变电设备招标中标合计超过63亿元，提升电网设备优先级。政策只用于方向排序，仍需回踩、承接和尾盘确认。
- A股：沪指涨0.25%、深成指涨0.44%、创业板指涨0.25%，科创50跌3.78%；两市成交不足2.2万亿元、超过4200只个股上涨。电力/有色/锂电扩散，半导体明显下跌，科技权重承接失败。
- 海外隔夜：7月22日道指近乎持平，标普500跌约0.14%，纳指跌约0.57%；费城半导体指数由早盘下跌修复至收涨，但AI股波动仍大。布油继续上行，美国10年期国债收益率升至约4.65%，美元指数约101.5，成长估值压力未解除。
- 映射与仓位：利好A股电网设备、煤炭、油气的相对优先级；利空高估值半导体与AI服务器追高。7月24日规则票仅1只，买点更靠近承接区，科技票不列入正式规则。

参考：[A股7月23日收评](https://www.nbd.com.cn/articles/2026-07-23/4504529.html)、[A股指数与成交复核](https://www.thepaper.cn/newsDetail_forward_33643740)、[美股7月22日收盘与油价/美债](https://apnews.com/article/207dfa55d180fcc565420454178168c5)。

## 逐票复盘

| 排名 | 股票 | 类型 | 收盘/涨跌幅 | 触发 | 失效 | 结果 | 复盘要点 |
| ---: | --- | --- | --- | --- | --- | --- | --- |
{table}

## 主要误差

方向层面防守、煤炭和油气优先级并不差，但执行层面仍把“守住/上涨”与“完整触发”混在一起；中国海油没有计划买点，中科曙光和浪潮信息的科技反弹预期则被半导体板块弱化打断。

## 7月24日预测与规则调整

| 排名 | 股票 | 类型 | 触发条件 | 失效条件 |
| ---: | --- | --- | --- | --- |
{next_table}

- 正式票：仅国电南瑞1只，首次试错不超过计划最大仓位的1/3。
- 非规则票：中国神华、中国海油只观察，不作为策略放宽依据。
- 若电网设备板块低开弱于沪指，或国电南瑞高开超过3%且不回踩，取消正式触发。
- 若油价快速回落，煤炭和油气观察票同步降级；若科技继续缩量下跌，不新增科技候选。

数据日期：2026-07-23。个股与指数行情采用腾讯收盘快照，新闻与海外市场使用公开报道交叉核验。仅作条件化策略复盘，不构成确定性投资建议。
""", encoding="utf-8")

print("全量", full_stats)
print("规则", rule_stats)
print("下一交易日预测", len(NEXT_ROWS))
