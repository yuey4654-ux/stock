import csv
import json
import time
from collections import defaultdict
from pathlib import Path
from urllib.request import Request, urlopen

BASE = Path.cwd()
DAILY = BASE / "prediction_tracking" / "daily_predictions.csv"
OUT = BASE / "prediction_tracking" / "rule_top2_vs_rule1_nonrule1_compare.csv"
DETAIL = BASE / "prediction_tracking" / "rule_top2_vs_rule1_nonrule1_detail.csv"
REPORT = BASE / "reports" / "规则前二_vs_规则一非规则一收益对比_2026-07-01.md"
BUY_TIME = "09:35"
SELL_TIME = "10:00"
SHARES = 200
HIT_RESULTS = {"命中", "部分命中", "未命中"}


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
            time.sleep(0.12)
            return out
        except Exception as exc:
            last_error = exc
            time.sleep(0.8 + attempt * 0.8)
    raise last_error


def load_rows():
    with DAILY.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    by_day = defaultdict(list)
    for row in rows:
        if row["市场"] != "A股":
            continue
        if row["复盘结果"] not in HIT_RESULTS:
            continue
        by_day[norm_date(row["目标日期"])].append(row)
    for day in by_day:
        by_day[day].sort(key=lambda row: int(row["排名"]))
    return dict(sorted(by_day.items()))


def build_price_maps(codes):
    maps = {}
    for code in sorted(codes):
        print(f"fetch {code}", flush=True)
        by_date = defaultdict(dict)
        dates = []
        for bar in fetch_m5(code):
            by_date[bar["date"]][bar["time"]] = bar["open"]
            if not dates or dates[-1] != bar["date"]:
                dates.append(bar["date"])
        maps[code] = {"by_date": by_date, "dates": dates}
    return maps


def next_date(pmap, day):
    if day not in pmap["dates"]:
        return None
    idx = pmap["dates"].index(day)
    return pmap["dates"][idx + 1] if idx + 1 < len(pmap["dates"]) else None


def is_nonrule(row):
    return row["预测类型"].startswith("非规则")


def select_rule_top2(rows):
    return [row for row in rows if not is_nonrule(row)][:2]


def select_rule1_nonrule1(rows):
    rule = [row for row in rows if not is_nonrule(row)]
    nonrule = [row for row in rows if is_nonrule(row)]
    selected = []
    if rule:
        selected.append(rule[0])
    if nonrule:
        selected.append(nonrule[0])
    return selected


def run_strategy(name, grouped, price_maps, selector):
    daily = []
    details = []
    skipped = []
    for day, rows in grouped.items():
        selected = selector(rows)
        if len(selected) < 2:
            skipped.append((day, "不足2只可选票"))
            continue
        cost = 0.0
        profit = 0.0
        wins = 0
        losses = 0
        sell_day_used = ""
        trade_count = 0
        for row in selected:
            code = row["代码"]
            pmap = price_maps[code]
            sell_day = next_date(pmap, day)
            if not sell_day:
                skipped.append((day, f"{code} 无下一交易日"))
                continue
            if BUY_TIME not in pmap["by_date"][day] or SELL_TIME not in pmap["by_date"][sell_day]:
                skipped.append((day, f"{code} 缺少指定时间价格"))
                continue
            buy = pmap["by_date"][day][BUY_TIME]
            sell = pmap["by_date"][sell_day][SELL_TIME]
            item_cost = buy * SHARES
            item_profit = (sell - buy) * SHARES
            cost += item_cost
            profit += item_profit
            sell_day_used = sell_day
            trade_count += 1
            if item_profit > 0:
                wins += 1
            elif item_profit < 0:
                losses += 1
            details.append({
                "策略": name,
                "目标日期": day,
                "卖出日期": sell_day,
                "排名": row["排名"],
                "代码": code,
                "名称": row["名称"],
                "预测类型": row["预测类型"],
                "买入价": f"{buy:.2f}",
                "卖出价": f"{sell:.2f}",
                "收益": f"{item_profit:.2f}",
                "收益率": f"{item_profit / item_cost * 100:.2f}%",
            })
        if trade_count:
            daily.append({
                "策略": name,
                "目标日期": day,
                "卖出日期": sell_day_used,
                "票数": str(trade_count),
                "买入金额": f"{cost:.2f}",
                "收益": f"{profit:.2f}",
                "收益率": f"{profit / cost * 100:.2f}%" if cost else "0.00%",
                "盈利票": str(wins),
                "亏损票": str(losses),
            })
    return daily, details, skipped


