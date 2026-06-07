$ErrorActionPreference = "Stop"

$configPath = "C:\Users\Administrator\.codex\config.toml"
$projectName = -join ([char[]](32929, 31080, 20998, 26512))
$serverPath = "C:\Users\Administrator\Documents\$projectName\mcp\eastmoney\server.mjs"
$nodePath = "C:\Users\Administrator\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe"

if (-not (Test-Path -LiteralPath $configPath)) {
  throw "Codex config not found: $configPath"
}

if (-not (Test-Path -LiteralPath $serverPath)) {
  throw "Eastmoney MCP server not found: $serverPath"
}

if (-not (Test-Path -LiteralPath $nodePath)) {
  throw "Bundled Node.js runtime not found: $nodePath"
}

$config = Get-Content -Raw -LiteralPath $configPath -Encoding UTF8

$block = @"

[mcp_servers.eastmoneyMcp]
command = '$nodePath'
args = ['$serverPath']
startup_timeout_sec = 30
"@

if ($config -match "\[mcp_servers\.eastmoneyMcp\]") {
  $updated = $config -replace "(?s)\[mcp_servers\.eastmoneyMcp\].*?(?=\r?\n\[|$)", $block.Trim()
  Set-Content -LiteralPath $configPath -Encoding UTF8 -Value $updated
  Write-Host "eastmoneyMcp already existed; config path refreshed."
  exit 0
}

Copy-Item -LiteralPath $configPath -Destination "$configPath.eastmoney.bak" -Force

Add-Content -LiteralPath $configPath -Encoding UTF8 -Value $block

Write-Host "eastmoneyMcp added. Restart Codex to load the new MCP server."
