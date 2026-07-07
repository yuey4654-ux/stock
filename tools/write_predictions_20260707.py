import csv
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "prediction_tracking" / "daily_predictions.csv"
PRED_DIR = ROOT / "prediction_tracking"
REPORT_DIR = ROOT / "reports"
WORKBENCH = ROOT / "每日交易工作台"

PREDICTION_DATE = "2026/7/7"
TARGET_DATE = "2026/7/7"
TARGET_DASH = "2026-07-07"


ROWS = [
    {
        "预测日期": PREDICTION_DATE,
        "目标日期": TARGET_DATE,
        "排名": "1",
        "代码": "600276",
        "名称": "恒瑞医药",
        "市场": "A股",
        "预测类型": "稳健观察",
        "预测逻辑": "7月6日医药、创新药方向逆势走强，恒瑞医药收56.77、+4.26%，成交额超百亿，属于主线分歧日里少数有承接的大票；适合按稳健观察，不追高。",
        "触发条件": "最佳买点：回踩55.2-56.2不破，重新站回57.4；若高开超过3%不追，只等回踩后尾盘仍能站回57.4。",
        "失效条件": "跌破53.3降级；放量跌破52.0视为失效。若冲高58.5-59.5不能站稳，先按止盈/观察处理。",
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
        "代码": "688981",
        "名称": "中芯国际",
        "市场": "A股",
        "预测类型": "稳健观察",
        "预测逻辑": "隔夜美股半导体/AI硬件修复，费城半导体和AMD、博通明显反弹；中芯国际7月6日收143.99、+2.62%，较高弹性存储票更适合作为半导体映射的稳健承接样本。",
        "触发条件": "最佳买点：回踩139.0-142.5不破，重新站回145.8；若高开超过3%不追，只看回踩后能否重新站回145.8。",
        "失效条件": "跌破135.3降级；放量跌破132.0视为失效。若只因外盘利好高开但收盘跌回142.5下方，不算命中。",
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
        "代码": "300059",
        "名称": "东方财富",
        "市场": "A股",
        "预测类型": "条件观察",
        "预测逻辑": "两市成交额仍在3万亿元上方，券商/互联网金融有成交活跃度支撑；东方财富7月6日收21.18、+0.57%，位置相对温和，但不是当日最强板块，只作条件观察。",
        "触发条件": "升级条件：回踩20.6-21.0不破，14:30后仍能站回21.45；若只盘中冲高、尾盘跌回21.2下方，不升级。",
        "失效条件": "跌破19.9降级；放量跌破19.4视为失效。若大盘成交额明显萎缩或券商板块弱于指数，放弃。",
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
        "代码": "000977",
        "名称": "浪潮信息",
        "市场": "A股",
        "预测类型": "条件观察-AI服务器",
        "预测逻辑": "隔夜AI硬件链修复，A股AI服务器可能有映射；但7月6日PCB/机器人等科技高位方向回落，浪潮信息收69.71、+5.06%，已经有一定加速，只能等承接确认。",
        "触发条件": "升级条件：回踩67.0-68.5不破，尾盘重新站回70.5；若高开超过3%且30分钟内跌回69下方，不买。",
        "失效条件": "跌破65.5降级；放量跌破63.2视为失效。若板块只有个股独涨、没有AI服务器扩散，不升级。",
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
        "排名": "5",
        "代码": "688525",
        "名称": "佰维存储",
        "市场": "A股",
        "预测类型": "非规则观察-存储芯片",
        "预测逻辑": "隔夜美股存储芯片和AI半导体反弹，A股存储方向有情绪映射；但佰维存储7月6日收454.70、+6.26%，波动和高开风险都高，不纳入规则票。",
        "触发条件": "只看回踩438-450不破，重新站回468；若直接高开冲高或涨幅超过5%后不回踩，不追。",
        "失效条件": "跌破435降级；放量跌破420视为失效。若冲高后收盘跌回450下方，按非规则观察失败处理。",
        "收盘价": "",
        "涨跌幅": "",
        "是否触发": "",
        "是否失效": "",
        "复盘结果": "待复盘",
        "复盘备注": "",
    },
]


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


def markdown_table() -> str:
    lines = [
        "| 排名 | 股票 | 代码 | 层级 | 买点/升级条件 | 失效条件 |",
        "| ---: | --- | --- | --- | --- | --- |",
    ]
    for row in ROWS:
        lines.append(
            f"| {row['排名']} | {row['名称']} | {row['代码']} | {row['预测类型']} | {row['触发条件']} | {row['失效条件']} |"
        )
    return "\n".join(lines)


