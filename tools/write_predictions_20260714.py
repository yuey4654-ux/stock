import csv
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRED = ROOT / "prediction_tracking"
REPORTS = ROOT / "reports"
WORKBENCH = ROOT / "每日交易工作台"

A_LEDGER = PRED / "daily_predictions.csv"
HK_LEDGER = PRED / "hk_daily_predictions.csv"
PREDICTION_DATE = "2026/7/14"
TARGET_DATE = "2026/7/14"
TARGET_DASH = "2026-07-14"

A_FIELDS = ["预测日期", "目标日期", "排名", "代码", "名称", "市场", "预测类型", "预测逻辑", "触发条件", "失效条件", "收盘价", "涨跌幅", "是否触发", "是否失效", "复盘结果", "复盘备注"]
HK_FIELDS = A_FIELDS + ["是否计入准确率"]


def row(rank: int, code: str, name: str, market: str, kind: str, logic: str, trigger: str, invalid: str, hk: bool = False) -> dict:
    result = {
        "预测日期": PREDICTION_DATE,
        "目标日期": TARGET_DATE,
        "排名": str(rank),
        "代码": code,
        "名称": name,
        "市场": market,
        "预测类型": kind,
        "预测逻辑": logic,
        "触发条件": trigger,
        "失效条件": invalid,
        "收盘价": "",
        "涨跌幅": "",
        "是否触发": "",
        "是否失效": "",
        "复盘结果": "待复盘",
        "复盘备注": f"{TARGET_DASH}全量样本；{'港股独立' if hk else 'A股'}台账，计入全量准确率。",
    }
    if hk:
        result["是否计入准确率"] = "是"
    return result


A_ROWS = [
    row(1, "600938", "中国海油", "A股", "稳健观察", "7月13日收28.82、+2.38%，在A股大跌日逆势走强；隔夜WTI原油上涨约1.8%，能源高股息是今天少数同时具备外盘顺风和防守属性的方向。只做回踩确认，不追油价消息高开。", "最佳买点：回踩28.4-28.7不破，14:30后重新站回28.9；高开超过3%不追。", "跌破28.0降级，放量跌破27.7视为失效；若原油冲高回落且能源板块不扩散，不触发。"),
    row(2, "600900", "长江电力", "A股", "稳健观察", "7月13日收28.42、+1.39%，成交放大且连续走强，在指数风险释放中体现低波动和高股息防守价值。今天作为与能源不同的稳健规则票，只看回踩承接。", "最佳买点：回踩28.1-28.3不破，重新站回28.5；若直接高开超过3%不追。", "跌破27.8降级，放量跌破27.5视为失效；若高股息板块整体转弱且收盘低于28.1，按未命中处理。"),
    row(3, "600276", "恒瑞医药", "A股", "非规则条件观察-创新药防守", "7月13日收55.75、平盘，明显强于沪深主指数，但连续两次只守结构、未完成收盘触发。今天保留防守观察，不再作为正式规则票。", "升级条件：回踩55.0-55.5不破，尾盘站回56.2；高开超过3%不追。", "跌破54.4降级，放量跌破53.6视为失效；若医药只局部活跃、不形成扩散，不升级。"),
    row(4, "002223", "鱼跃医疗", "A股", "非规则条件观察-康复器械", "7月13日收26.31、+1.11%，结构强于市场；康复辅助器具扩能提质政策对医疗器械有方向映射，但消息可能带来高开兑现，因此只观察标准回踩。", "升级条件：回踩25.9-26.2不破，尾盘站回26.5；高开超过3%或开盘急拉不追。", "跌破25.5降级，放量跌破25.1视为失效；若康复器械只有概念小票冲高，本票不升级。"),
    row(5, "601088", "中国神华", "A股", "非规则条件观察-高股息能源", "7月13日除权后收42.65、+4.00%，高股息能源在风险日有明显资金承接，但短线涨幅已大，今天只等分歧回踩，不把强势延续当作默认买点。", "升级条件：回踩41.8-42.2不破，尾盘重新站回42.8；高开超过3%不追。", "跌破41.2降级，放量跌破40.7视为失效；若能源高开后普遍回落，本票不升级。"),
    row(6, "002422", "科伦药业", "A股", "非规则条件观察-创新药扩散", "7月13日收44.80、+1.66%，创新药扩散中相对强于恒瑞，但上一交易日没有给到标准低吸点。今天继续验证承接，不因相对强势直接追涨。", "升级条件：回踩44.0-44.5不破，尾盘站回45.2；若高开超过3%不追。", "跌破43.5降级，放量跌破42.8视为失效；若创新药板块冲高回落，按条件观察未兑现处理。"),
]

