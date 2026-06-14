#!/usr/bin/env node

const TUSHARE_HOST = "http://api.tushare.pro";
const textDecoder = new TextDecoder();
let inputBuffer = "";

function writeMessage(message) {
  const payload = JSON.stringify(message);
  process.stdout.write(`Content-Length: ${Buffer.byteLength(payload, "utf8")}\r\n\r\n${payload}`);
}

function success(id, result) {
  writeMessage({ jsonrpc: "2.0", id, result });
}

function failure(id, code, message, data) {
  writeMessage({ jsonrpc: "2.0", id, error: { code, message, data } });
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

function requireToken() {
  const token = process.env.TUSHARE_TOKEN?.trim();
  if (!token) {
    throw new Error("Missing TUSHARE_TOKEN. Add it to the tushareMcp env block in C:\\Users\\Administrator\\.codex\\config.toml.");
  }
  return token;
}

function normalizeTsCode(code) {
  const raw = String(code || "").trim().toUpperCase();
  if (/^\d{6}\.(SH|SZ|BJ)$/.test(raw)) return raw;
  if (/^(5|6|9)\d{5}$/.test(raw)) return `${raw}.SH`;
  if (/^(0|2|3)\d{5}$/.test(raw)) return `${raw}.SZ`;
  if (/^(4|8)\d{5}$/.test(raw)) return `${raw}.BJ`;
  throw new Error(`Unsupported TS code format: ${code}`);
}

async function tushareCall(api_name, params = {}, fields = "") {
  const response = await fetch(TUSHARE_HOST, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "User-Agent": "codex-tushare-mcp",
    },
    body: JSON.stringify({
      api_name,
      token: requireToken(),
      params,
      fields,
    }),
  });

  if (!response.ok) {
    throw new Error(`Tushare request failed: HTTP ${response.status}`);
  }

  const json = await response.json();
  if (json.code !== 0) {
    throw new Error(`Tushare error ${json.code}: ${json.msg || "unknown error"}`);
  }
  return json.data || { fields: [], items: [] };
}

function tableToObjects(table) {
  const fields = table.fields || [];
  const items = table.items || [];
  return items.map((row) => Object.fromEntries(fields.map((field, index) => [field, row[index]])));
}

async function getStockBasic(args) {
  const rows = tableToObjects(await tushareCall(
    "stock_basic",
    {
      ts_code: args.ts_code ? normalizeTsCode(args.ts_code) : undefined,
      name: args.name,
      market: args.market,
      list_status: args.list_status || "L",
      exchange: args.exchange,
      is_hs: args.is_hs,
    },
    "ts_code,symbol,name,area,industry,market,exchange,list_date,list_status,is_hs"
  ));

  return {
    source: "Tushare stock_basic",
    count: rows.length,
    rows,
  };
}

async function getDaily(args) {
  const rows = tableToObjects(await tushareCall(
    "daily",
    {
      ts_code: normalizeTsCode(args.ts_code),
      start_date: args.start_date,
      end_date: args.end_date,
      trade_date: args.trade_date,
    },
    "ts_code,trade_date,open,high,low,close,pre_close,change,pct_chg,vol,amount"
  ));

  return {
    source: "Tushare daily",
    count: rows.length,
    rows,
  };
}

async function getDailyBasic(args) {
  const rows = tableToObjects(await tushareCall(
    "daily_basic",
    {
      ts_code: args.ts_code ? normalizeTsCode(args.ts_code) : undefined,
      trade_date: args.trade_date,
      start_date: args.start_date,
      end_date: args.end_date,
    },
    "ts_code,trade_date,close,turnover_rate,turnover_rate_f,volume_ratio,pe,pe_ttm,pb,ps,ps_ttm,dv_ratio,dv_ttm,total_share,float_share,free_share,total_mv,circ_mv"
  ));

  return {
    source: "Tushare daily_basic",
    count: rows.length,
    rows,
  };
}

async function getIncome(args) {
  const rows = tableToObjects(await tushareCall(
    "income",
    {
      ts_code: normalizeTsCode(args.ts_code),
      period: args.period,
      start_date: args.start_date,
      end_date: args.end_date,
      report_type: args.report_type,
    },
    "ts_code,ann_date,f_ann_date,end_date,report_type,basic_eps,total_revenue,revenue,operate_profit,total_profit,n_income,n_income_attr_p"
  ));

  return {
    source: "Tushare income",
    count: rows.length,
    rows,
  };
}

async function getBalanceSheet(args) {
  const rows = tableToObjects(await tushareCall(
    "balancesheet",
    {
      ts_code: normalizeTsCode(args.ts_code),
      period: args.period,
      start_date: args.start_date,
      end_date: args.end_date,
      report_type: args.report_type,
    },
    "ts_code,ann_date,f_ann_date,end_date,total_assets,total_liab,money_cap,inventories,accounts_receiv,fixed_assets,total_hldr_eqy_exc_min_int"
  ));

  return {
    source: "Tushare balancesheet",
    count: rows.length,
    rows,
  };
}

async function getCashflow(args) {
  const rows = tableToObjects(await tushareCall(
    "cashflow",
    {
      ts_code: normalizeTsCode(args.ts_code),
      period: args.period,
      start_date: args.start_date,
      end_date: args.end_date,
      report_type: args.report_type,
    },
    "ts_code,ann_date,f_ann_date,end_date,net_profit,c_fr_sale_sg,n_cashflow_act,n_cashflow_inv_act,n_cash_flows_fnc_act,free_cashflow"
  ));

  return {
    source: "Tushare cashflow",
    count: rows.length,
    rows,
  };
}

