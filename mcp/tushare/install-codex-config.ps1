$projectPath = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$serverPath = Join-Path $projectPath "mcp\tushare\server.mjs"
$configPath = "C:\Users\Administrator\.codex\config.toml"

if (-not (Test-Path $serverPath)) {
  throw "Tushare MCP server not found: $serverPath"
}

if (-not (Test-Path $configPath)) {
  throw "Codex config not found: $configPath"
}

$token = Read-Host "Paste your Tushare token"
if ([string]::IsNullOrWhiteSpace($token)) {
  throw "Empty token. Aborted."
}

$nodePath = "C:\Users\Administrator\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe"

$block = @"
[mcp_servers.tushareMcp]
command = '$nodePath'
args = ['$serverPath']
startup_timeout_sec = 30

[mcp_servers.tushareMcp.env]
TUSHARE_TOKEN = '$token'
"@

$config = Get-Content -Raw $configPath

if ($config -match "\[mcp_servers\.tushareMcp\]") {
  $updated = $config -replace "(?s)\[mcp_servers\.tushareMcp\].*?(?=\r?\n\[|$)", $block.Trim()
  Write-Host "tushareMcp already existed; config block refreshed."
} else {
  $updated = $config.TrimEnd() + "`r`n`r`n" + $block.Trim() + "`r`n"
  Write-Host "tushareMcp added to config."
}

Copy-Item -LiteralPath $configPath -Destination "$configPath.tushare.bak" -Force
Set-Content -LiteralPath $configPath -Value $updated -Encoding UTF8

Write-Host "Done. Restart Codex or open a new thread so the tushareMcp tools are loaded."