HK_ROWS = [
    row(1, "00883.HK", "中国海洋石油", "港股", "稳健观察", "7月13日收22.26、+2.02%，隔夜WTI原油上涨约1.8%，能源方向具备外盘顺风和高股息防守属性。港股正式票优先，但高开超过4%仍不追。", "最佳买点：回踩22.0-22.2不破，重新站回22.4；高开超过4%必须等30分钟回踩。", "跌破21.7降级，放量跌破21.4视为失效；若油价和港股能源同步冲高回落，不触发。", True),
    row(2, "00941.HK", "中国移动", "港股", "稳健观察", "7月13日收79.25、+0.63%，连续多日保持上升结构，兼具高股息和低科技估值敏感度，适合在海外半导体大跌背景下作为防守锚。", "最佳买点：回踩78.6-79.0不破，尾盘站回79.5；高开超过4%不追。", "跌破78.0降级，放量跌破77.4视为失效；若高股息权重整体弱于恒指，不触发。", True),
    row(3, "01093.HK", "石药集团", "港股", "稳健观察", "7月13日收8.16、+0.62%，在恒生科技走弱时保持防守；A股创新药和康复政策提供情绪映射，但仍要求收盘确认。", "最佳买点：回踩7.98-8.08不破，尾盘站回8.22；高开超过4%不追。", "跌破7.82降级，放量跌破7.66视为失效；若港股医药弱于恒指且不能站回8.22，不触发。", True),
    row(4, "00388.HK", "香港交易所", "港股", "非规则条件观察-交易活跃度", "港交所7月13日收387.60、+0.68%，连续两次承接较好，但隔夜全球风险偏好转弱可能压制成交与估值，今天降为条件观察。", "升级条件：回踩383.8-386不破，尾盘站回389；高开超过4%不追。", "跌破381降级，放量跌破377视为失效；若恒指与成交额同步收缩，本票不升级。", True),
    row(5, "09618.HK", "京东集团-SW", "港股", "非规则条件观察-互联网消费", "7月13日收113.20、+2.72%，上一交易日完成标准回踩确认；但隔夜纳指与AI股明显转弱，今天不连续升级，只看能否守住昨日突破。", "升级条件：回踩111.0-112.5不破，尾盘站回114.5；高开超过4%不追。", "跌破109.5降级，放量跌破108视为失效；若恒生科技继续走弱且京东收盘低于112.5，不升级。", True),
    row(6, "01088.HK", "中国神华", "港股", "非规则条件观察-高股息能源", "7月13日收41.54、+1.66%，高股息能源在港股风险环境中相对稳，但煤炭与油价并非完全同一驱动，今天只作为能源扩散验证。", "升级条件：回踩40.8-41.3不破，尾盘站回41.8；高开超过4%不追。", "跌破40.4降级，放量跌破39.8视为失效；若只有油气上涨、煤炭不跟随，本票不升级。", True),
]


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(rows)


def upsert(path: Path, new_rows: list[dict], fields: list[str]) -> None:
    existing = [{field: row.get(field, "") for field in fields} for row in read_csv(path)]
    existing = [row for row in existing if row.get("目标日期") != TARGET_DATE]
    write_csv(path, existing + [{field: row.get(field, "") for field in fields} for row in new_rows], fields)


def table(rows: list[dict]) -> str:
    lines = ["| 排名 | 股票 | 类型 | 触发/升级条件 | 失效条件 |", "| ---: | --- | --- | --- | --- |"]
    for item in rows:
        lines.append(f"| {item['排名']} | {item['名称']} `{item['代码']}` | {item['预测类型']} | {item['触发条件']} | {item['失效条件']} |")
    return "\n".join(lines)


INFO = """## 信息前置快照

| 模块 | 最新核对 | 对今天的影响 |
| --- | --- | --- |
| 财联社与国内政策 | 14部门发布康复辅助器具产业扩能提质方案，脑机接口、康养机器人、智能康复设备获得政策关注；今天10:00有上半年进出口发布会，15:00有自然资源资产管理制度发布会。 | 康复器械只提高观察优先级，不替代买点；外贸和资源方向等待发布会信息，不提前押注。 |
| A股昨日盘面 | 沪指跌2.06%、深成指跌3.48%、创业板指跌3.10%，沪深成交约1.10万亿元；通信、算力、存储等科技票承接失败，医药、高股息、能源相对抗跌。 | 正式规则票压缩至2只，科技硬件继续冷却；优先能源、高股息和医药防守。 |
| 港股昨日盘面 | 恒指涨0.16%、恒生科技跌0.96%；港交所、京东兑现较好，中芯国际和华虹宏力继续失效。 | 港股正式票压缩至3只，半导体不进买入候选；互联网仅保留回踩确认样本。 |
| 隔夜美股与AI | 道指跌0.26%、标普跌0.79%、纳指跌1.55%、费城半导体跌4.78%；英伟达跌3.52%、AMD跌4.21%、博通跌3.98%、甲骨文跌6.47%。 | 对A/H科技、半导体、算力明显偏空，今天不抢反弹。 |
| 风险偏好变量 | VIX收17.16、上涨14.17%；10年美债收益率升至4.609%，美元指数微升0.04%；WTI原油上涨约1.8%，黄金基本持平。 | 总体偏risk-off；能源是少数明确顺风方向，但高开仍不追。 |

来源：[财联社提醒电报](https://api3.cls.cn/share/subject/9829?os=CailianpressWeb&sv=860)、[康复辅助器具政策背景](https://www.cncaprc.gov.cn/xxzcfg/770823.jhtml)、[美股7月13日收盘](https://apnews.com/article/84784dd049267a58ac547d8a1c7fcd02)、[腾讯行情](https://qt.gtimg.cn/)。
"""