def write_reports() -> tuple[Path, Path]:
    PRED_DIR.mkdir(exist_ok=True)
    REPORT_DIR.mkdir(exist_ok=True)
    md = PRED_DIR / f"今日预测票_{TARGET_DASH}.md"
    table_md = PRED_DIR / f"今日预测票_表格版_{TARGET_DASH}.md"
    report = REPORT_DIR / f"每日热点预测_{TARGET_DASH}.md"

    text = f"""# 今日预测票 {TARGET_DASH}

## 信息前置快照

| 模块 | 盘前记录 | 对今天预测的影响 |
| --- | --- | --- |
| 财联社与国内政策 | 7月6日A股收跌，医药、煤炭、银行、猪肉偏强；交易新规落地后高波动票继续分化。 | 正式规则票不扩张，优先稳健承接。 |
| 海外与美股 | 7月6日美股三大指数收涨，纳指涨1.12%，标普涨0.72%，道指涨0.29%；AI硬件链重现抱团，费城半导体反弹，AMD、博通、特斯拉强。 | 半导体/AI硬件允许观察，但只低吸承接，不追高。 |
| 风险偏好 | 美股风险偏好修复，但A股7月6日超3500股下跌、创业板指跌1.77%，内部仍偏分化。 | 规则票控制在2只，条件观察票不直接计入放宽依据。 |
| A股盘面验证 | 医药、煤炭、银行等防御方向强；PCB、小金属、元件、机器人等跌幅居前。 | 恒瑞医药优先，科技票只选中芯国际这类相对稳健映射。 |

## 新闻政策与美股影响

- 利好方向：创新药/医药、AI硬件、半导体、存储芯片、AI服务器。
- 利空或降权方向：机器人、PCB、小金属、元件等7月6日跌幅居前方向；前一日大涨且高开风险大的票。
- 今日规则：正式规则票只给2只，其他全部列为条件观察或非规则观察。新闻只决定方向优先级，不能替代回踩承接、触发位和失效位。

## 今日预测票

{markdown_table()}

## 执行纪律

- 今天不追高。高开超过3%默认等回踩，不能回踩就放弃。
- 正式可执行只看恒瑞医药、中芯国际；东方财富、浪潮信息需尾盘确认后才允许升级。
- 佰维存储只做非规则观察，不用于判断主策略是否放宽。
- 若美股科技利好导致A股半导体集体高开，反而要降低买点冲动，只等回踩不破。
"""
    md.write_text(text, encoding="utf-8")
    table_md.write_text(text, encoding="utf-8")

    report.write_text(
        f"""# 每日热点预测 {TARGET_DASH}

## 今日主线判断

今天是“外盘科技修复 + A股内部分化”的盘前环境。美股AI硬件和半导体反弹会抬高A股科技映射预期，但7月6日A股机器人、PCB、小金属、元件跌幅居前，说明不能把外盘利好直接等同于A股追高买点。

## 热点优先级

1. 医药/创新药：7月6日逆势走强，适合稳健观察，代表票恒瑞医药。
2. 半导体/AI硬件：受美股反弹映射，优先看中芯国际这类相对稳的承接票。
3. 券商/成交额受益：成交额仍高，东方财富可条件观察，但需要大盘成交继续支撑。
4. AI服务器/存储芯片：只看回踩确认，浪潮信息、佰维存储不追高。
5. 机器人/PCB：7月6日跌幅居前，今天只看修复承接，不做规则票扩张。

## 今日票池

{markdown_table()}
""",
        encoding="utf-8",
    )
    return md, report


def main() -> None:
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
    existing = [
        row
        for row in existing
        if not (row.get("预测日期") == PREDICTION_DATE and row.get("目标日期") == TARGET_DATE)
    ]
    write_csv(LEDGER, existing + ROWS, fields)
    md, report = write_reports()

    if WORKBENCH.exists():
        shutil.copyfile(LEDGER, WORKBENCH / "03_每日预测台账.csv")
        shutil.copyfile(md, WORKBENCH / f"02_今日预测票_{TARGET_DASH}.md")
        shutil.copyfile(report, WORKBENCH / "11_每日热点预测.md")
    print(md)
    print(report)


if __name__ == "__main__":
    main()
