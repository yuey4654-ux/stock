import argparse
import csv
import json
from datetime import datetime
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[1]
POOL = ROOT / "prediction_tracking" / "watch_pool_full.csv"
POOL_MD = ROOT / "prediction_tracking" / "watch_pool_full.md"
HOT_LOG = ROOT / "prediction_tracking" / "daily_hot_stocks.csv"
HOT_SUMMARY = ROOT / "prediction_tracking" / "daily_hot_stock_summary.md"
SCORES = ROOT / "prediction_tracking" / "next_day_candidate_scores.csv"
REPORT_DIR = ROOT / "reports"
WORKBENCH = ROOT / "每日交易工作台"
WB_POOL = WORKBENCH / "10_全量自选池.csv"
WB_POOL_MD = WORKBENCH / "10_全量自选池.md"
WB_CURRENT = WORKBENCH / "07_当前股票池.md"


POOL_FIELDS = ["代码", "名称", "市场", "方向", "当前层级", "提醒条件", "降级条件", "来源", "更新时间"]
HOT_FIELDS = [
    "日期",
    "代码",
    "名称",
    "市场",
    "方向",
    "分类",
    "热度来源",
    "收盘价",
    "涨跌幅",
    "成交额",
    "热度评分",
    "入池动作",
    "记录备注",
]

THEME_KEYWORDS = [
    ("AI芯片", ["寒武纪", "海光", "AI芯片", "算力芯片", "芯片"]),
    ("半导体设备", ["北方华创", "中微", "华海清科", "芯源微", "盛美", "半导体设备"]),
    ("先进封装", ["长电", "通富", "华天", "晶方", "封装", "Chiplet"]),
    ("存储芯片", ["兆易", "佰维", "江波龙", "德明利", "存储", "DRAM", "NAND"]),
    ("CPO/光模块", ["中际旭创", "新易盛", "天孚", "光模块", "CPO"]),
    ("PCB/AI服务器", ["胜宏", "沪电", "深南", "东山", "PCB", "AI服务器", "服务器"]),
    ("液冷/算力", ["英维克", "液冷", "算力", "数据中心"]),
    ("机器人", ["机器人", "三花", "埃斯顿", "柯力"]),
    ("面板/消费电子", ["京东方", "TCL", "面板", "消费电子", "光学"]),
    ("氟化工/电池材料", ["多氟多", "氟", "电池", "锂"]),
    ("低空/军工", ["低空", "军工", "航天", "航空"]),
]

OBSERVATION_LEVELS = {"强势观察池", "轮动观察池", "低权重观察池", "降级观察池"}


def today_string() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, fields: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def request_json(url: str, params: dict) -> dict | None:
    session = requests.Session()
    session.trust_env = False
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = session.get(url, params=params, headers=headers, timeout=12)
        response.raise_for_status()
        return response.json()
    except Exception:
        return None


def fetch_eastmoney_hot(limit: int) -> list[dict]:
    params = {
        "pn": 1,
        "pz": max(limit * 2, 50),
        "po": 1,
        "np": 1,
        "fltt": 2,
        "invt": 2,
        "fid": "f6",
        "fs": "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23,m:0+t:81+s:2048",
        "fields": "f12,f14,f2,f3,f6,f20,f100,f109",
    }
    data = request_json("https://push2.eastmoney.com/api/qt/clist/get", params)
    diff = ((data or {}).get("data") or {}).get("diff") or []
    rows = []
    for item in diff:
        code = str(item.get("f12", "")).zfill(6)
        pct = float(item.get("f3") or 0)
        amount = float(item.get("f6") or 0)
        if not code or pct < 0:
            continue
        rows.append(
            {
                "代码": code,
                "名称": item.get("f14") or "",
                "市场": "A股",
                "方向": item.get("f100") or "",
                "收盘价": item.get("f2") or "",
                "涨跌幅": pct,
                "成交额": amount,
                "热度来源": "东方财富成交额/涨幅榜",
                "raw_score": pct * 3 + min(amount / 100000000, 80),
            }
        )
    return sorted(rows, key=lambda x: x["raw_score"], reverse=True)[:limit]


def load_fallback_hot(limit: int) -> list[dict]:
    rows = read_csv(SCORES)
    out = []
    for item in rows:
        try:
            score = float(item.get("评分") or 0)
            pct = float((item.get("涨跌幅") or "0").replace("%", ""))
        except ValueError:
            score, pct = 0, 0
        out.append(
            {
                "代码": str(item.get("代码", "")).zfill(6),
                "名称": item.get("名称", ""),
                "市场": "A股",
                "方向": item.get("方向", ""),
                "收盘价": item.get("收盘价", ""),
                "涨跌幅": pct,
                "成交额": "",
                "热度来源": "本地候选评分回退",
                "raw_score": score + max(pct, 0) * 2,
            }
        )
    return sorted(out, key=lambda x: x["raw_score"], reverse=True)[:limit]


