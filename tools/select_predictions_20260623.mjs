const candidates = [
  ["600522", "中天科技", "光通信", "稳健观察"],
  ["002837", "英维克", "液冷/算力", "核心承接"],
  ["002156", "通富微电", "半导体封测", "弹性进攻"],
  ["002436", "兴森科技", "PCB/封装基板", "弹性进攻"],
  ["600703", "三安光电", "化合物半导体", "稳健观察"],
  ["000636", "风华高科", "被动元件", "稳健观察"],
  ["600114", "东睦股份", "机器人/高端制造", "观察降级"],
  ["06613.HK", "蓝思科技H", "AI硬件/消费电子", "观察降级"],
  ["002475", "立讯精密", "AI硬件/消费电子", "稳健观察"],
  ["600105", "永鼎股份", "光通信", "稳健观察"],
  ["0981.HK", "中芯国际", "半导体", "观察降级"],
  ["688333", "铂力特", "3D打印/高端制造", "非规则高风险观察"],
  ["301269", "华大九天", "EDA/国产软件", "非规则票"],
  ["09880.HK", "优必选", "机器人", "非规则票"],
  ["002050", "三花智控", "机器人/热管理", "稳健观察"],
  ["002709", "天赐材料", "锂电材料", "轮动备选"],
  ["002549", "凯美特气", "电子气体", "轮动备选"],
  ["002555", "三七互娱", "游戏/AI应用", "轮动备选"],
];

function secidFromCode(code) {
  const raw = String(code).trim();
  const clean = raw.replace(/\.(SH|SZ|BJ)$/i, "");
  if (/^(5|6|9)\d{5}$/.test(clean)) return `1.${clean}`;
  if (/^(0|2|3)\d{5}$/.test(clean)) return `0.${clean}`;
  if (/^(4|8)\d{5}$/.test(clean)) return `0.${clean}`;
  if (/^\d{5}\.HK$/i.test(raw)) return `116.${raw.slice(0, 5)}`;
  if (/^\d{4}\.HK$/i.test(raw)) return `116.0${raw.slice(0, 4)}`;
  throw new Error(`bad code ${code}`);
}

async function getKlines(code) {
  const url = new URL("https://push2his.eastmoney.com/api/qt/stock/kline/get");
  const params = {
    secid: secidFromCode(code),
    klt: "101",
    fqt: "0",
    beg: "20260515",
    end: "20260622",
    lmt: "60",
    fields1: "f1,f2,f3,f4,f5,f6",
    fields2: "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
  };
  Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, v));
  let lastError;
  for (let i = 0; i < 4; i += 1) {
    try {
      const r = await fetch(url, { headers: { "User-Agent": "Mozilla/5.0", Referer: "https://quote.eastmoney.com/" } });
      const j = await r.json();
      return (j.data?.klines || []).map((line) => {
        const [date, open, close, high, low, volume, amount, amplitude, changePct, change, turnover] = line.split(",");
        return { date, open: +open, close: +close, high: +high, low: +low, volume: +volume, amount: +amount, amplitude: +amplitude, changePct: +changePct, change: +change, turnover: +turnover };
      });
    } catch (error) {
      lastError = error;
      await new Promise((resolve) => setTimeout(resolve, 600 + i * 400));
    }
  }
  throw lastError;
}

function avg(values) {
  return values.length ? values.reduce((a, b) => a + b, 0) / values.length : 0;
}

function round(v, n = 2) {
  return Number.isFinite(v) ? Math.round(v * 10 ** n) / 10 ** n : null;
}

function analyze(meta, rows) {
  const [code, name, theme, defaultType] = meta;
  const r = rows.at(-1);
  const prev = rows.at(-2);
  const closes = rows.map((x) => x.close);
  const vols = rows.map((x) => x.volume);
  const ma5 = avg(closes.slice(-5));
  const ma10 = avg(closes.slice(-10));
  const ma20 = avg(closes.slice(-20));
  const vol5 = avg(vols.slice(-5));
  const vol20 = avg(vols.slice(-20));
  const closePos = (r.close - r.low) / Math.max(r.high - r.low, 0.01);
  const gap = prev ? (r.open - prev.close) / prev.close : 0;
  const highOpenWeak = gap >= 0.03 && r.close < r.open;
  const longUpper = (r.high - r.close) / Math.max(r.high - r.low, 0.01) >= 0.45;
  const trend = r.close > ma5 && ma5 >= ma10 && ma10 >= ma20;
  const above10 = r.close >= ma10;
  const volumeOk = vol20 ? vol5 / vol20 >= 1.05 : false;
  let score = 0;
  if (trend) score += 3;
  else if (r.close > ma5 && r.close > ma10) score += 2;
  else if (above10) score += 1;
  if (r.changePct > 0 && r.changePct < 7) score += 2;
  if (r.changePct >= 7) score += 0.5;
  if (closePos >= 0.55) score += 1.5;
  if (volumeOk) score += 1;
  if (highOpenWeak) score -= 3;
  if (longUpper && closePos < 0.55) score -= 2;
  if (defaultType.includes("降级")) score -= 2;
  if (defaultType.startsWith("非规则")) score -= 1.5;

  return {
    code,
    name,
    theme,
    defaultType,
    date: r.date,
    close: round(r.close),
    pct: round(r.changePct),
    high: round(r.high),
    low: round(r.low),
    ma5: round(ma5),
    ma10: round(ma10),
    ma20: round(ma20),
    closePos: round(closePos, 2),
    gap: round(gap * 100, 2),
    volRatio: round(vol5 / vol20, 2),
    trend,
    highOpenWeak,
    longUpper,
    score: round(score, 2),
  };
}

const out = [];
for (const c of candidates) {
  try {
    const rows = await getKlines(c[0]);
    out.push(analyze(c, rows));
    await new Promise((resolve) => setTimeout(resolve, 250));
  } catch (error) {
    out.push({ code: c[0], name: c[1], error: error.message });
  }
}

out.sort((a, b) => (b.score ?? -99) - (a.score ?? -99));
console.log(JSON.stringify(out, null, 2));
