import csv
import json
import time
from pathlib import Path
from urllib.request import Request, urlopen

BASE = Path.cwd()
DAILY = BASE / "prediction_tracking" / "daily_predictions.csv"
DETAIL = BASE / "prediction_tracking" / "open_to_next_open_backtest_detail.csv"
SUMMARY = BASE / "prediction_tracking" / "open_to_next_open_backtest_daily.csv"
REPORT = BASE / "reports" / "开盘买入次日开盘卖出收益测算_2026-06-30.md"
SHARES = 200


def norm_date(value):
    y, m, d = value.split("/")
    return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"


def market_code(code):
    return ("sh" if code.startswith("6") else "sz") + code


def read_predictions():
    with DAILY.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def fetch_kline(code):
    symbol = market_code(code)
    url = f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={symbol},day,2026-06-01,2026-07-10,640,qfq"
    last_error = None
    for attempt in range(6):
        try:
            request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urlopen(request, timeout=20) as response:
                payload = json.loads(response.read().decode("utf-8"))
            time.sleep(0.25)
            break
        except Exception as exc:
            last_error = exc
            time.sleep(1.0 + attempt * 1.0)
    else:
        raise last_error
    data = (payload.get("data") or {}).get(symbol) or {}
    klines = data.get("qfqday") or data.get("day") or []
    parsed = []
    for item in klines:
        parsed.append(
            {
                "date": item[0],
                "open": float(item[1]),
                "close": float(item[2]),
                "high": float(item[3]),
                "low": float(item[4]),
            }
        )
    return parsed


