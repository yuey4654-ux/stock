#!/usr/bin/env node

const DEFAULT_BASE_URL = process.env.AKTOOLS_BASE_URL || "http://127.0.0.1:8080";
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

function toUrl(pathname, params = {}) {
  const base = DEFAULT_BASE_URL.replace(/\/+$/, "");
  const path = pathname.startsWith("/") ? pathname : `/${pathname}`;
  const url = new URL(`${base}${path}`);
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === "") continue;
    url.searchParams.set(key, String(value));
  }
  return url.toString();
}

async function getJson(pathname, params) {
  const url = toUrl(pathname, params);
  const response = await fetch(url, {
    headers: {
      "User-Agent": "codex-aktools-mcp",
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(`AKTools request failed: HTTP ${response.status} for ${url}`);
  }

  return response.json();
}

async function getText(pathname) {
  const url = toUrl(pathname);
  const response = await fetch(url, {
    headers: {
      "User-Agent": "codex-aktools-mcp",
    },
  });

  if (!response.ok) {
    throw new Error(`AKTools request failed: HTTP ${response.status} for ${url}`);
  }

  return response.text();
}

async function healthCheck() {
  const schema = await getJson("/openapi.json");
  return {
    source: "AKTools OpenAPI",
    base_url: DEFAULT_BASE_URL,
    title: schema.info?.title ?? null,
    version: schema.info?.version ?? null,
    path_count: schema.paths ? Object.keys(schema.paths).length : 0,
    healthy: true,
  };
}

async function getOpenApi() {
  const schema = await getJson("/openapi.json");
  return {
    source: "AKTools OpenAPI",
    base_url: DEFAULT_BASE_URL,
    schema,
  };
}

async function callPublicEndpoint(args) {
  const endpoint = String(args.endpoint || "").trim().replace(/^\/+/, "");
  if (!endpoint) {
    throw new Error("Missing endpoint. Example: stock_zh_a_hist");
  }

  const data = await getJson(`/api/public/${endpoint}`, args.params || {});
  return {
    source: "AKTools public endpoint",
    base_url: DEFAULT_BASE_URL,
    endpoint,
    params: args.params || {},
    data,
  };
}

async function getStockZhAHist(args) {
  const data = await getJson("/api/public/stock_zh_a_hist", {
    symbol: args.symbol,
    period: args.period || "daily",
    start_date: args.start_date,
    end_date: args.end_date,
    adjust: args.adjust || "",
  });

  return {
    source: "AKTools stock_zh_a_hist",
    base_url: DEFAULT_BASE_URL,
    symbol: args.symbol,
    period: args.period || "daily",
    start_date: args.start_date ?? null,
    end_date: args.end_date ?? null,
    adjust: args.adjust || "",
    rows: data,
  };
}

async function getStockCommentEm(args) {
  const data = await getJson("/api/public/stock_comment_em", {
    symbol: args.symbol,
  });

  return {
    source: "AKTools stock_comment_em",
    base_url: DEFAULT_BASE_URL,
    symbol: args.symbol ?? null,
    rows: data,
  };
}

async function getDocsHtml() {
  const html = await getText("/docs");
  return {
    source: "AKTools Swagger UI",
    base_url: DEFAULT_BASE_URL,
    note: "Open this URL in a browser for interactive endpoint discovery.",
    docs_url: `${DEFAULT_BASE_URL.replace(/\/+$/, "")}/docs`,
    html_preview: html.slice(0, 500),
  };
}

const tools = [
  {
    name: "aktools_health",
    description: "Check whether the local AKTools HTTP service is up and return OpenAPI metadata.",
    inputSchema: {
      type: "object",
      properties: {},
    },
  },
  {
    name: "aktools_openapi",
    description: "Fetch the AKTools OpenAPI schema to inspect available public endpoints.",
    inputSchema: {
      type: "object",
      properties: {},
    },
  },
  {
    name: "aktools_public_endpoint",
    description: "Call any AKTools public endpoint by function name, for example stock_zh_a_hist or stock_hk_spot_em.",
    inputSchema: {
      type: "object",
      properties: {
        endpoint: { type: "string", description: "AKTools endpoint name after /api/public/, for example stock_zh_a_hist." },
        params: {
          type: "object",
          description: "Query parameters passed through to AKTools.",
          additionalProperties: { type: ["string", "number", "boolean"] },
        },
      },
      required: ["endpoint"],
    },
  },
  {
    name: "aktools_stock_zh_a_hist",
    description: "Get A-share historical kline data through AKTools stock_zh_a_hist.",
    inputSchema: {
      type: "object",
      properties: {
        symbol: { type: "string", description: "A-share symbol, for example 600000 or 000001." },
        period: { type: "string", enum: ["daily", "weekly", "monthly"] },
        start_date: { type: "string", description: "YYYYMMDD" },
        end_date: { type: "string", description: "YYYYMMDD" },
        adjust: { type: "string", description: "Usually empty, qfq, or hfq depending on AKShare support." },
      },
      required: ["symbol"],
    },
  },
  {
    name: "aktools_stock_comment_em",
    description: "Get Eastmoney-style A-share commentary data via AKTools stock_comment_em.",
    inputSchema: {
      type: "object",
      properties: {
        symbol: { type: "string", description: "Optional A-share symbol if supported by the installed AKTools version." },
      },
    },
  },
  {
    name: "aktools_docs",
    description: "Return the AKTools Swagger docs URL and a short HTML preview for endpoint discovery.",
    inputSchema: {
      type: "object",
      properties: {},
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
        serverInfo: { name: "aktools-mcp", version: "0.1.0" },
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
        name === "aktools_health" ? await healthCheck() :
        name === "aktools_openapi" ? await getOpenApi() :
        name === "aktools_public_endpoint" ? await callPublicEndpoint(args) :
        name === "aktools_stock_zh_a_hist" ? await getStockZhAHist(args) :
        name === "aktools_stock_comment_em" ? await getStockCommentEm(args) :
        name === "aktools_docs" ? await getDocsHtml() :
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
