import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_rows(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def counts_from_ledger(rows):
    return (
        len(rows),
        sum(r["复盘结果"] == "命中" for r in rows),
        sum(r["复盘结果"] == "部分命中" for r in rows),
        sum(r["复盘结果"] == "未命中" for r in rows),
    )


def counts_from_daily(rows):
    return (
        sum(int(r["总数"]) for r in rows),
        sum(int(r["命中"]) for r in rows),
        sum(int(r["部分命中"]) for r in rows),
        sum(int(r["未命中"]) for r in rows),
    )


def paths(kind, month):
    if kind == "old":
        directory = ROOT / "prediction_tracking" / f"historical_backtest_2026_{month:02d}"
        return (
            directory / f"2026年{month}月规则倒推预测与复盘台账.csv",
            directory / f"2026年{month}月规则倒推每日统计.csv",
        )
    directory = ROOT / "prediction_tracking" / f"historical_backtest_latest_strategy_2026_{month:02d}"
    return (
        directory / f"2026年{month}月最新策略倒推预测与复盘台账.csv",
        directory / f"2026年{month}月最新策略倒推每日统计.csv",
    )


def main():
    errors = []
    for kind in ("old", "latest"):
        for month in range(1, 6):
            ledger_path, daily_path = paths(kind, month)
            ledger_counts = counts_from_ledger(read_rows(ledger_path))
            daily_counts = counts_from_daily(read_rows(daily_path))
            status = "OK" if ledger_counts == daily_counts else "MISMATCH"
            print(kind, month, "ledger", ledger_counts, "daily", daily_counts, status)
            if ledger_counts != daily_counts:
                errors.append((kind, month, ledger_counts, daily_counts))
    if errors:
        raise SystemExit(errors)


if __name__ == "__main__":
    main()
