#!/usr/bin/env node

const EASTMONEY_HOST = "https://push2.eastmoney.com";
const EASTMONEY_KLINE_HOST = "https://push2his.eastmoney.com";

const textDecoder = new TextDecoder();
let inputBuffer = "";

function success(id, result) {
  writeMessage({ jsonrpc: "2.0", id, result });
}

function failure(id, code, message, data) {
  writeMessage({ jsonrpc: "2.0", id, error: { code, message, data } });
}

function writeMessage(message) {
  const payload = JSON.stringify(message);
  process.stdout.write(`Content-Length: ${Buffer.byteLength(payload, "utf8")}\r\n\r\n${payload}`);
}

function parseMessages() {
  const messages = [];

  while (true) {
    const headerEnd = inputBuffer.indexOf("\r\n\r\n");
    if (headerEnd === -1) break;

    const header = inputBuffer.slice(0, headerEnd);
    const lengthMatch = header.match(/Content-Length:\s*(\d+)/i);
    if (!lengthMatch) {
      inputBuffer = inputBuffer.slice(headerEnd + 4);
      continue;
    }

    const contentLength = Number(lengthMatch[1]);
    const bodyStart = headerEnd + 4;
    const bodyEnd = bodyStart + contentLength;
    if (Buffer.byteLength(inputBuffer.slice(bodyStart), "utf8") < contentLength) break;

    const body = inputBuffer.slice(bodyStart, bodyEnd);
    inputBuffer = inputBuffer.slice(bodyEnd);
    messages.push(JSON.parse(body));
  }

  return messages;
}

function normalizeCode(code) {
  return String(code || "").trim().replace(/\.(SH|SZ|BJ)$/i, "");
}

function secidFromCode(code) {
  const raw = String(code || "").trim();
  const clean = normalizeCode(raw);
  if (/^(5|6|9)\d{5}$/.test(clean)) return `1.${clean}`;
  if (/^(0|2|3)\d{5}$/.test(clean)) return `0.${clean}`;
  if (/^(4|8)\d{5}$/.test(clean)) return `0.${clean}`;
  if (/^HK\.\d{5}$/i.test(raw)) return `116.${raw.slice(3)}`;
  if (/^\d{5}$/.test(clean)) return `116.${clean}`;
  throw new Error(`Unrecognized security code: ${code}`);
}

async function eastmoneyJson(url, params) {
  const query = new URLSearchParams(params);
  const response = await fetch(`${url}?${query}`, {
    headers: {
      "User-Agent": "Mozilla/5.0",
      Referer: "https://quote.eastmoney.com/",
    },
  });

  if (!response.ok) {
    throw new Error(`Eastmoney request failed: HTTP ${response.status}`);
  }

  const json = await response.json();
  if (json?.rc && json.rc !== 0) {
    throw new Error(`Eastmoney returned error: rc=${json.rc}`);
  }
  return json;
}

function cleanValue(value) {
  if (value === "-" || value === null || value === undefined) return null;
  return value;
}

function scale(value, divisor) {
  const cleaned = cleanValue(value);
  return typeof cleaned === "number" ? cleaned / divisor : cleaned;
}

function percent(value) {
  const cleaned = cleanValue(value);
  return typeof cleaned === "number" ? cleaned / 100 : cleaned;
}

function round(value, digits = 4) {
  if (!Number.isFinite(value)) return null;
  const factor = 10 ** digits;
  return Math.round(value * factor) / factor;
}

async function getRealtimeQuote(args) {
  const secid = secidFromCode(args.code);
  const json = await eastmoneyJson(`${EASTMONEY_HOST}/api/qt/stock/get`, {
    secid,
    fields: "f57,f58,f43,f44,f45,f46,f47,f48,f49,f60,f86,f169,f170,f116,f117,f162,f167,f168,f127,f128,f140,f141,f138,f139,f173",
  });

  const d = json.data || {};
  return {
    source: "Eastmoney public quote API",
    code: d.f57,
    name: d.f58,
    price: scale(d.f43, 100),
    change: scale(d.f169, 100),
    change_pct: percent(d.f170),
    open: scale(d.f46, 100),
    high: scale(d.f44, 100),
    low: scale(d.f45, 100),
    previous_close: scale(d.f60, 100),
    volume_shares: cleanValue(d.f47),
    amount_yuan: cleanValue(d.f48),
    turnover_rate: percent(d.f168),
    pe_ttm: scale(d.f162, 100),
    pb: scale(d.f167, 100),
    total_market_cap_yuan: cleanValue(d.f116),
    circulating_market_cap_yuan: cleanValue(d.f117),
    timestamp: d.f86,
  };
}

