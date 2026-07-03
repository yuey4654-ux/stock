import csv
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "prediction_tracking" / "daily_predictions.csv"
PRED_DIR = ROOT / "prediction_tracking"
REPORT_DIR = ROOT / "reports"
WORKBENCH = ROOT / "每日交易工作台"

PREDICTION_DATE = "2026/7/3"
TARGET_DATE = "2026/7/3"
TARGET_DASH = "2026-07-03"


ROWS = [
    {
        "预测日期": PREDICTION_DATE,
        "目标日期": TARGET_DATE,
        "排名": "1",
        "代码": "600378",
        "名称": "昊华科技",
        "市场": "A股",
        "预测类型": "稳健观察",
        "预测逻辑": "六氟化钨/电子特气/氟化工方向，7月2日收82.17、+1.44%，在科创50大跌中仍收红，但日内振幅很大，今天只看分歧后承接。",
        "触发条件": "最佳买点：09:40后回踩78.0-80.2不破，并重新站回82.5；若高开超过3%不追，只等回踩确认。",
        "失效条件": "跌破75.5降级；放量跌破73.8视为失效。卖点：默认下个交易日13:15；若今日冲高86-88不能站稳，先做减仓/止盈。",
        "收盘价": "",
        "涨跌幅": "",
        "是否触发": "",
        "是否失效": "",
        "复盘结果": "待复盘",
        "复盘备注": "",
    },
    {
        "预测日期": PREDICTION_DATE,
        "目标日期": TARGET_DATE,
        "排名": "2",
        "代码": "002125",
        "名称": "湘潭电化",
        "市场": "A股",
        "预测类型": "稳健观察",
        "预测逻辑": "磷酸铁锂/锰材料方向，7月2日收13.59、-2.09%，跌幅小于科技主线，位置相对低，适合作为低位稳健观察。",
        "触发条件": "最佳买点：09:40后回踩13.50-13.70不破，重新站回14.05；或突破14.22后回踩不破13.90。",
        "失效条件": "跌破13.30降级；放量跌破13.05视为失效。卖点：默认下个交易日13:15；若今日冲高14.55-14.80放量滞涨，先止盈。",
        "收盘价": "",
        "涨跌幅": "",
        "是否触发": "",
        "是否失效": "",
        "复盘结果": "待复盘",
        "复盘备注": "",
    },
    {
        "预测日期": PREDICTION_DATE,
        "目标日期": TARGET_DATE,
        "排名": "3",
        "代码": "300014",
        "名称": "亿纬锂能",
        "市场": "A股",
        "预测类型": "稳健观察",
        "预测逻辑": "电池/储能方向，7月2日收61.27、-3.13%，相对科技高位票抗跌，适合只看低吸承接，不做突破追高。",
        "触发条件": "最佳买点：09:40后回踩60.5-61.3不破，重新站回62.5；若直接高开超过3%不追。",
        "失效条件": "跌破59.4降级；放量跌破58.5视为失效。卖点：默认下个交易日13:15；若今日冲高64.5-65.5不能放量站稳，先止盈。",
        "收盘价": "",
        "涨跌幅": "",
        "是否触发": "",
        "是否失效": "",
        "复盘结果": "待复盘",
        "复盘备注": "",
    },
    {
        "预测日期": PREDICTION_DATE,
        "目标日期": TARGET_DATE,
        "排名": "4",
        "代码": "002407",
        "名称": "多氟多",
        "市场": "A股",
        "预测类型": "非规则观察-氟化工/PVDF",
        "预测逻辑": "氟化工/PVDF仍有题材热度，7月2日收54.82、-0.78%，未跌破51.8放弃线，但收盘未站回55，今天只作非规则强者承接观察。",
        "触发条件": "最佳买点：只看回踩53.0-54.0不破，并重新站回55.2；若高开秒冲或高开超过3%不追。",
        "失效条件": "跌破51.8放弃；放量跌破50视为失效。卖点：默认下个交易日13:15；若今日冲高57.5附近不能突破，先止盈。",
        "收盘价": "",
        "涨跌幅": "",
        "是否触发": "",
        "是否失效": "",
        "复盘结果": "待复盘",
        "复盘备注": "",
    },
]


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


