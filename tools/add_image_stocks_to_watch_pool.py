import csv
import json
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[1]
POOL = ROOT / "prediction_tracking" / "watch_pool_full.csv"
POOL_MD = ROOT / "prediction_tracking" / "watch_pool_full.md"
WB_POOL = ROOT / "每日交易工作台" / "10_全量自选池.csv"
WB_POOL_MD = ROOT / "每日交易工作台" / "10_全量自选池.md"
WB_CURRENT = ROOT / "每日交易工作台" / "07_当前股票池.md"
REPORT = ROOT / "reports" / "观察池新增_科技板块清单_2026-07-02.md"


THEMES = {
    "CPO": ["中际旭创", "新易盛", "天孚通信", "华工科技"],
    "PCB": ["胜宏科技", "东山精密", "深南电路", "沪电股份"],
    "存储芯片": ["兆易创新", "佰维存储", "德明利", "江波龙"],
    "先进封装": ["通富微电", "长电科技", "华天科技", "晶方科技"],
    "光纤光缆": ["长飞光纤", "亨通光电", "中天科技", "烽火通信"],
    "MLCC": ["风华高科", "三环集团", "火炬电子", "国瓷材料"],
    "AI PC": ["京东方A", "春秋电子", "苏大维格", "雷神科技"],
    "AI芯片": ["寒武纪", "海光信息", "沐曦股份", "摩尔线程"],
    "AI服务器": ["工业富联", "浪潮信息", "紫光股份", "中科曙光"],
    "OCS": ["腾景科技", "福晶科技", "光库科技", "德科立"],
    "培育钻石": ["黄河旋风", "惠丰钻石", "恒盛能源", "四方达"],
    "玻璃基板": ["沃格光电", "彩虹股份", "五方光电", "旗滨集团"],
    "陶瓷基板": ["旭光电子", "中瓷电子", "博敏电子", "武汉凡谷"],
    "高速连接": ["立讯精密", "兆龙互连", "沃尔核材", "鼎通科技"],
    "铜箔": ["铜冠铜箔", "诺德股份", "嘉元科技", "德福科技"],
    "树脂": ["东材科技", "圣泉集团", "美联新材", "宏昌电子"],
    "电子布": ["宏和科技", "中国巨石", "中材科技", "国际复材"],
    "液冷": ["英维克", "冰轮环境", "江南新材", "中菱环境"],
    "六氟化钨": ["中船特气", "和远气体", "昊华科技", "华特气体"],
    "磷酸铁锂": ["丰元股份", "兴发集团", "亿纬锂能", "湘潭电化"],
}

ALIASES = {
    "华天": "华天科技",
    "国瓷": "国瓷材料",
    "中天": "中天科技",
    "紫光": "紫光股份",
    "惠丰": "惠丰钻石",
    "沃尔": "沃尔核材",
    "中材": "中材科技",
    "和远": "和远气体",
    "兴发": "兴发集团",
    "京东方A": "京东方Ａ",
}

MANUAL_LISTED = {
    "京东方Ａ": {"f12": "000725", "f14": "京东方Ａ", "f13": ""},
    "雷神科技": {"f12": "872190", "f14": "雷神科技", "f13": ""},
    "惠丰钻石": {"f12": "839725", "f14": "惠丰钻石", "f13": ""},
}


def get_universe():
    cache = ROOT / "prediction_tracking" / "historical_backtest_cache" / "universe.json"
    if cache.exists():
        cached = json.loads(cache.read_text(encoding="utf-8"))
        return [{"f12": row["代码"], "f14": row["名称"], "f13": ""} for row in cached]
    rows = []
    for page in range(1, 80):
        params = {
            "pn": page,
            "pz": 100,
            "po": 1,
            "np": 1,
            "fltt": 2,
            "invt": 2,
            "fid": "f3",
            "fs": "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23,m:0+t:81+s:2048",
            "fields": "f12,f14,f13",
        }
        data = requests.get("https://push2.eastmoney.com/api/qt/clist/get", params=params, timeout=10).json().get("data") or {}
        diff = data.get("diff") or []
        if not diff:
            break
        rows.extend(diff)
        if page * 100 >= int(data.get("total", 0)):
            break
    return rows


def read_pool():
    if not POOL.exists():
        return []
    with POOL.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_pool(rows):
    fields = ["代码", "名称", "市场", "方向", "当前层级", "提醒条件", "降级条件", "来源", "更新时间"]
    with POOL.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    WB_POOL.parent.mkdir(parents=True, exist_ok=True)
    with WB_POOL.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def quote(code):
    if code.startswith(("8", "4")):
        prefix = "bj"
    else:
        prefix = "sh" if code.startswith(("6", "9")) else "sz"
    text = requests.get(f"https://qt.gtimg.cn/q={prefix}{code}", timeout=8).text
    if "~" not in text:
        return None
    parts = text.split("=")[1].strip('";').split("~")
    try:
        return {
            "name": parts[1],
            "code": parts[2],
            "close": float(parts[3]),
            "prev": float(parts[4]),
            "open": float(parts[5]),
            "high": float(parts[33]),
            "low": float(parts[34]),
        }
    except Exception:
        return None