async function getAShareSpot(args) {
  const pageSize = Math.min(Math.max(Number(args.limit || 50), 1), 500);
  const page = Math.max(Number(args.page || 1), 1);
  const json = await eastmoneyJson(`${EASTMONEY_HOST}/api/qt/clist/get`, {
    pn: String(page),
    pz: String(pageSize),
    po: args.sort_order === "asc" ? "0" : "1",
    np: "1",
    ut: "bd1d9ddb04089700cf9c27f6f7426281",
    fltt: "2",
    invt: "2",
    fid: args.sort_field || "f3",
    fs: "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23",
    fields: "f12,f14,f2,f3,f4,f5,f6,f7,f8,f9,f10,f15,f16,f17,f18,f20,f21,f23",
  });

  return {
    source: "Eastmoney public A-share list API",
    page,
    limit: pageSize,
    total: json.data?.total ?? null,
    rows: (json.data?.diff || []).map(mapSpotRow),
  };
}

function mapSpotRow(d) {
  return {
    code: d.f12,
    name: d.f14,
    price: cleanValue(d.f2),
    change_pct: percent(d.f3),
    change: cleanValue(d.f4),
    volume_lot: cleanValue(d.f5),
    amount_yuan: cleanValue(d.f6),
    amplitude: percent(d.f7),
    turnover_rate: percent(d.f8),
    pe_dynamic: cleanValue(d.f9),
    volume_ratio: cleanValue(d.f10),
    high: cleanValue(d.f15),
    low: cleanValue(d.f16),
    open: cleanValue(d.f17),
    previous_close: cleanValue(d.f18),
    total_market_cap_yuan: cleanValue(d.f20),
    circulating_market_cap_yuan: cleanValue(d.f21),
    pb: cleanValue(d.f23),
  };
}

async function getDailyKline(args) {
  const secid = secidFromCode(args.code);
  const limit = Math.min(Math.max(Number(args.limit || 120), 1), 1000);
  const json = await eastmoneyJson(`${EASTMONEY_KLINE_HOST}/api/qt/stock/kline/get`, {
    secid,
    klt: args.period === "weekly" ? "102" : args.period === "monthly" ? "103" : "101",
    fqt: args.adjust === "qfq" ? "1" : args.adjust === "hfq" ? "2" : "0",
    beg: "19900101",
    end: "20500101",
    lmt: String(limit),
    fields1: "f1,f2,f3,f4,f5,f6",
    fields2: "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
  });

  return {
    source: "Eastmoney public historical kline API",
    code: json.data?.code,
    name: json.data?.name,
    period: args.period || "daily",
    adjust: args.adjust || "none",
    rows: (json.data?.klines || []).map(parseKline),
  };
}

function parseKline(line) {
  const [date, open, close, high, low, volume, amount, amplitude, changePct, change, turnover] = line.split(",");
  return {
    date,
    open: Number(open),
    close: Number(close),
    high: Number(high),
    low: Number(low),
    volume_lot: Number(volume),
    amount_yuan: Number(amount),
    amplitude: Number(amplitude) / 100,
    change_pct: Number(changePct) / 100,
    change: Number(change),
    turnover_rate: Number(turnover) / 100,
  };
}