def quote_prefix(code: str) -> str:
    if code.startswith(("8", "4")):
        return "bj"
    return "sh" if code.startswith(("6", "9")) else "sz"


def fetch_tencent_pool_hot(limit: int) -> list[dict]:
    pool = read_csv(POOL)
    if not pool:
        return []
    out = []
    for offset in range(0, len(pool), 50):
        chunk = pool[offset : offset + 50]
        symbols = ",".join(f"{quote_prefix(str(row['代码']).zfill(6))}{str(row['代码']).zfill(6)}" for row in chunk)
        try:
            text = requests.get(f"https://qt.gtimg.cn/q={symbols}", timeout=12).text
        except Exception:
            continue
        by_code = {str(row["代码"]).zfill(6): row for row in chunk}
        for line in text.splitlines():
            if "~" not in line:
                continue
            parts = line.split("=", 1)[1].strip('";').split("~")
            if len(parts) < 38:
                continue
            code = parts[2].zfill(6)
            try:
                close = float(parts[3])
                pct = float(parts[32])
                amount = float(parts[37]) * 10000
            except ValueError:
                continue
            if close <= 0 or pct <= 0:
                continue
            pool_row = by_code.get(code, {})
            out.append(
                {
                    "代码": code,
                    "名称": parts[1] or pool_row.get("名称", ""),
                    "市场": "A股",
                    "方向": pool_row.get("方向", ""),
                    "收盘价": f"{close:.2f}",
                    "涨跌幅": pct,
                    "成交额": amount,
                    "热度来源": "腾讯行情股票池涨幅/成交额回退",
                    "raw_score": pct * 4 + min(amount / 100000000, 80),
                }
            )
    return sorted(out, key=lambda x: x["raw_score"], reverse=True)[:limit]


def classify(name: str, direction: str, pct: float, score: float) -> tuple[str, str]:
    haystack = f"{name} {direction}"
    theme = direction or "其他热点"
    for candidate, keywords in THEME_KEYWORDS:
        if any(keyword in haystack for keyword in keywords):
            theme = candidate
            break
    if pct >= 9 or score >= 80:
        level = "强势观察池"
    elif pct >= 3 or score >= 55:
        level = "轮动观察池"
    else:
        level = "低权重观察池"
    return theme, level


def normalize_hot_level(current_level: str, fallback_level: str) -> str:
    if current_level in OBSERVATION_LEVELS:
        return current_level
    return fallback_level


def build_conditions(close_value: str, pct: float, theme: str) -> tuple[str, str]:
    try:
        close = float(close_value)
    except (TypeError, ValueError):
        close = 0
    if close <= 0:
        return (
            f"{theme}方向热度观察；等待放量站稳短线平台后再升级",
            f"明显弱于{theme}同题材或跌破近期平台则降级",
        )
    support_low = close * 0.965
    support_high = close * 0.99
    trigger = close * 1.012
    invalid = close * 0.94
    chase_note = "高开超过3%不追" if pct >= 3 else "先看承接，不追盘中急拉"
    return (
        f"回踩{support_low:.2f}-{support_high:.2f}不破，重新站回{trigger:.2f}；{chase_note}",
        f"跌破{invalid:.2f}降级；放量弱于{theme}同题材则继续降级",
    )


def merge_pool(hot_rows: list[dict], run_date: str) -> tuple[list[dict], list[dict]]:
    pool = read_csv(POOL)
    by_code = {str(row["代码"]).zfill(6): row for row in pool}
    log_rows = []

    for item in hot_rows:
        code = str(item["代码"]).zfill(6)
        if not code or not item["名称"]:
            continue
        pct = float(item.get("涨跌幅") or 0)
        theme, level = classify(item["名称"], item.get("方向", ""), pct, float(item.get("raw_score") or 0))
        remind, downgrade = build_conditions(str(item.get("收盘价") or ""), pct, theme)
        source = f"每日热门股票-{run_date}"
        action = "新增"
        if code in by_code:
            row = by_code[code]
            if theme and theme not in row.get("方向", ""):
                row["方向"] = f"{row.get('方向', '')}/{theme}".strip("/")
            row["当前层级"] = normalize_hot_level(row.get("当前层级", ""), level)
            row["提醒条件"] = row.get("提醒条件") or remind
            row["降级条件"] = row.get("降级条件") or downgrade
            if source not in row.get("来源", ""):
                row["来源"] = f"{row.get('来源', '')}+{source}".strip("+")
            row["更新时间"] = run_date
            action = "已存在-补分类/更新时间"
        else:
            row = {
                "代码": code,
                "名称": item["名称"],
                "市场": "A股",
                "方向": theme,
                "当前层级": level,
                "提醒条件": remind,
                "降级条件": downgrade,
                "来源": source,
                "更新时间": run_date,
            }
            pool.append(row)
            by_code[code] = row

        log_rows.append(
            {
                "日期": run_date,
                "代码": code,
                "名称": item["名称"],
                "市场": "A股",
                "方向": theme,
                "分类": by_code[code]["当前层级"],
                "热度来源": item["热度来源"],
                "收盘价": item.get("收盘价", ""),
                "涨跌幅": f"{pct:.2f}%",
                "成交额": item.get("成交额", ""),
                "热度评分": f"{float(item.get('raw_score') or 0):.1f}",
                "入池动作": action,
                "记录备注": "热门票只进入股票池观察，不自动升级为正式预测票",
            }
        )

    pool.sort(key=lambda row: (row.get("当前层级", ""), row.get("方向", ""), row.get("代码", "")))
    return pool, log_rows