def main():
    rows = read_predictions()
    a_rows = [
        row
        for row in rows
        if row["市场"] == "A股"
        and row["复盘结果"] in {"命中", "部分命中", "未命中"}
    ]
    codes = sorted({row["代码"] for row in a_rows})
    kline_by_code = {}
    fetch_errors = {}
    for code in codes:
        try:
            print(f"fetch {code}", flush=True)
            kline_by_code[code] = fetch_kline(code)
        except Exception as exc:
            fetch_errors[code] = str(exc)
            kline_by_code[code] = []

    details = []
    skipped = []
    for row in a_rows:
        code = row["代码"]
        buy_date = norm_date(row["目标日期"])
        klines = kline_by_code.get(code, [])
        if not klines and code in fetch_errors:
            skipped.append((row, f"行情获取失败：{fetch_errors[code]}"))
            continue
        dates = [item["date"] for item in klines]
        if buy_date not in dates:
            skipped.append((row, "无买入日开盘价"))
            continue
        buy_index = dates.index(buy_date)
        if buy_index + 1 >= len(klines):
            skipped.append((row, "无下一交易日开盘价"))
            continue
        buy = klines[buy_index]
        sell = klines[buy_index + 1]
        buy_open = buy["open"]
        sell_open = sell["open"]
        profit = (sell_open - buy_open) * SHARES
        cost = buy_open * SHARES
        ret = profit / cost if cost else 0
        details.append(
            {
                "目标日期": buy_date,
                "卖出日期": sell["date"],
                "代码": code,
                "名称": row["名称"],
                "预测类型": row["预测类型"],
                "复盘结果": row["复盘结果"],
                "买入开盘价": f"{buy_open:.2f}",
                "卖出开盘价": f"{sell_open:.2f}",
                "股数": str(SHARES),
                "买入金额": f"{cost:.2f}",
                "收益": f"{profit:.2f}",
                "收益率": f"{ret * 100:.2f}%",
            }
        )

    grouped = {}
    for item in details:
        key = item["目标日期"]
        grouped.setdefault(
            key,
            {
                "目标日期": key,
                "卖出日期": item["卖出日期"],
                "票数": 0,
                "买入金额": 0.0,
                "收益": 0.0,
                "盈利票": 0,
                "亏损票": 0,
            },
        )
        group = grouped[key]
        group["票数"] += 1
        group["买入金额"] += float(item["买入金额"])
        group["收益"] += float(item["收益"])
        if float(item["收益"]) > 0:
            group["盈利票"] += 1
        elif float(item["收益"]) < 0:
            group["亏损票"] += 1

    summaries = []
    for key in sorted(grouped):
        group = grouped[key]
        cost = group["买入金额"]
        profit = group["收益"]
        summaries.append(
            {
                "目标日期": group["目标日期"],
                "卖出日期": group["卖出日期"],
                "票数": str(group["票数"]),
                "买入金额": f"{cost:.2f}",
                "收益": f"{profit:.2f}",
                "收益率": f"{profit / cost * 100:.2f}%" if cost else "0.00%",
                "盈利票": str(group["盈利票"]),
                "亏损票": str(group["亏损票"]),
            }
        )

    detail_fields = [
        "目标日期",
        "卖出日期",
        "代码",
        "名称",
        "预测类型",
        "复盘结果",
        "买入开盘价",
        "卖出开盘价",
        "股数",
        "买入金额",
        "收益",
        "收益率",
    ]
    summary_fields = ["目标日期", "卖出日期", "票数", "买入金额", "收益", "收益率", "盈利票", "亏损票"]
    with DETAIL.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=detail_fields)
        writer.writeheader()
        writer.writerows(details)
    with SUMMARY.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=summary_fields)
        writer.writeheader()
        writer.writerows(summaries)

    total_cost = sum(float(row["买入金额"]) for row in details)
    total_profit = sum(float(row["收益"]) for row in details)
    win_count = sum(float(row["收益"]) > 0 for row in details)
    loss_count = sum(float(row["收益"]) < 0 for row in details)
    best = max(details, key=lambda row: float(row["收益"])) if details else None
    worst = min(details, key=lambda row: float(row["收益"])) if details else None

    lines = [
        "# 开盘买入次日开盘卖出收益测算_2026-06-30",
        "",
        "测算口径：只统计 A 股正式预测台账；每只票目标日 9:30 按开盘价买入 200 股，下一交易日 9:30 按开盘价卖出；不考虑手续费、滑点、涨跌停无法成交、港股汇率。",
        "",
        "## 汇总",
        "",
        f"- 已完成交易：{len(details)} 笔。",
        f"- 累计买入金额：{total_cost:.2f} 元。",
        f"- 累计收益：{total_profit:.2f} 元。",
        f"- 累计收益率：{(total_profit / total_cost * 100 if total_cost else 0):.2f}%。",
        f"- 盈利票/亏损票：{win_count}/{loss_count}。",
    ]
    if best and worst:
        lines.extend(
            [
                f"- 单票最大盈利：{best['目标日期']} {best['名称']} {best['收益']} 元，收益率 {best['收益率']}。",
                f"- 单票最大亏损：{worst['目标日期']} {worst['名称']} {worst['收益']} 元，收益率 {worst['收益率']}。",
            ]
        )
    lines.extend(["", "## 每日收益", "", "| 目标日期 | 卖出日期 | 票数 | 买入金额 | 收益 | 收益率 | 盈利票 | 亏损票 |", "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |"])
    for row in summaries:
        lines.append(
            f"| {row['目标日期']} | {row['卖出日期']} | {row['票数']} | {row['买入金额']} | {row['收益']} | {row['收益率']} | {row['盈利票']} | {row['亏损票']} |"
        )
    lines.extend(
        [
            "",
            "## 说明",
            "",
            f"- 跳过记录：{len(skipped)} 条，主要为港股、未复盘票、行情接口失败或尚无下一交易日开盘价。",
            "- `2026-07-01` 目标日预测尚未有下一交易日开盘价，未纳入本次完成交易统计。",
            f"- 明细文件：`{DETAIL.as_posix()}`。",
            f"- 每日汇总：`{SUMMARY.as_posix()}`。",
        ]
    )
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")
    print(f"details={len(details)} skipped={len(skipped)} profit={total_profit:.2f} cost={total_cost:.2f}")


if __name__ == "__main__":
    main()