async function getMoneyFlow(args) {
  const secid = secidFromCode(args.code);
  const json = await eastmoneyJson(`${EASTMONEY_HOST}/api/qt/stock/fflow/daykline/get`, {
    secid,
    lmt: String(Math.min(Math.max(Number(args.limit || 20), 1), 200)),
    klt: "101",
    fields1: "f1,f2,f3,f7",
    fields2: "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63",
  });

  return {
    source: "Eastmoney public money flow API",
    code: json.data?.code,
    name: json.data?.name,
    rows: (json.data?.klines || []).map((line) => {
      const [date, mainNet, smallNet, mediumNet, largeNet, superLargeNet, mainNetPct, smallNetPct, mediumNetPct, largeNetPct, superLargeNetPct, close, changePct] = line.split(",");
      return {
        date,
        main_net_inflow_yuan: Number(mainNet),
        small_net_inflow_yuan: Number(smallNet),
        medium_net_inflow_yuan: Number(mediumNet),
        large_net_inflow_yuan: Number(largeNet),
        super_large_net_inflow_yuan: Number(superLargeNet),
        main_net_inflow_pct: Number(mainNetPct) / 100,
        small_net_inflow_pct: Number(smallNetPct) / 100,
        medium_net_inflow_pct: Number(mediumNetPct) / 100,
        large_net_inflow_pct: Number(largeNetPct) / 100,
        super_large_net_inflow_pct: Number(superLargeNetPct) / 100,
        close: Number(close),
        change_pct: Number(changePct) / 100,
      };
    }),
  };
}

async function getValuationSnapshot(args) {
  const quote = await getRealtimeQuote(args);
  return {
    source: quote.source,
    code: quote.code,
    name: quote.name,
    price: quote.price,
    pe_ttm: quote.pe_ttm,
    pb: quote.pb,
    total_market_cap_yuan: quote.total_market_cap_yuan,
    circulating_market_cap_yuan: quote.circulating_market_cap_yuan,
    turnover_rate: quote.turnover_rate,
    amount_yuan: quote.amount_yuan,
    note: "For full financial statements, use the configured tushareMcp when available.",
  };
}

async function getTechnicalSummary(args) {
  const limit = Math.max(Number(args.limit || 180), 80);
  const kline = await getDailyKline({ ...args, limit, period: args.period || "daily", adjust: args.adjust || "qfq" });
  const rows = kline.rows;
  const closes = rows.map((r) => r.close);
  const highs = rows.map((r) => r.high);
  const lows = rows.map((r) => r.low);
  const volumes = rows.map((r) => r.volume_lot);
  const latest = rows.at(-1);

  const ma5 = sma(closes, 5);
  const ma10 = sma(closes, 10);
  const ma20 = sma(closes, 20);
  const ma60 = sma(closes, 60);
  const volumeMa5 = sma(volumes, 5);
  const volumeMa20 = sma(volumes, 20);
  const macdValue = macd(closes);
  const rsi14 = rsi(closes, 14);
  const bollValue = bollinger(closes, 20);
  const recentHigh20 = Math.max(...highs.slice(-20));
  const recentLow20 = Math.min(...lows.slice(-20));
  const trend =
    latest?.close > ma20 && ma20 > ma60 ? "uptrend" :
    latest?.close < ma20 && ma20 < ma60 ? "downtrend" :
    "range_or_transition";

  return {
    source: "Computed from Eastmoney kline data",
    code: kline.code,
    name: kline.name,
    as_of: latest?.date ?? null,
    latest_close: latest?.close ?? null,
    moving_average: {
      ma5: round(ma5),
      ma10: round(ma10),
      ma20: round(ma20),
      ma60: round(ma60),
    },
    momentum: {
      rsi14: round(rsi14, 2),
      macd: macdValue,
      bollinger: bollValue,
      trend,
    },
    volume: {
      latest_volume_lot: latest?.volume_lot ?? null,
      volume_ma5_lot: round(volumeMa5, 2),
      volume_ma20_lot: round(volumeMa20, 2),
      volume_vs_ma20: round(latest?.volume_lot / volumeMa20, 2),
    },
    key_levels: {
      support_20d: round(recentLow20, 3),
      resistance_20d: round(recentHigh20, 3),
      distance_to_resistance_20d: round((recentHigh20 - latest?.close) / latest?.close, 4),
      distance_to_support_20d: round((latest?.close - recentLow20) / latest?.close, 4),
    },
  };
}

function sma(values, period) {
  if (values.length < period) return null;
  const slice = values.slice(-period);
  return slice.reduce((sum, value) => sum + value, 0) / period;
}

function emaSeries(values, period) {
  if (values.length < period) return [];
  const alpha = 2 / (period + 1);
  const result = [];
  let prev = values.slice(0, period).reduce((sum, value) => sum + value, 0) / period;
  result.push(prev);
  for (const value of values.slice(period)) {
    prev = value * alpha + prev * (1 - alpha);
    result.push(prev);
  }
  return result;
}