def write_markdown_pool(pool: list[dict]) -> None:
    lines = ["# 全量自选池", "", "| 代码 | 名称 | 方向 | 层级 | 提醒条件 |", "| --- | --- | --- | --- | --- |"]
    for row in pool[:160]:
        lines.append(
            f"| {row['代码']} | {row['名称']} | {row['方向']} | {row['当前层级']} | {row['提醒条件']} |"
        )
    text = "\n".join(lines) + "\n"
    POOL_MD.write_text(text, encoding="utf-8")
    WORKBENCH.mkdir(parents=True, exist_ok=True)
    WB_POOL_MD.write_text(text, encoding="utf-8")
    WB_CURRENT.write_text(text, encoding="utf-8")


def append_hot_log(log_rows: list[dict]) -> list[dict]:
    old = read_csv(HOT_LOG)
    dates = {row["日期"] for row in log_rows}
    kept = [row for row in old if row.get("日期") not in dates]
    merged = kept + log_rows
    merged.sort(key=lambda row: (row["日期"], row["分类"], row["方向"], row["代码"]))
    write_csv(HOT_LOG, HOT_FIELDS, merged)
    return merged


def write_reports(run_date: str, log_rows: list[dict], all_log: list[dict]) -> Path:
    REPORT_DIR.mkdir(exist_ok=True)
    report = REPORT_DIR / f"每日热门股票入池分类_{run_date}.md"
    added = [row for row in log_rows if row["入池动作"] == "新增"]
    updated = [row for row in log_rows if row["入池动作"] != "新增"]
    source_names = sorted({row["热度来源"] for row in log_rows})
    lines = [
        f"# 每日热门股票入池分类 {run_date}",
        "",
        "## 处理结果",
        "",
        f"- 本次记录：{len(log_rows)} 只",
        f"- 新增入池：{len(added)} 只",
        f"- 已存在并更新分类/时间：{len(updated)} 只",
        f"- 数据来源：{'、'.join(source_names) if source_names else '无'}",
        "",
        "## 分类明细",
        "",
        "| 分类 | 方向 | 代码 | 名称 | 涨跌幅 | 入池动作 |",
        "| --- | --- | --- | --- | ---: | --- |",
    ]
    for row in log_rows:
        lines.append(
            f"| {row['分类']} | {row['方向']} | {row['代码']} | {row['名称']} | {row['涨跌幅']} | {row['入池动作']} |"
        )
    lines += [
        "",
        "## 使用规则",
        "",
        "- 热门股票只进入股票池和观察记录，不自动进入正式预测票。",
        "- 次日预测仍必须按承接区、触发位、失效位和高开不追规则筛选。",
        "- 若同题材连续冲高回落，后续只保留低权重观察，不作为规则票放宽依据。",
    ]
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")

    summary_lines = [
        "# 每日热门股票入池汇总",
        "",
        "| 日期 | 记录数 | 新增 | 已存在更新 | 主要方向 | 报告 |",
        "| --- | ---: | ---: | ---: | --- | --- |",
    ]
    by_date: dict[str, list[dict]] = {}
    for row in all_log:
        by_date.setdefault(row["日期"], []).append(row)
    for date in sorted(by_date):
        rows = by_date[date]
        main_dirs = []
        for row in rows:
            if row["方向"] not in main_dirs:
                main_dirs.append(row["方向"])
        summary_lines.append(
            f"| {date} | {len(rows)} | {sum(r['入池动作'] == '新增' for r in rows)} | "
            f"{sum(r['入池动作'] != '新增' for r in rows)} | {'; '.join(main_dirs[:6])} | "
            f"reports/每日热门股票入池分类_{date}.md |"
        )
    HOT_SUMMARY.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Add daily hot A-share stocks to the watch pool and classify them.")
    parser.add_argument("--date", default=today_string())
    parser.add_argument("--limit", type=int, default=30)
    args = parser.parse_args()

    hot = fetch_eastmoney_hot(args.limit)
    if not hot:
        hot = fetch_tencent_pool_hot(args.limit)
    if not hot:
        hot = load_fallback_hot(args.limit)
    pool, log_rows = merge_pool(hot, args.date)
    write_csv(POOL, POOL_FIELDS, pool)
    write_csv(WB_POOL, POOL_FIELDS, pool)
    write_markdown_pool(pool)
    all_log = append_hot_log(log_rows)
    report = write_reports(args.date, log_rows, all_log)
    print(json.dumps({"date": args.date, "count": len(log_rows), "report": str(report)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