def main():
    fields = [
        "预测日期",
        "目标日期",
        "排名",
        "代码",
        "名称",
        "市场",
        "预测类型",
        "预测逻辑",
        "触发条件",
        "失效条件",
        "收盘价",
        "涨跌幅",
        "是否触发",
        "是否失效",
        "复盘结果",
        "复盘备注",
    ]
    existing = read_csv(LEDGER)
    existing = [r for r in existing if not (r.get("预测日期") == PREDICTION_DATE and r.get("目标日期") == TARGET_DATE)]
    write_csv(LEDGER, existing + ROWS, fields)

    md = PRED_DIR / f"今日预测票_{TARGET_DASH}.md"
    table_md = PRED_DIR / f"今日预测票_表格版_{TARGET_DASH}.md"
    report = REPORT_DIR / f"每日热点预测_{TARGET_DASH}.md"

    table = "\n".join(
        f"| {r['排名']} | {r['名称']} | {r['代码']} | {r['预测类型']} | {r['触发条件']} | {r['失效条件']} |"
        for r in ROWS
    )
    md.write_text(
        f"""# 今日预测票 {TARGET_DASH}

## 新闻政策与美股影响

- 隔夜美股分化：道指偏强，但纳指和半导体方向偏弱，芯片股映射对A股半导体/CPO/AI芯片不友好。
- A股前一交易日风险较高：上证-2.03%、深成指-3.85%、创业板-5.71%、科创50-7.70%，科技主线不是普通分歧，而是批量破位。
- 财联社/产业方向仍有AI算力、CPO、半导体材料、电池材料等线索，但今天新闻只能做热点优先级，不能替代承接确认。
- 规则执行：今天强收紧，不做核心承接，不追高位科技；规则票控制在3只，且全部为稳健观察。

## 今日预测票

| 排名 | 股票 | 代码 | 类型 | 最佳买点 | 卖点/失效 |
| ---: | --- | --- | --- | --- | --- |
{table}

## 今日执行纪律

- 最佳固定模式仍按回测：稳健观察票优先 09:40 后确认买入，默认下个交易日 13:15 卖出。
- 今天是周五，若持有隔夜，默认卖点顺延到下个交易日 13:15。
- 如果 09:40 前后跌破承接区，不买；如果盘中跌破失效位，不能因为尾盘拉回而强行记买点。
- 今日最多执行2只稳健观察票；多氟多只作非规则观察，不影响主策略仓位。
""",
        encoding="utf-8",
    )
    table_md.write_text(md.read_text(encoding="utf-8"), encoding="utf-8")
    report.write_text(
        f"""# 每日热点预测 {TARGET_DASH}

## 热点排序

1. 六氟化钨/电子特气/氟化工：昨日部分标的逆势，昊华科技、和远气体有强度，但波动大，只看分歧承接。
2. 磷酸铁锂/电池材料：相对高位科技更低位，适合作为稳健观察备选。
3. AI算力/CPO/半导体：长期线索仍在，但隔夜美股半导体走弱叠加A股昨日批量破位，今日降权。
4. 面板/显示：京东方A昨日收红但盘中跌破失效线，今天不作为规则票。

## 今日主线判断

今天不是进攻日，是风险修复观察日。规则内只看昊华科技、湘潭电化、亿纬锂能这类相对低位/抗跌承接；高位半导体、PCB、CPO、AI芯片只观察，不追。
""",
        encoding="utf-8",
    )

    shutil.copyfile(LEDGER, WORKBENCH / "03_每日预测台账.csv")
    shutil.copyfile(md, WORKBENCH / f"02_今日预测票_{TARGET_DASH}.md")
    shutil.copyfile(table_md, WORKBENCH / f"02A_今日预测票_表格版_{TARGET_DASH}.md")
    shutil.copyfile(report, WORKBENCH / "11_每日热点预测.md")
    print(md)
    print(report)


if __name__ == "__main__":
    main()
