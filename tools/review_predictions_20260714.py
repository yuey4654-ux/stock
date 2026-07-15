import csv
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRED = ROOT / "prediction_tracking"
REPORTS = ROOT / "reports"
TARGET = "2026/7/14"
TARGET_ISO = "2026-07-14"
LEDGER = PRED / "daily_predictions.csv"
FULL_CSV = PRED / "daily_review_summary.csv"
RULE_CSV = PRED / "rule_based_daily_summary.csv"
FULL_MD = PRED / "daily_review_summary.md"
RULE_MD = PRED / "rule_based_daily_summary.md"
REPORT = REPORTS / f"预测命中复盘_{TARGET_ISO}.md"

REVIEWS = {
    "600938": ("29.52", "+2.43%", "是", "否", "命中", "开29.51/高29.88/低28.70/收29.52。低点触及28.4-28.7承接区上沿，尾盘收在28.9确认位上方，能源方向完成回踩与确认。"),
    "600900": ("28.55", "+0.46%", "是", "否", "命中", "开28.40/高28.73/低28.21/收28.55。低点进入28.1-28.3承接区，收盘站回28.5，稳健高股息规则完整兑现。"),
    "600276": ("54.82", "-1.67%", "否", "否", "未命中", "开55.75/高55.98/低54.27/收54.82。盘中跌破54.4降级线，收盘未站回56.2；虽未触及53.6深失效位，但创新药防守确认失败。"),
    "002223": ("26.90", "+2.24%", "否", "否", "部分命中", "开26.49/高27.44/低26.33/收26.90。政策映射方向正确且收盘站上26.5，但未回踩25.9-26.2理想买点，按方向兑现、执行点不完整记部分命中。"),
    "601088": ("43.42", "+1.81%", "否", "否", "部分命中", "开42.66/高44.36/低42.47/收43.42。收盘站上42.8且能源方向偏强，但未进入41.8-42.2理想承接区，未给标准低吸点，记部分命中。"),
    "002422": ("48.50", "+8.26%", "是", "否", "命中", "开44.30/高48.99/低44.03/收48.50。低点落在44.0-44.5承接区，尾盘大幅站上45.2，创新药扩散与买点均兑现。"),
}

def read(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def write(path, rows, fields):
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, quoting=csv.QUOTE_ALL)
        w.writeheader(); w.writerows(rows)

def weight(row):
    kind = row["预测类型"]
    return 1.5 if kind.startswith("核心承接") else 0.8 if kind.startswith(("弹性进攻", "弹性观察")) else 1.0

def stats(rows):
    n=len(rows); h=sum(r["复盘结果"]=="命中" for r in rows); p=sum(r["复盘结果"]=="部分命中" for r in rows); m=sum(r["复盘结果"]=="未命中" for r in rows)
    wt=sum(weight(r) for r in rows); wh=sum(weight(r) for r in rows if r["复盘结果"]=="命中"); wa=sum(weight(r)*(1 if r["复盘结果"]=="命中" else .5 if r["复盘结果"]=="部分命中" else 0) for r in rows)
    return {"总数":str(n),"命中":str(h),"部分命中":str(p),"未命中":str(m),"严格命中率":f"{h/n*100:.1f}%" if n else "0.0%","调整后命中率":f"{(h+.5*p)/n*100:.1f}%" if n else "0.0%","严格加权命中率":f"{wh/wt*100:.1f}%" if wt else "0.0%","调整后加权命中率":f"{wa/wt*100:.1f}%" if wt else "0.0%"}

def counts(rows, prefix):
    x=[r for r in rows if r["预测类型"].startswith(prefix)]; return str(sum(r["复盘结果"]=="命中" for r in x)),str(len(x))

def summary(rows, signal_field):
    s=stats(rows); core=counts(rows,"核心承接"); stable=counts(rows,"稳健观察"); elastic=counts(rows,"弹性进攻")
    other=[r for r in rows if not r["预测类型"].startswith(("核心承接","稳健观察","弹性进攻"))]
    best="; ".join(r["名称"] for r in rows if r["复盘结果"]=="命中") or "无"
    worst="; ".join(r["名称"] for r in rows if r["复盘结果"]=="未命中") or "无"
    return {"目标日期":TARGET_ISO,"预测日期":TARGET_ISO,**s,"核心承接命中":core[0],"核心承接总数":core[1],"稳健观察命中":stable[0],"稳健观察总数":stable[1],"弹性进攻命中":elastic[0],"弹性进攻总数":elastic[1],"其他类型命中":str(sum(r["复盘结果"]=="命中" for r in other)),"其他类型总数":str(len(other)),"最佳预测":best,"最差预测":worst,"主要误差":"防守医药内部出现明显分化：康复器械与科伦走强，但恒瑞未守降级线；能源方向判断正确，不过中国神华没有给到计划承接买点。",signal_field:"否","下一步规则调整":"当日两只正式规则票全部命中，未触发新的调整信号；但此前收紧框架的失效条件要求连续两日规则票调整后加权命中率回到65%以上，因此下一交易日仍维持1-2只正式稳健票，科技反弹只作条件观察。适用范围：A股正式规则票。失效条件：若下一交易日规则票再度低于60%或加权低于65%，继续收紧；若连续第二日高于65%且无深失效，再考虑小幅恢复数量。","报告文件":f"reports/预测命中复盘_{TARGET_ISO}.md"}