function macd(values) {
  if (values.length < 35) return { dif: null, dea: null, histogram: null };
  const ema12 = emaSeries(values, 12);
  const ema26 = emaSeries(values, 26);
  const alignedEma12 = ema12.slice(ema12.length - ema26.length);
  const difSeries = ema26.map((value, index) => alignedEma12[index] - value);
  const deaSeries = emaSeries(difSeries, 9);
  const dif = difSeries.at(-1);
  const dea = deaSeries.at(-1);
  return {
    dif: round(dif, 4),
    dea: round(dea, 4),
    histogram: round((dif - dea) * 2, 4),
  };
}

function rsi(values, period) {
  if (values.length <= period) return null;
  let gains = 0;
  let losses = 0;
  const slice = values.slice(-(period + 1));
  for (let i = 1; i < slice.length; i += 1) {
    const diff = slice[i] - slice[i - 1];
    if (diff >= 0) gains += diff;
    else losses -= diff;
  }
  if (losses === 0) return 100;
  const rs = gains / losses;
  return 100 - 100 / (1 + rs);
}

function bollinger(values, period) {
  if (values.length < period) return { mid: null, upper: null, lower: null };
  const slice = values.slice(-period);
  const mid = slice.reduce((sum, value) => sum + value, 0) / period;
  const variance = slice.reduce((sum, value) => sum + (value - mid) ** 2, 0) / period;
  const sd = Math.sqrt(variance);
  return {
    mid: round(mid, 4),
    upper: round(mid + 2 * sd, 4),
    lower: round(mid - 2 * sd, 4),
  };
}

async function screenAShares(args) {
  const rawLimit = Math.min(Math.max(Number(args.scan_limit || 300), 1), 500);
  const spot = await getAShareSpot({
    limit: rawLimit,
    page: args.page || 1,
    sort_field: args.sort_field || "f6",
    sort_order: args.sort_order || "desc",
  });

  const rows = spot.rows.filter((row) => {
    if (Number.isFinite(args.min_change_pct) && !(row.change_pct >= args.min_change_pct)) return false;
    if (Number.isFinite(args.max_change_pct) && !(row.change_pct <= args.max_change_pct)) return false;
    if (Number.isFinite(args.min_amount_yuan) && !(row.amount_yuan >= args.min_amount_yuan)) return false;
    if (Number.isFinite(args.min_turnover_rate) && !(row.turnover_rate >= args.min_turnover_rate)) return false;
    if (Number.isFinite(args.max_pe_dynamic) && !(row.pe_dynamic <= args.max_pe_dynamic)) return false;
    if (Number.isFinite(args.max_pb) && !(row.pb <= args.max_pb)) return false;
    return true;
  }).slice(0, Math.min(Math.max(Number(args.limit || 50), 1), 200));

  return {
    source: spot.source,
    scan_limit: rawLimit,
    matched: rows.length,
    rows,
  };
}

