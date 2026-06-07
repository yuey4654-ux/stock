# Eastmoney MCP

This is a lightweight project-local MCP server for structured China market data.
It uses Eastmoney public web APIs for quotes, klines, money flow, valuation
snapshots, technical indicators, and simple A-share screening.

## Tools

- `eastmoney_realtime_quote`: realtime quote for A-shares, ETFs, indices, and HK stocks.
- `eastmoney_a_share_spot`: ranked A-share market list.
- `eastmoney_daily_kline`: daily, weekly, or monthly kline data.
- `eastmoney_money_flow`: recent money-flow data for one stock.
- `eastmoney_valuation_snapshot`: PE, PB, market cap, turnover, and amount.
- `eastmoney_technical_summary`: MA, RSI, MACD, Bollinger, volume ratio, support/resistance.
- `eastmoney_a_share_screener`: simple A-share screening by amount, change, turnover, PE, PB.

## Codex Config

The install script appends this server to `C:\Users\Administrator\.codex\config.toml`.
It resolves `server.mjs` from the script directory, so it is safe for the
project's Chinese path.

```toml
[mcp_servers.eastmoneyMcp]
command = 'C:\Users\Administrator\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe'
args = ['<resolved project path>\mcp\eastmoney\server.mjs']
startup_timeout_sec = 30
```

After updating the config, restart the current Codex thread/app session so the
new MCP tool list is loaded.

## Notes

Eastmoney public web APIs are not official commercial APIs. They are useful for
personal research, but fields and access behavior may change. For full financial
statements and compliance-sensitive data, prefer the already configured
`tushareMcp`.
