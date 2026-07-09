import csv
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAIN_LEDGER = ROOT / "prediction_tracking" / "daily_predictions.csv"
HK_LEDGER = ROOT / "prediction_tracking" / "hk_daily_predictions.csv"
PRED_DIR = ROOT / "prediction_tracking"
REPORT_DIR = ROOT / "reports"
WORKBENCH = ROOT / "每日交易工作台"

PREDICTION_DATE = "2026/7/8"
TARGET_DATE = "2026/7/9"
TARGET_DASH = "2026-07-09"

FIELDS = [
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
    "是否计入准确率",
]

ROWS = [
    {
        "预测日期": PREDICTION_DATE,
        "目标日期": TARGET_DATE,
        "排名": "1",
        "代码": "09988.HK",
        "名称": "阿里巴巴-W",
        "市场": "港股",
        "预测类型": "稳健观察",
        "预测逻辑": "7月8日港股科技主线集体修复，阿里巴巴-W收107.50，日内从96.55低位拉回，成交显著放大；属于本轮港股互联网修复的核心锚。高波动后只看回踩承接，不追高。",
        "触发条件": "最佳买点：回踩102.5-105.0不破，重新站回108.5；若高开超过4%，等30分钟后仍守105且尾盘站回108.5。",
        "失效条件": "跌破100.0降级；放量跌破96.5视为失效。若冲高112上方后收盘跌回105下方，按未命中处理。",
        "收盘价": "",
        "涨跌幅": "",
        "是否触发": "",
        "是否失效": "",
        "复盘结果": "待复盘",
        "复盘备注": "港股独立台账样本，计入港股全量准确率。",
        "是否计入准确率": "是",
    },
    {
        "预测日期": PREDICTION_DATE,
        "目标日期": TARGET_DATE,
        "排名": "2",
        "代码": "00700.HK",
        "名称": "腾讯控股",
        "市场": "港股",
        "预测类型": "稳健观察",
        "预测逻辑": "腾讯控股7月8日收478.80，互联网龙头中波动低于阿里和快手，是港股科技修复中的稳健样本；适合作为恒科强弱的核心观察票。",
        "触发条件": "最佳买点：回踩468-474不破，重新站回482；若直接冲490上方，不追，只看尾盘是否站稳482。",
        "失效条件": "跌破462降级；放量跌破456视为失效。若恒科转弱且腾讯收回474下方，按未触发处理。",
        "收盘价": "",
        "涨跌幅": "",
        "是否触发": "",
        "是否失效": "",
        "复盘结果": "待复盘",
        "复盘备注": "港股独立台账样本，计入港股全量准确率。",
        "是否计入准确率": "是",
    },
    {
        "预测日期": PREDICTION_DATE,
        "目标日期": TARGET_DATE,
        "排名": "3",
        "代码": "00981.HK",
        "名称": "中芯国际",
        "市场": "港股",
        "预测类型": "稳健观察",
        "预测逻辑": "港股中芯国际7月8日收75.80，日内最高79.50后回落，半导体映射明确但上影线较长；只适合看回踩不破后的收盘确认。",
        "触发条件": "最佳买点：回踩73.5-75.0不破，重新站回77.0；若盘中上79但收盘低于77，不算升级。",
        "失效条件": "跌破72.0降级；放量跌破70.0视为失效。若A股半导体弱化且港股SMIC低于75，降低权重。",
        "收盘价": "",
        "涨跌幅": "",
        "是否触发": "",
        "是否失效": "",
        "复盘结果": "待复盘",
        "复盘备注": "港股独立台账样本，计入港股全量准确率。",
        "是否计入准确率": "是",
    },
    {
        "预测日期": PREDICTION_DATE,
        "目标日期": TARGET_DATE,
        "排名": "4",
        "代码": "01810.HK",
        "名称": "小米集团-W",
        "市场": "港股",
        "预测类型": "条件观察-AI终端/汽车",
        "预测逻辑": "小米集团-W 7月8日收25.30，科技消费和汽车链修复弹性较强；但日内涨幅大，明天只能等回踩承接，不直接追。",
        "触发条件": "升级条件：回踩24.3-24.8不破，14:30后站回25.6；若高开超过4%且30分钟内跌回25下方，不买。",
        "失效条件": "跌破23.8降级；放量跌破23.3视为失效。若恒科强但小米弱于指数，不升级。",
        "收盘价": "",
        "涨跌幅": "",
        "是否触发": "",
        "是否失效": "",
        "复盘结果": "待复盘",
        "复盘备注": "港股独立台账样本，计入港股全量准确率。",
        "是否计入准确率": "是",
    },
    {
        "预测日期": PREDICTION_DATE,
        "目标日期": TARGET_DATE,
        "排名": "5",
        "代码": "01024.HK",
        "名称": "快手-W",
        "市场": "港股",
        "预测类型": "条件观察-互联网弹性",
        "预测逻辑": "快手-W 7月8日收43.98，日内高低波动大，属于互联网修复中的高弹性分支；可观察但不作为稳健主仓。",
        "触发条件": "升级条件：回踩42.0-43.0不破，尾盘站回44.6；若只盘中冲高、收盘低于43，不升级。",
        "失效条件": "跌破41.0降级；放量跌破40.0视为失效。若互联网板块只有阿里独强，快手不升级。",
        "收盘价": "",
        "涨跌幅": "",
        "是否触发": "",
        "是否失效": "",
        "复盘结果": "待复盘",
        "复盘备注": "港股独立台账样本，计入港股全量准确率。",
        "是否计入准确率": "是",
    },
    {
        "预测日期": PREDICTION_DATE,
        "目标日期": TARGET_DATE,
        "排名": "6",
        "代码": "03690.HK",
        "名称": "美团-W",
        "市场": "港股",
        "预测类型": "条件观察-互联网消费",
        "预测逻辑": "美团-W 7月8日收80.90，修复力度落后阿里但走势较稳；适合作为互联网消费线是否扩散的条件观察样本。",
        "触发条件": "升级条件：回踩78.0-79.5不破，尾盘站回81.5；若收盘仍低于80，不升级。",
        "失效条件": "跌破77.5降级；放量跌破75.5视为失效。若消费互联网弱于恒科，放弃。",
        "收盘价": "",
        "涨跌幅": "",
        "是否触发": "",
        "是否失效": "",
        "复盘结果": "待复盘",
        "复盘备注": "港股独立台账样本，计入港股全量准确率。",
        "是否计入准确率": "是",
    },
    {
        "预测日期": PREDICTION_DATE,
        "目标日期": TARGET_DATE,
        "排名": "7",
        "代码": "01347.HK",
        "名称": "华虹半导体",
        "市场": "港股",
        "预测类型": "非规则观察-半导体弹性",
        "预测逻辑": "华虹半导体7月8日收186.10，日内最高198后明显回落，弹性强但波动也大；作为半导体情绪样本记录，不作为稳健票。",
        "触发条件": "只看回踩178-184不破后重新站回190；若高开冲198附近后回落，不追。",
        "失效条件": "跌破174降级；放量跌破170视为失效。若收盘低于184，按非规则观察未兑现。",
        "收盘价": "",
        "涨跌幅": "",
        "是否触发": "",
        "是否失效": "",
        "复盘结果": "待复盘",
        "复盘备注": "港股独立台账样本，计入港股全量准确率。",
        "是否计入准确率": "是",
    },
    {
        "预测日期": PREDICTION_DATE,
        "目标日期": TARGET_DATE,
        "排名": "8",
        "代码": "09880.HK",
        "名称": "优必选",
        "市场": "港股",
        "预测类型": "非规则观察-机器人",
        "预测逻辑": "优必选7月8日收88.30，日内从93.35回落，机器人弹性仍在但承接弱于互联网核心；只做博弈温度样本。",
        "触发条件": "只看回踩85.5-88.0不破后重新站回91；若开盘冲高但不能站回91，不触发。",
        "失效条件": "跌破85降级；放量跌破82视为失效。若机器人链未扩散，本票按非规则观察处理。",
        "收盘价": "",
        "涨跌幅": "",
        "是否触发": "",
        "是否失效": "",
        "复盘结果": "待复盘",
        "复盘备注": "港股独立台账样本，计入港股全量准确率。",
        "是否计入准确率": "是",
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


def normalize_row(row: dict) -> dict:
    out = {field: row.get(field, "") for field in FIELDS}
    out["市场"] = "港股"
    out["是否计入准确率"] = row.get("是否计入准确率") or "是"
    return out


def bootstrap_hk_ledger() -> list[dict]:
    existing = [normalize_row(row) for row in read_csv(HK_LEDGER)]
    if existing:
        return existing
    main_rows = read_csv(MAIN_LEDGER)
    hk_rows = [normalize_row(row) for row in main_rows if row.get("市场") == "港股" or row.get("代码", "").upper().endswith(".HK")]
    hk_rows.sort(key=lambda row: (row.get("目标日期", ""), row.get("排名", "")))
    return hk_rows


def markdown_table() -> str:
    lines = [
        "| 排名 | 股票 | 代码 | 层级 | 触发/升级条件 | 失效条件 |",
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
    md = PRED_DIR / f"港股明日预测票_{TARGET_DASH}.md"
    report = REPORT_DIR / f"港股每日热点预测_{TARGET_DASH}.md"
    table = markdown_table()
    text = f"""# 港股明日预测票 {TARGET_DASH}

## 一句话结论

港股单独给 8 只样本，并全部写入港股独立台账 `hk_daily_predictions.csv`；后续港股准确率单独由 `hk_daily_review_summary.csv/md` 统计，不再和 A 股预测混在一起。

## 信息前置快照

| 模块 | 记录 | 对明天预测的影响 |
| --- | --- | --- |
| 港股盘面 | 7月8日港股科技股集体修复，恒生科技指数强于大盘，阿里、腾讯、小米、快手、中芯国际等同步走强。 | 明天可以给 8 只样本，但全部按回踩承接和收盘确认处理。 |
| 行情数据 | Yahoo chart 接口显示：阿里巴巴-W收107.50，腾讯收478.80，中芯国际收75.80，小米收25.30，快手收43.98，美团收80.90，华虹半导体收186.10，优必选收88.30，数据日期均为2026-07-08。 | 触发位和失效位按7月8日收盘与日内区间设置。 |
| 风险点 | 港股T+0且波动更大，7月8日多只票日内高点回落，明天若高开容易冲高兑现。 | 高开不追，优先等30分钟后承接；盘中突破但收盘跌回触发位不算命中。 |
| 准确率口径 | 港股独立台账中 `是否计入准确率=是` 的票全部进入港股全量准确率。 | 本次8只分母固定进入港股待复盘样本。 |

## 港股预测票

{table}

## 执行纪律

- 港股高开超过 4% 不追；先看30分钟承接，再看尾盘是否站回触发位。
- 稳健观察优先阿里、腾讯、中芯；小米、快手、美团只做条件观察。
- 华虹半导体、优必选属于非规则弹性样本，计入准确率，但不作为主策略放宽依据。
"""
    md.write_text(text, encoding="utf-8")
    report.write_text(
        f"""# 港股每日热点预测 {TARGET_DASH}

## 当前市场状态

7月8日港股出现明显科技修复，互联网平台、半导体、AI终端和机器人弹性票同步活跃。外部报道显示恒生指数重回24000点附近，恒生科技指数涨幅更强，阿里巴巴、腾讯、小米、中芯国际、快手等为主要贡献方向。

## 明日港股主线

1. 互联网平台：阿里巴巴-W、腾讯控股、美团-W、快手-W。
2. 半导体：中芯国际、华虹半导体。
3. AI终端/汽车：小米集团-W。
4. 机器人弹性：优必选只做非规则观察。

## 港股预测样本

{table}

## 准确率口径

本次8只全部写入港股独立台账，全部计入港股全量准确率；后续复盘时会输出港股全量、分类型和每日准确率，不与A股台账混算。
""",
        encoding="utf-8",
    )
    return md, report


def main() -> None:
    rows = bootstrap_hk_ledger()
    rows = [
        row
        for row in rows
        if not (row.get("预测日期") == PREDICTION_DATE and row.get("目标日期") == TARGET_DATE)
    ]
    rows.extend(ROWS)
    write_csv(HK_LEDGER, rows, FIELDS)
    md, report = write_reports()

    subprocess.run(["python", str(ROOT / "tools" / "calc_hk_prediction_accuracy.py")], cwd=ROOT, check=True)

    if WORKBENCH.exists():
        shutil.copyfile(HK_LEDGER, WORKBENCH / "03A_港股预测台账.csv")
        shutil.copyfile(md, WORKBENCH / f"02B_港股明日预测票_{TARGET_DASH}.md")
        shutil.copyfile(report, WORKBENCH / "11A_港股每日热点预测.md")
        shutil.copyfile(PRED_DIR / "hk_daily_review_summary.md", WORKBENCH / "05A_港股复盘统计.md")
        shutil.copyfile(PRED_DIR / "hk_daily_review_summary.csv", WORKBENCH / "05A_港股复盘统计.csv")

    print(HK_LEDGER)
    print(md)
    print(report)


if __name__ == "__main__":
    main()