const tools = [
  {
    name: "eastmoney_realtime_quote",
    description: "Get structured realtime quote for an A-share, ETF, index, or HK stock from Eastmoney public quote API.",
    inputSchema: {
      type: "object",
      properties: {
        code: { type: "string", description: "Security code, such as 600519, 002050, 159740, 01810, HK.01810." },
      },
      required: ["code"],
    },
  },
  {
    name: "eastmoney_a_share_spot",
    description: "Get A-share realtime market list with ranking fields such as change, turnover, amount, PE, PB, and market cap.",
    inputSchema: {
      type: "object",
      properties: {
        limit: { type: "number", description: "Rows to return, 1-500. Default 50." },
        page: { type: "number", description: "Page number. Default 1." },
        sort_field: { type: "string", description: "Eastmoney field, e.g. f3 change pct, f6 amount, f20 total market cap." },
        sort_order: { type: "string", enum: ["asc", "desc"], description: "Sort order. Default desc." },
      },
    },
  },
  {
    name: "eastmoney_daily_kline",
    description: "Get daily, weekly, or monthly kline data with optional forward/backward adjustment.",
    inputSchema: {
      type: "object",
      properties: {
        code: { type: "string", description: "Security code." },
        limit: { type: "number", description: "Number of bars, default 120, max 1000." },
        period: { type: "string", enum: ["daily", "weekly", "monthly"], description: "Kline period. Default daily." },
        adjust: { type: "string", enum: ["none", "qfq", "hfq"], description: "Adjustment. Default none." },
      },
      required: ["code"],
    },
  },
  {
    name: "eastmoney_money_flow",
    description: "Get recent daily money flow for one stock, including main, large, and super-large net inflow.",
    inputSchema: {
      type: "object",
      properties: {
        code: { type: "string", description: "Security code." },
        limit: { type: "number", description: "Days to return, default 20, max 200." },
      },
      required: ["code"],
    },
  },
  {
    name: "eastmoney_valuation_snapshot",
    description: "Get valuation snapshot: PE TTM, PB, market cap, turnover, and trading amount.",
    inputSchema: {
      type: "object",
      properties: {
        code: { type: "string", description: "Security code." },
      },
      required: ["code"],
    },
  },
  {
    name: "eastmoney_technical_summary",
    description: "Compute technical indicators from kline data: MA, RSI, MACD, Bollinger, volume ratio, 20-day support/resistance.",
    inputSchema: {
      type: "object",
      properties: {
        code: { type: "string", description: "Security code." },
        limit: { type: "number", description: "Bars used for computation. Default 180." },
        period: { type: "string", enum: ["daily", "weekly", "monthly"], description: "Kline period. Default daily." },
        adjust: { type: "string", enum: ["none", "qfq", "hfq"], description: "Adjustment. Default qfq." },
      },
      required: ["code"],
    },
  },
  {
    name: "eastmoney_a_share_screener",
    description: "Screen A-shares by turnover amount, change pct, turnover rate, PE, PB, then return structured rows.",
    inputSchema: {
      type: "object",
      properties: {
        scan_limit: { type: "number", description: "Rows to scan from ranked market list, max 500. Default 300." },
        limit: { type: "number", description: "Rows to return, max 200. Default 50." },
        page: { type: "number", description: "Source page number. Default 1." },
        sort_field: { type: "string", description: "Eastmoney rank field. Default f6 amount." },
        sort_order: { type: "string", enum: ["asc", "desc"], description: "Sort order. Default desc." },
        min_change_pct: { type: "number", description: "Minimum change pct as decimal, e.g. 0.03 for +3%." },
        max_change_pct: { type: "number", description: "Maximum change pct as decimal, e.g. -0.02 for -2%." },
        min_amount_yuan: { type: "number", description: "Minimum trading amount in yuan." },
        min_turnover_rate: { type: "number", description: "Minimum turnover rate as decimal." },
        max_pe_dynamic: { type: "number", description: "Maximum dynamic PE." },
        max_pb: { type: "number", description: "Maximum PB." },
      },
    },
  },
];

async function handleRequest(message) {
  const { id, method, params } = message;

  try {
    if (method === "initialize") {
      success(id, {
        protocolVersion: "2024-11-05",
        capabilities: { tools: {} },
        serverInfo: { name: "eastmoney-mcp", version: "0.2.0" },
      });
      return;
    }

    if (method === "notifications/initialized") return;

    if (method === "tools/list") {
      success(id, { tools });
      return;
    }

    if (method === "tools/call") {
      const args = params?.arguments || {};
      const name = params?.name;
      const result =
        name === "eastmoney_realtime_quote" ? await getRealtimeQuote(args) :
        name === "eastmoney_a_share_spot" ? await getAShareSpot(args) :
        name === "eastmoney_daily_kline" ? await getDailyKline(args) :
        name === "eastmoney_money_flow" ? await getMoneyFlow(args) :
        name === "eastmoney_valuation_snapshot" ? await getValuationSnapshot(args) :
        name === "eastmoney_technical_summary" ? await getTechnicalSummary(args) :
        name === "eastmoney_a_share_screener" ? await screenAShares(args) :
        null;

      if (!result) throw new Error(`Unknown tool: ${name}`);
      success(id, {
        content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
        structuredContent: result,
      });
      return;
    }

    failure(id, -32601, `Method not found: ${method}`);
  } catch (error) {
    failure(id, -32000, error.message, { stack: error.stack });
  }
}

process.stdin.on("data", async (chunk) => {
  inputBuffer += textDecoder.decode(chunk, { stream: true });
  for (const message of parseMessages()) {
    await handleRequest(message);
  }
});

process.stdin.resume();
