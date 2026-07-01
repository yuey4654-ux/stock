import csv
import json
import time
from collections import defaultdict
from pathlib import Path
from urllib.request import Request, urlopen

BASE = Path.cwd()
DAILY = BASE / "prediction_tracking" / "daily_predictions.csv"
DETAIL = BASE / "prediction_tracking" / "top2_0935_buy_1000_sell_detail.csv"
SUMMARY = BASE / "prediction_tracking" / "top2_0935_buy_1000_sell_daily.csv"
REPORT = BASE / "reports" / "前两只票0935买入次日1000卖出收益测算_2026-07-01.md"
SHARES = 200
BUY_TIME = "09:35"
SELL_TIME = "10:00"


def norm_date(value):
    y, m, d = value.split("/")
    return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"


def symbol(code):
    return ("sh" if code.startswith("6") else "sz") + code


def fetch_m5(code):
    sym = symbol(code)
    url = f"https://ifzq.gtimg.cn/appstock/app/kline/mkline?param={sym},m5,,640"
    last_error = None
    for attempt in range(5):
        try:
            req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urlopen(req, timeout=20) as res:
                payload = json.loads(res.read().decode("utf-8"))
            bars = ((payload.get("data") or {}).get(sym) or {}).get("m5") or []
            out = []
            for bar in bars:
                stamp = bar[0]
                out.append({
                    "date": f"{stamp[:4]}-{stamp[4:6]}-{stamp[6:8]}",
                    "time": f"{stamp[8:10]}:{stamp[10:12]}",
                    "open": float(bar[1]),
                })
            time.sleep(0.15)
            return out
        except Exception as exc:
            last_error = exc
            time.sleep(0.8 + attempt * 0.8)
    raise last_error