async function getFinaIndicator(args) {
  const rows = tableToObjects(await tushareCall(
    "fina_indicator",
    {
      ts_code: normalizeTsCode(args.ts_code),
      period: args.period,
      start_date: args.start_date,
      end_date: args.end_date,
    },
    "ts_code,ann_date,end_date,eps,dt_eps,roe,roe_dt,roa,grossprofit_margin,netprofit_margin,assets_turn,inv_turn,current_ratio,quick_ratio,debt_to_assets,ocfps"
  ));

  return {
    source: "Tushare fina_indicator",
    count: rows.length,
    rows,
  };
}

async function getDisclosureDate(args) {
  const rows = tableToObjects(await tushareCall(
    "disclosure_date",
    {
      ts_code: args.ts_code ? normalizeTsCode(args.ts_code) : undefined,
      end_date: args.end_date,
      pre_date: args.pre_date,
      actual_date: args.actual_date,
    },
    "ts_code,ann_date,end_date,pre_date,actual_date,modify_date"
  ));

  return {
    source: "Tushare disclosure_date",
    count: rows.length,
    rows,
  };
}

const tools = [
  {
    name: "tushare_stock_basic",
    description: "Get A-share basic security metadata such as name, industry, market, exchange, and list date.",
    inputSchema: {
      type: "object",
      properties: {
        ts_code: { type: "string" },
        name: { type: "string" },
        market: { type: "string" },
        exchange: { type: "string" },
        list_status: { type: "string", enum: ["L", "D", "P"] },
        is_hs: { type: "string", enum: ["N", "H", "S"] }
      }
    }
  },
  {
    name: "tushare_daily",
    description: "Get A-share daily OHLCV history.",
    inputSchema: {
      type: "object",
      properties: {
        ts_code: { type: "string" },
        trade_date: { type: "string", description: "YYYYMMDD" },
        start_date: { type: "string", description: "YYYYMMDD" },
        end_date: { type: "string", description: "YYYYMMDD" }
      },
      required: ["ts_code"]
    }
  },
  {
    name: "tushare_daily_basic",
    description: "Get daily valuation and liquidity metrics such as PE, PB, PS, turnover, and market cap.",
    inputSchema: {
      type: "object",
      properties: {
        ts_code: { type: "string" },
        trade_date: { type: "string", description: "YYYYMMDD" },
        start_date: { type: "string", description: "YYYYMMDD" },
        end_date: { type: "string", description: "YYYYMMDD" }
      }
    }
  },
  {
    name: "tushare_income",
    description: "Get income statement data for a stock.",
    inputSchema: {
      type: "object",
      properties: {
        ts_code: { type: "string" },
        period: { type: "string", description: "Report period, e.g. 20250331" },
        start_date: { type: "string", description: "Announcement start date, YYYYMMDD" },
        end_date: { type: "string", description: "Announcement end date, YYYYMMDD" },
        report_type: { type: "string" }
      },
      required: ["ts_code"]
    }
  },
  {
    name: "tushare_balancesheet",
    description: "Get balance sheet data for a stock.",
    inputSchema: {
      type: "object",
      properties: {
        ts_code: { type: "string" },
        period: { type: "string", description: "Report period, e.g. 20250331" },
        start_date: { type: "string", description: "Announcement start date, YYYYMMDD" },
        end_date: { type: "string", description: "Announcement end date, YYYYMMDD" },
        report_type: { type: "string" }
      },
      required: ["ts_code"]
    }
  },
  {
    name: "tushare_cashflow",
    description: "Get cashflow statement data for a stock.",
    inputSchema: {
      type: "object",
      properties: {
        ts_code: { type: "string" },
        period: { type: "string", description: "Report period, e.g. 20250331" },
        start_date: { type: "string", description: "Announcement start date, YYYYMMDD" },
        end_date: { type: "string", description: "Announcement end date, YYYYMMDD" },
        report_type: { type: "string" }
      },
      required: ["ts_code"]
    }
  },
  {
    name: "tushare_fina_indicator",
    description: "Get financial quality indicators such as ROE, ROA, gross margin, leverage, and cash flow per share.",
    inputSchema: {
      type: "object",
      properties: {
        ts_code: { type: "string" },
        period: { type: "string", description: "Report period, e.g. 20250331" },
        start_date: { type: "string", description: "Announcement start date, YYYYMMDD" },
        end_date: { type: "string", description: "Announcement end date, YYYYMMDD" }
      },
      required: ["ts_code"]
    }
  },
  {
    name: "tushare_disclosure_date",
    description: "Get planned and actual disclosure dates for financial reports.",
    inputSchema: {
      type: "object",
      properties: {
        ts_code: { type: "string" },
        end_date: { type: "string", description: "Report period, e.g. 20250331" },
        pre_date: { type: "string", description: "Planned disclosure date, YYYYMMDD" },
        actual_date: { type: "string", description: "Actual disclosure date, YYYYMMDD" }
      }
    }
  }
];

async function handleRequest(message) {
  const { id, method, params } = message;

  try {
    if (method === "initialize") {
      success(id, {
        protocolVersion: "2024-11-05",
        capabilities: { tools: {} },
        serverInfo: { name: "tushare-mcp", version: "0.1.0" },
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
        name === "tushare_stock_basic" ? await getStockBasic(args) :
        name === "tushare_daily" ? await getDaily(args) :
        name === "tushare_daily_basic" ? await getDailyBasic(args) :
        name === "tushare_income" ? await getIncome(args) :
        name === "tushare_balancesheet" ? await getBalanceSheet(args) :
        name === "tushare_cashflow" ? await getCashflow(args) :
        name === "tushare_fina_indicator" ? await getFinaIndicator(args) :
        name === "tushare_disclosure_date" ? await getDisclosureDate(args) :
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