def aggregate(daily):
    cost = sum(float(row["买入金额"]) for row in daily)
    profit = sum(float(row["收益"]) for row in daily)
    wins = sum(int(row["盈利票"]) for row in daily)
    losses = sum(int(row["亏损票"]) for row in daily)
    losing_days = sum(float(row["收益"]) < 0 for row in daily)
    trades = sum(int(row["票数"]) for row in daily)
    return {
        "交易日数": len(daily),
        "单票交易数": trades,
        "买入金额": cost,
        "收益": profit,
        "收益率": profit / cost if cost else 0,
        "盈利票": wins,
        "亏损票": losses,
        "单票胜率": wins / trades if trades else 0,
        "亏损天数": losing_days,
    }


def main():
    grouped = load_rows()
    all_selected = []
    for rows in grouped.values():
        all_selected.extend(select_rule_top2(rows))
        all_selected.extend(select_rule1_nonrule1(rows))
    codes = {row["代码"] for row in all_selected}
    price_maps = build_price_maps(codes)

    daily_a, detail_a, skipped_a = run_strategy("规则内前两只", grouped, price_maps, select_rule_top2)
    daily_b, detail_b, skipped_b = run_strategy("规则内第一只+规则外第一只", grouped, price_maps, select_rule1_nonrule1)
    agg_a = aggregate(daily_a)
    agg_b = aggregate(daily_b)

    fields = ["策略", "目标日期", "卖出日期", "票数", "买入金额", "收益", "收益率", "盈利票", "亏损票"]
    with OUT.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(daily_a + daily_b)
    detail_fields = ["策略", "目标日期", "卖出日期", "排名", "代码", "名称", "预测类型", "买入价", "卖出价", "收益", "收益率"]
    with DETAIL.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=detail_fields)
        writer.writeheader()
        writer.writerows(detail_a + detail_b)

    def fmt_agg(name, agg):
        return f"| {name} | {agg['交易日数']} | {agg['单票交易数']} | {agg['买入金额']:.2f} | {agg['收益']:.2f} | {agg['收益率']*100:.2f}% | {agg['单票胜率']*100:.1f}% | {agg['亏损天数']} |"

    lines = [
        "# 规则前二_vs_规则一非规则一收益对比_2026-07-01",
        "",
        f"口径：A股已复盘预测票；{BUY_TIME} 买入，每只 200 股；下一交易日 {SELL_TIME} 卖出；成交价按 5 分钟 K 线开盘价；不计手续费、滑点和涨跌停成交限制。",
        "",
        "## 对比结论",
        "",
        "| 策略 | 交易日数 | 单票交易数 | 买入金额 | 收益 | 收益率 | 单票胜率 | 亏损天数 |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        fmt_agg("规则内前两只", agg_a),
        fmt_agg("规则内第一只+规则外第一只", agg_b),
        "",
        "## 每日对比",
        "",
        "| 策略 | 买入日 | 卖出日 | 票数 | 买入金额 | 收益 | 收益率 | 盈利票 | 亏损票 |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in daily_a + daily_b:
        lines.append(f"| {row['策略']} | {row['目标日期']} | {row['卖出日期']} | {row['票数']} | {row['买入金额']} | {row['收益']} | {row['收益率']} | {row['盈利票']} | {row['亏损票']} |")
    lines.extend([
        "",
        "## 文件",
        "",
        f"- 每日对比：`{OUT.as_posix()}`",
        f"- 逐票明细：`{DETAIL.as_posix()}`",
        f"- 跳过记录：规则内前两只 {len(skipped_a)} 条，规则一+非规则一 {len(skipped_b)} 条。",
    ])
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")
    print(f"A_profit={agg_a['收益']:.2f} A_return={agg_a['收益率']*100:.2f}% B_profit={agg_b['收益']:.2f} B_return={agg_b['收益率']*100:.2f}%")


if __name__ == "__main__":
    main()