def build_conditions(name, theme, q):
    if not q or not q["close"]:
        return (
            f"{theme}方向观察；等待放量站稳短线平台后再升级",
            "跌破近期平台或明显弱于同题材则降级",
        )
    close = q["close"]
    low = q["low"]
    support_low = max(low, close * 0.965)
    support_high = close * 0.99
    trigger = close * 1.01
    invalid = min(low * 0.985, close * 0.94)
    return (
        f"回踩{support_low:.2f}-{support_high:.2f}不破，重新站回{trigger:.2f}；高开超过3%不追",
        f"跌破{invalid:.2f}降级；放量弱于{theme}同题材则继续降级",
    )


def main():
    universe = get_universe()
    existing_names = {item["f14"] for item in universe}
    for item in MANUAL_LISTED.values():
        if item["f14"] not in existing_names:
            universe.append(item)
    by_name = {item["f14"]: item for item in universe}
    existing = read_pool()
    by_code = {row["代码"]: row for row in existing}

    added = []
    existed = []
    unmatched = []

    for theme, names in THEMES.items():
        for raw_name in names:
            name = ALIASES.get(raw_name, raw_name)
            item = by_name.get(name)
            if not item:
                candidates = [x for x in universe if name in x["f14"] or x["f14"] in name]
                if candidates:
                    item = candidates[0]
                    name = item["f14"]
            if not item:
                unmatched.append({"主题": theme, "名称": raw_name})
                continue
            code = str(item["f12"]).zfill(6)
            q = quote(code)
            remind, downgrade = build_conditions(name, theme, q)
            if code in by_code:
                row = by_code[code]
                if theme not in row["方向"]:
                    row["方向"] = f"{row['方向']}/{theme}"
                row["提醒条件"] = row["提醒条件"] or remind
                row["降级条件"] = row["降级条件"] or downgrade
                row["来源"] = row["来源"] + "+图片科技板块补充" if "图片科技板块补充" not in row["来源"] else row["来源"]
                row["更新时间"] = "2026-07-02"
                existed.append({"代码": code, "名称": name, "主题": theme})
                continue
            level = "轮动观察池"
            if theme in {"CPO", "PCB", "存储芯片", "先进封装", "AI服务器", "液冷"}:
                level = "强势观察池"
            row = {
                "代码": code,
                "名称": name,
                "市场": "A股",
                "方向": theme,
                "当前层级": level,
                "提醒条件": remind,
                "降级条件": downgrade,
                "来源": "图片科技板块补充",
                "更新时间": "2026-07-02",
            }
            existing.append(row)
            by_code[code] = row
            added.append({"代码": code, "名称": name, "主题": theme, "层级": level})

    existing.sort(key=lambda r: (r["当前层级"], r["方向"], r["代码"]))
    write_pool(existing)

    theme_lines = []
    for theme, names in THEMES.items():
        matched = [x for x in added + existed if x["主题"] == theme]
        theme_lines.append(f"| {theme} | {len(matched)} | " + "、".join(f"{x['名称']}({x['代码']})" for x in matched) + " |")

    added_lines = "\n".join(f"| {x['主题']} | {x['代码']} | {x['名称']} | {x['层级']} |" for x in added)
    unmatched_lines = "\n".join(f"| {x['主题']} | {x['名称']} | 未匹配到A股简称，暂不加入可交易池 |" for x in unmatched)
    if not unmatched_lines:
        unmatched_lines = "| - | - | 无 |"

    REPORT.write_text(
        f"""# 观察池新增 - 科技板块清单

## 处理结果

- 新增股票：{len(added)} 只
- 已存在并补充主题：{len(existed)} 只
- 未匹配/疑似未上市：{len(unmatched)} 个

## 分主题归档

| 主题 | 匹配数量 | 股票 |
| --- | ---: | --- |
{chr(10).join(theme_lines)}

## 本次新增明细

| 主题 | 代码 | 名称 | 层级 |
| --- | --- | --- | --- |
{added_lines}

## 未加入可交易池

| 主题 | 名称 | 原因 |
| --- | --- | --- |
{unmatched_lines}

## 后续使用规则

- 这些票先进入观察池，不自动进入正式预测票。
- 每天预测仍按“稳健观察优先版收紧策略”筛选，只有主线强、不过热、承接区清楚的票才能进入规则内。
- 高弹性、连续加速、未给回踩买点的票，只能列为非规则观察。
""",
        encoding="utf-8",
    )

    # Compact markdown copies for daily workbench.
    md_rows = existing[:120]
    md = "# 全量自选池\n\n| 代码 | 名称 | 方向 | 层级 | 提醒条件 |\n| --- | --- | --- | --- | --- |\n"
    md += "\n".join(f"| {r['代码']} | {r['名称']} | {r['方向']} | {r['当前层级']} | {r['提醒条件']} |" for r in md_rows)
    POOL_MD.write_text(md, encoding="utf-8")
    WB_POOL_MD.write_text(md, encoding="utf-8")
    WB_CURRENT.write_text(md, encoding="utf-8")

    print(json.dumps({"added": added, "existed": existed, "unmatched": unmatched}, ensure_ascii=False, indent=2))
    print(REPORT)


if __name__ == "__main__":
    main()
