import fs from "fs";

const csvPath = `${process.cwd()}/每日交易工作台/03_每日预测台账.csv`;

function parseCsv(text) {
  text = text.replace(/^\uFEFF/, "");
  const rows = [];
  let row = [];
  let field = "";
  let q = false;
  for (let i = 0; i < text.length; i += 1) {
    const c = text[i];
    const n = text[i + 1];
    if (q) {
      if (c === '"' && n === '"') {
        field += '"';
        i += 1;
      } else if (c === '"') {
        q = false;
      } else {
        field += c;
      }
    } else if (c === '"') {
      q = true;
    } else if (c === ",") {
      row.push(field);
      field = "";
    } else if (c === "\n") {
      row.push(field);
      rows.push(row);
      row = [];
      field = "";
    } else if (c !== "\r") {
      field += c;
    }
  }
  if (field.length || row.length) {
    row.push(field);
    rows.push(row);
  }
  const header = rows.shift();
  return rows
    .filter((r) => r.some((x) => x !== ""))
    .map((r) => Object.fromEntries(header.map((h, i) => [h, r[i] ?? ""])));
}

function normDate(s) {
  const [y, m, d] = String(s).split(/[/-]/);
  return `${y}-${String(m).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
}

function isRule(row) {
  return !String(row.prediction_type).startsWith("非规则");
}

function score(rows) {
  const hit = rows.filter((r) => r.result === "命中").length;
  const partial = rows.filter((r) => r.result === "部分命中").length;
  const miss = rows.filter((r) => r.result === "未命中").length;
  return {
    total: rows.length,
    hit,
    partial,
    miss,
    strict_rate: rows.length ? `${((hit / rows.length) * 100).toFixed(1)}%` : "0.0%",
    adjusted_rate: rows.length ? `${(((hit + partial * 0.5) / rows.length) * 100).toFixed(1)}%` : "0.0%",
  };
}

// These labels were produced from the 2026-06-22 Eastmoney daily-K replay.
// Keep this script offline so future validation is reproducible even if the quote endpoint is unavailable.
const rejectedByNewRules = new Map([
  ["2026-06-15|000547", "触发失效条件，直接降级"],
  ["2026-06-15|9660.HK", "弹性票高开/转弱后长上影，过滤追涨"],
  ["2026-06-15|2432.HK", "弹性票长上影且收盘不确认，降级观察"],
  ["2026-06-16|300316", "核心承接收盘未转强"],
  ["2026-06-16|0981.HK", "触发失效条件，直接降级"],
  ["2026-06-18|002837", "核心承接收盘未转强"],
  ["2026-06-22|06613.HK", "触发失效条件，直接降级"],
  ["2026-06-22|600114", "触发失效条件，直接降级"],
]);

const predictions = parseCsv(fs.readFileSync(csvPath, "utf8")).filter(
  (r) => isRule(r) && r.result !== "待复盘" && normDate(r.target_date) >= "2026-06-15",
);

const rejected = [];
const accepted = [];
for (const row of predictions) {
  const key = `${normDate(row.target_date)}|${row.ticker}`;
  const reason = rejectedByNewRules.get(key);
  if (reason) rejected.push({ ...row, reason });
  else accepted.push(row);
}

console.log(JSON.stringify({
  sample: "2026-06-15 至 2026-06-22 已复盘规则票",
  old_rule: score(predictions),
  new_rule_executable_subset: score(accepted),
  filter_effect: {
    rejected_total: rejected.length,
    avoided_misses: rejected.filter((r) => r.result === "未命中").length,
    downgraded_partials: rejected.filter((r) => r.result === "部分命中").length,
    rejected_hits: rejected.filter((r) => r.result === "命中").length,
  },
  rejected: rejected.map((r) => ({
    target_date: normDate(r.target_date),
    ticker: r.ticker,
    name: r.name,
    type: r.prediction_type,
    result: r.result,
    reason: r.reason,
  })),
}, null, 2));