def main():
    with DAILY.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    by_day = defaultdict(list)
    for row in rows:
        if row["市场"] != "A股":
            continue
        if row["复盘结果"] not in {"命中", "部分命中", "未命中"}:
            continue
        by_day[row["目标日期"]].append(row)

    selected = []
    for day in sorted(by_day, key=lambda x: norm_date(x)):
        day_rows = sorted(by_day[day], key=lambda r: int(r["排名"]))
        selected.extend(day_rows[:2])

    codes = sorted({row["代码"] for row in selected})
    price_maps = {}
    for code in codes:
        print(f"fetch {code}", flush=True)
        by_date = defaultdict(dict)
        dates = []
        for bar in fetch_m5(code):
            by_date[bar["date"]][bar["time"]] = bar["open"]
            if not dates or dates[-1] != bar["date"]:
                dates.append(bar["date"])
        price_maps[code] = {"by_date": by_date, "dates": dates}

    details = []
    skipped = []
    for row in selected:
        code = row["代码"]
        buy_date = norm_date(row["目标日期"])
        pmap = price_maps[code]
        dates = pmap["dates"]
        if buy_date not in dates:
            skipped.append((row, "无买入日分钟线"))
            continue
        idx = dates.index(buy_date)
        if idx + 1 >= len(dates):
            skipped.append((row, "无下一交易日分钟线"))
            continue
        sell_date = dates[idx + 1]
        if BUY_TIME not in pmap["by_date"][buy_date] or SELL_TIME not in pmap["by_date"][sell_date]:
            skipped.append((row, "缺少指定时间点价格"))
            continue
        buy_price = pmap["by_date"][buy_date][BUY_TIME]
        sell_price = pmap["by_date"][sell_date][SELL_TIME]
        cost = buy_price * SHARES
        profit = (sell_price - buy_price) * SHARES
        details.append({
            "目标日期": buy_date,
            "卖出日期": sell_date,
            "排名": row["排名"],
            "代码": code,
            "名称": row["名称"],
            "预测类型": row["预测类型"],
            "复盘结果": row["复盘结果"],
            "买入时间": BUY_TIME,
            "卖出时间": SELL_TIME,
            "买入价": f"{buy_price:.2f}",
            "卖出价": f"{sell_price:.2f}",
            "股数": str(SHARES),
            "买入金额": f"{cost:.2f}",
            "收益": f"{profit:.2f}",
            "收益率": f"{profit / cost * 100:.2f}%",
        })

    grouped = defaultdict(lambda: {"票数": 0, "买入金额": 0.0, "收益": 0.0, "盈利票": 0, "亏损票": 0, "卖出日期": ""})
    for row in details:
        g = grouped[row["目标日期"]]
        g["卖出日期"] = row["卖出日期"]
        g["票数"] += 1
        g["买入金额"] += float(row["买入金额"])
        g["收益"] += float(row["收益"])
        if float(row["收益"]) > 0:
            g["盈利票"] += 1
        elif float(row["收益"]) < 0:
            g["亏损票"] += 1

    summaries = []
    for day in sorted(grouped):
        g = grouped[day]
        summaries.append({
            "目标日期": day,
            "卖出日期": g["卖出日期"],
            "票数": str(g["票数"]),
            "买入金额": f"{g['买入金额']:.2f}",
            "收益": f"{g['收益']:.2f}",
            "收益率": f"{g['收益'] / g['买入金额'] * 100:.2f}%" if g["买入金额"] else "0.00%",
            "盈利票": str(g["盈利票"]),
            "亏损票": str(g["亏损票"]),
        })

    detail_fields = ["目标日期", "卖出日期", "排名", "代码", "名称", "预测类型", "复盘结果", "买入时间", "卖出时间", "买入价", "卖出价", "股数", "买入金额", "收益", "收益率"]
    summary_fields = ["目标日期", "卖出日期", "票数", "买入金额", "收益", "收益率", "盈利票", "亏损票"]
    with DETAIL.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=detail_fields)
        writer.writeheader()
        writer.writerows(details)
    with SUMMARY.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=summary_fields)
        writer.writeheader()
        writer.writerows(summaries)

    total_cost = sum(float(r["买入金额"]) for r in details)
    total_profit = sum(float(r["收益"]) for r in details)
    wins = sum(float(r["收益"]) > 0 for r in details)
    losses = sum(float(r["收益"]) < 0 for r in details)
    best = max(details, key=lambda r: float(r["收益"])) if details else None
    worst = min(details, key=lambda r: float(r["收益"])) if details else None

    lines = [
        "# 前两只票0935买入次日1000卖出收益测算_2026-07-01",
        "",
        f"口径：每天只买正式预测台账排名前 2 的 A 股；目标日 {BUY_TIME} 买入，每只 200 股；下一交易日 {SELL_TIME} 卖出；成交价按 5 分钟 K 线开盘价；不计手续费、滑点和涨跌停成交限制。",
        "",
        "## 汇总",
        "",
        f"- 已完成交易日：{len(summaries)} 天。",
        f"- 已完成单票交易：{len(details)} 笔。",
        f"- 累计买入金额：{total_cost:.2f} 元。",
        f"- 累计收益：{total_profit:.2f} 元。",
        f"- 累计收益率：{(total_profit / total_cost * 100 if total_cost else 0):.2f}%。",
        f"- 盈利票/亏损票：{wins}/{losses}。",
    ]
    if best and worst:
        lines += [
            f"- 单票最大盈利：{best['目标日期']} {best['名称']} {best['收益']} 元，收益率 {best['收益率']}。",
            f"- 单票最大亏损：{worst['目标日期']} {worst['名称']} {worst['收益']} 元，收益率 {worst['收益率']}。",
        ]
    lines += [
        "",
        "## 每日收益",
        "",
        "| 买入日 | 卖出日 | 票数 | 买入金额 | 收益 | 收益率 | 盈利票 | 亏损票 |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in summaries:
        lines.append(f"| {row['目标日期']} | {row['卖出日期']} | {row['票数']} | {row['买入金额']} | {row['收益']} | {row['收益率']} | {row['盈利票']} | {row['亏损票']} |")
    lines += [
        "",
        "## 文件",
        "",
        f"- 每日汇总：`{SUMMARY.as_posix()}`",
        f"- 逐票明细：`{DETAIL.as_posix()}`",
        f"- 跳过记录：{len(skipped)} 条，主要为港股、未复盘或尚无下一交易日分钟线。",
    ]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")
    print(f"days={len(summaries)} details={len(details)} skipped={len(skipped)} profit={total_profit:.2f} cost={total_cost:.2f}")


if __name__ == "__main__":
    main()