def upsert(path, row):
    rows=read(path); fields=list(rows[0]); rows=[r for r in rows if r["目标日期"]!=TARGET_ISO]; rows.append({k:row.get(k,"") for k in fields}); rows.sort(key=lambda r:r["目标日期"]); write(path,rows,fields); return rows

def md(path,title,rows):
    fields=list(rows[0]); lines=[title,"",f"更新日期：{TARGET_ISO}","","| "+" | ".join(fields)+" |","| "+" | ".join(["---"]*len(fields))+" |"]
    lines += ["| "+" | ".join(r.get(k,"").replace("|","／") for k in fields)+" |" for r in rows]
    path.write_text("\n".join(lines)+"\n",encoding="utf-8")

def main():
    rows=read(LEDGER); fields=list(rows[0]); seen=set()
    for r in rows:
        if r["目标日期"]==TARGET and r["代码"] in REVIEWS:
            c,ch,t,i,res,note=REVIEWS[r["代码"]]; r.update({"收盘价":c,"涨跌幅":ch,"是否触发":t,"是否失效":i,"复盘结果":res,"复盘备注":note+" 数据日期：2026-07-14；来源：腾讯行情日线。"}); seen.add(r["代码"])
    if seen != set(REVIEWS): raise RuntimeError(f"未更新完整: {set(REVIEWS)-seen}")
    write(LEDGER,rows,fields)
    today=[r for r in rows if r["目标日期"]==TARGET]; rules=[r for r in today if not r["预测类型"].startswith("非规则")]
    full=upsert(FULL_CSV,summary(today,"策略提醒")); rule=upsert(RULE_CSV,summary(rules,"规则调整信号")); md(FULL_MD,"# 每日预测复盘全量汇总",full); md(RULE_MD,"# 每日预测复盘规则票汇总",rule)
    table="\n".join(f"| {r['排名']} | {r['名称']} `{r['代码']}` | {r['预测类型']} | {r['收盘价']} / {r['涨跌幅']} | {r['是否触发']} | {r['是否失效']} | {r['复盘结果']} | {r['复盘备注']} |" for r in today)
    fs,rs=stats(today),stats(rules)
    REPORT.write_text(f'''# 预测命中复盘 {TARGET_ISO}

## 策略调整提醒

- 今日未新增触发：两只正式规则票均命中，规则票严格命中率与调整后加权命中率均为 `100.0%`。
- 但暂不解除收紧：此前连续低命中的解除条件是连续两日规则票调整后加权命中率回到65%以上。下一交易日仍只保留1-2只稳健规则票；若再度低于阈值则继续收紧，若连续第二日达标且无深失效，再小幅恢复数量。

## 一句话结论

全量6票为 `3命中 / 2部分命中 / 1未命中`，严格命中率 `{fs['严格命中率']}`、调整后命中率 `{fs['调整后命中率']}`；正式规则票2票全部命中。风险偏好午后修复，能源、高股息和部分医药兑现，但理想买点纪律仍应保留。

## 新闻政策与美股影响

- 隔夜美股风险偏弱：7月13日道指跌约0.3%、标普500跌0.79%、纳指跌1.55%、费城半导体跌4.78%，AI与芯片股承压；油价上行并推高美债收益率。该组合利好能源相对强度、压制高估值科技，因此预测前将正式票压缩至中国海油和长江电力是有效降险。
- 国内康复辅助器具政策提高了医疗器械观察优先级，鱼跃医疗收涨2.24%，但没有给出计划内回踩买点，只能记部分命中；新闻没有替代买点和收盘确认。
- A股7月14日午后反攻：沪指涨1.36%、深成指涨2.77%、创业板指涨3.43%，全市场成交约2.72万亿元、逾4200股上涨；算力硬件和医药走强，军工、商业航天偏弱。对下一交易日的映射是：科技可恢复观察池，但正式规则票仍不宜追高，必须等待回踩承接与14:30后确认。
- 风险偏好变量继续关注油价、10年美债和美元：若油价冲高回落且美债收益率继续上行，能源追高与科技反弹都可能失效；规则票数量保持低位。

来源：[腾讯行情](https://qt.gtimg.cn/)、[A股7月14日收盘复盘](https://www.nbd.com.cn/articles/2026-07-14/4471050.html)、[美股7月13日收盘](https://apnews.com/article/84784dd049267a58ac547d8a1c7fcd02)。

## 逐票复盘

| 排名 | 股票 | 类型 | 收盘/涨跌幅 | 触发 | 失效 | 结果 | 复盘要点 |
| ---: | --- | --- | --- | --- | --- | --- | --- |
{table}

## 主要误差与明日规则调整建议

- 主要误差：防守医药内部强弱分化，恒瑞跌破降级线；中国神华方向正确但没有回踩到计划买点，说明“板块对”不等于“买点可执行”。
- 明日建议：正式规则票仍维持1-2只，优先低位稳健承接；科技反弹先列条件观察，高开超过3%不追；只有回踩不破且14:30后站回确认位才升级。上述建议在规则票连续第二日调整后加权命中率高于65%、且无深失效后才可适度放宽。
''',encoding="utf-8")
    print("全量",fs,"规则",rs)

if __name__ == "__main__": main()