def write_reports() -> tuple[Path, Path, Path, Path]:
    a_pred = PRED / f"今日预测票_{TARGET_DASH}.md"
    a_report = REPORTS / f"每日热点预测_{TARGET_DASH}.md"
    hk_pred = PRED / f"港股今日预测票_{TARGET_DASH}.md"
    hk_report = REPORTS / f"港股每日热点预测_{TARGET_DASH}.md"
    a_text = f"""# 今日预测票 {TARGET_DASH}

## 一句话结论

今天A股给6只全量样本，正式规则票仅中国海油、长江电力2只；其余4只统一标为非规则条件观察。隔夜科技与半导体风险继续释放，今天不抢科技反弹，优先能源、高股息和医药防守，任何高开都必须等回踩。

{INFO}
## A股预测票

{table(A_ROWS)}

## 执行纪律

- 正式规则票仅前2只，单票只适合轻仓试错；若沪指开盘30-60分钟不能止跌，两只正式票也只观察不执行。
- A股高开超过3%不追；必须回踩承接区不破，再看14:30后是否站回触发位。
- 康复器械政策只决定热点优先级，鱼跃医疗仍需真实承接；翔宇医疗等高波动概念票不列入今天预测批次。
- 半导体、存储、算力、PCB和AI服务器继续冷却，至少等板块止跌和收盘确认后再恢复。
"""
    hk_text = f"""# 港股今日预测票 {TARGET_DASH}

## 一句话结论

今天港股给6只独立样本，正式规则票为中国海洋石油、中国移动、石药集团3只；港交所、京东和中国神华只作非规则条件观察。能源、高股息和医药优先，互联网不追连续加速，半导体不列买入候选。

{INFO}
## 港股预测票

{table(HK_ROWS)}

## 执行纪律

- 港股正式规则票只保留前3只；若恒生科技低开后继续放量下杀，互联网条件票全部取消升级。
- 港股高开超过4%不追，先观察30分钟承接，再看尾盘收盘确认。
- 中国海洋石油受益于油价，但若油价盘中回落或能源板块高开低走，同样不触发。
- 中芯国际、华虹宏力已连续失效，今天不做抢反弹样本。
"""
    a_pred.write_text(a_text, encoding="utf-8")
    a_report.write_text(a_text.replace("# 今日预测票", "# 每日热点预测"), encoding="utf-8")
    hk_pred.write_text(hk_text, encoding="utf-8")
    hk_report.write_text(hk_text.replace("# 港股今日预测票", "# 港股每日热点预测"), encoding="utf-8")
    return a_pred, a_report, hk_pred, hk_report


def copy_outputs(paths: tuple[Path, Path, Path, Path]) -> None:
    if not WORKBENCH.exists():
        return
    a_pred, a_report, hk_pred, hk_report = paths
    pairs = [
        (A_LEDGER, WORKBENCH / "03_每日预测台账.csv"),
        (HK_LEDGER, WORKBENCH / "03A_港股预测台账.csv"),
        (a_pred, WORKBENCH / f"02_今日预测票_{TARGET_DASH}.md"),
        (hk_pred, WORKBENCH / f"02B_港股今日预测票_{TARGET_DASH}.md"),
        (a_report, WORKBENCH / "11_每日热点预测.md"),
        (hk_report, WORKBENCH / "11A_港股每日热点预测.md"),
    ]
    for source, destination in pairs:
        shutil.copyfile(source, destination)


def main() -> None:
    upsert(A_LEDGER, A_ROWS, A_FIELDS)
    upsert(HK_LEDGER, HK_ROWS, HK_FIELDS)
    paths = write_reports()
    subprocess.run(["python", str(ROOT / "tools" / "calc_hk_prediction_accuracy.py")], cwd=ROOT, check=True)
    copy_outputs(paths)
    print(paths[1])
    print(paths[3])
    print(f"A股 {len(A_ROWS)} 只，正式规则票 {sum(not item['预测类型'].startswith('非规则') for item in A_ROWS)} 只")
    print(f"港股 {len(HK_ROWS)} 只，正式规则票 {sum(not item['预测类型'].startswith('非规则') for item in HK_ROWS)} 只")


if __name__ == "__main__":
    main()
