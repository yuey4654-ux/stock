import csv
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRED = ROOT / "prediction_tracking"
REPORTS = ROOT / "reports"
WORKBENCH = ROOT / "每日交易工作台"

HK_LEDGER = PRED / "hk_daily_predictions.csv"
HK_REPORT = REPORTS / "港股预测命中复盘_2026-07-10.md"
HK_SUMMARY_CSV = PRED / "hk_daily_review_summary.csv"
HK_SUMMARY_MD = PRED / "hk_daily_review_summary.md"

TARGET = "2026/7/10"

HK_REVIEWS = {
    "00981.HK": (
        "79.65",
        "-4.67%",
        "否",
        "否",
        "未命中",
        "收盘79.65，-4.67%；低点78.75跌破79.5-82.0承接区，收盘也未站回84.5确认位。虽未跌破77.0降级线，但港股半导体权重承接失败。数据：腾讯行情快照，开84.95/高87.60/低78.75/收79.65。"
    ),
    "01347.HK": (
        "185.50",
        "-8.08%",
        "否",
        "是",
        "未命中",
        "收盘185.50，-8.08%；低点183.90跌破186降级线，收盘也低于198与205升级位，半导体弹性样本明显回撤。数据：腾讯行情快照，开204.20/高218.80/低183.90/收185.50。"
    ),
    "00700.HK": (
        "460.20",
        "-2.00%",
        "否",
        "是",
        "未命中",
        "收盘460.20，-2.00%；低点458.80跌破462降级线，收盘也未站回476，腾讯承接转弱。虽未破456深失效位，但按规则记未命中。数据：腾讯行情快照，开472.80/高473.60/低458.80/收460.20。"
    ),
    "09988.HK": (
        "110.20",
        "+2.04%",
        "否",
        "否",
        "部分命中",
        "收盘110.20，+2.04%；低点109.00高于106-108理想承接区，没有给到标准回踩买点，但收盘重新站回110。方向正确、执行位不完整，只记部分命中。数据：腾讯行情快照，开110.00/高113.00/低109.00/收110.20。"
    ),
    "00388.HK": (
        "385.00",
        "+1.21%",
        "是",
        "否",
        "命中",
        "收盘385.00，+1.21%；低点381.00守住377-381承接区上沿，收盘站回384，港交所作为防守样本兑现。数据：腾讯行情快照，开383.00/高392.80/低381.00/收385.00。"
    ),
    "01810.HK": (
        "25.84",
        "+3.36%",
        "是",
        "否",
        "命中",
        "收盘25.84，+3.36%；低点24.50落在24.5-25.0承接区，尾盘站回25.4升级位，小米条件观察兑现。数据：腾讯行情快照，开25.22/高26.30/低24.50/收25.84。"
    ),
    "09618.HK": (
        "110.20",
        "+2.32%",
        "否",
        "否",
        "部分命中",
        "收盘110.20，+2.32%；低点108.20落在106-108.5承接区上沿，尾盘接近但未站上110.5升级位，京东守承接但确认不足。数据：腾讯行情快照，开109.60/高111.60/低108.20/收110.20。"
    ),
    "09880.HK": (
        "85.05",
        "-3.02%",
        "否",
        "否",
        "未命中",
        "收盘85.05，-3.02%；低点84.50已跌出86-88承接区，收盘也未站回90.5，机器人非规则样本未兑现。虽未跌破82深失效位，但按港股规则记未命中。数据：腾讯行情快照，开89.00/高90.75/低84.50/收85.05。"
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


def summarize(rows: list[dict]) -> dict:
    total = len(rows)
    hit = sum(r.get("复盘结果") == "命中" for r in rows)
    partial = sum(r.get("复盘结果") == "部分命中" for r in rows)
    miss = sum(r.get("复盘结果") == "未命中" for r in rows)
    return {
        "总数": str(total),
        "命中": str(hit),
        "部分命中": str(partial),
        "未命中": str(miss),
        "严格命中率": f"{hit / total * 100:.1f}%" if total else "0.0%",
        "调整后命中率": f"{(hit + 0.5 * partial) / total * 100:.1f}%" if total else "0.0%",
    }


def is_nonrule(row: dict) -> bool:
    return row.get("预测类型", "").startswith("非规则")


def is_formal_or_condition(row: dict) -> bool:
    return not is_nonrule(row)


def update_hk() -> tuple[dict, dict, dict]:
    rows = read_csv(HK_LEDGER)
    fields = list(rows[0].keys())
    for row in rows:
        if row.get("目标日期") == TARGET and row.get("代码") in HK_REVIEWS and row.get("复盘结果") == "待复盘":
            close, pct, triggered, invalid, result, note = HK_REVIEWS[row["代码"]]
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
    write_csv(HK_LEDGER, rows, fields)

    day_rows = [r for r in rows if r.get("目标日期") == TARGET]
    full_stats = summarize(day_rows)
    formal_rows = [r for r in day_rows if is_formal_or_condition(r)]
    formal_stats = summarize(formal_rows)
    nonrule_rows = [r for r in day_rows if is_nonrule(r)]
    nonrule_stats = summarize(nonrule_rows)

    subprocess.run(["python", str(ROOT / "tools" / "calc_hk_prediction_accuracy.py")], cwd=ROOT, check=True)

    HK_REPORT.write_text(
        f"""# 港股预测命中复盘 2026-07-10

## 一句话结论

港股昨天 8 票里 `2命中 / 2部分命中 / 4未命中`，严格命中率 `25.0%`，调整后命中率 `37.5%`。半导体高位票和腾讯明显走弱，只有港交所、小米两个样本完成了相对标准的承接确认。

## 港股统计

| 口径 | 总数 | 命中 | 部分命中 | 未命中 | 严格命中率 | 调整后命中率 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 港股全量预测票 | {full_stats['总数']} | {full_stats['命中']} | {full_stats['部分命中']} | {full_stats['未命中']} | {full_stats['严格命中率']} | {full_stats['调整后命中率']} |
| 正式/条件非非规则票 | {formal_stats['总数']} | {formal_stats['命中']} | {formal_stats['部分命中']} | {formal_stats['未命中']} | {formal_stats['严格命中率']} | {formal_stats['调整后命中率']} |
| 非规则观察票 | {nonrule_stats['总数']} | {nonrule_stats['命中']} | {nonrule_stats['部分命中']} | {nonrule_stats['未命中']} | {nonrule_stats['严格命中率']} | {nonrule_stats['调整后命中率']} |

## 逐票复盘

| 排名 | 股票 | 类型 | 收盘/涨跌幅 | 触发 | 失效 | 结果 | 复盘要点 |
| ---: | --- | --- | --- | --- | --- | --- | --- |
""" + "\n".join(
            f"| {r['排名']} | {r['名称']} `{r['代码']}` | {r['预测类型']} | {r['收盘价']} / {r['涨跌幅']} | {r['是否触发']} | {r['是否失效']} | {r['复盘结果']} | {r['复盘备注']} |"
            for r in day_rows
        ) + """

## 结论

- 港股延续了“半导体优先、互联网偏弱”的主判断，但高位半导体没有稳住，中芯国际和华虹宏力都从强势转为分歧回撤。
- 互联网平台里，阿里和京东属于方向没错但买点不干净，腾讯则直接跌破降级线，说明港股互联网承接仍弱于预期。
- 下一次港股规则票要更保守：半导体和互联网龙头都先等回踩承接后再看尾盘，不能因为前一日强势就默认隔日继续兑现。
""",
        encoding="utf-8",
    )
    return full_stats, formal_stats, nonrule_stats


def copy_outputs() -> None:
    if not WORKBENCH.exists():
        return
    pairs = [
        (HK_LEDGER, WORKBENCH / "03A_港股预测台账.csv"),
        (HK_SUMMARY_CSV, WORKBENCH / "05A_港股复盘统计.csv"),
        (HK_SUMMARY_MD, WORKBENCH / "05A_港股复盘统计.md"),
        (HK_REPORT, WORKBENCH / "14A_港股预测命中复盘_2026-07-10.md"),
    ]
    for src, dst in pairs:
        shutil.copyfile(src, dst)


def main() -> None:
    full_stats, formal_stats, nonrule_stats = update_hk()
    copy_outputs()
    print("港股全量", full_stats)
    print("港股正式/条件", formal_stats)
    print("港股非规则", nonrule_stats)
    print(HK_REPORT)


if __name__ == "__main__":
    main()
