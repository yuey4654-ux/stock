$projectPath = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$serverPath = Join-Path $projectPath "mcp\aktools\server.mjs"
$configPath = "C:\Users\Administrator\.codex\config.toml"
$nodePath = "C:\Users\Administrator\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe"
$baseUrl = "http://127.0.0.1:8080"

if (-not (Test-Path $serverPath)) {
  throw "AKTools MCP server not found: $serverPath"
}

if (-not (Test-Path $configPath)) {
  throw "Codex config not found: $configPath"
}

$block = @"
[mcp_servers.aktoolsMcp]
command = '$nodePath'
args = ['$serverPath']
startup_timeout_sec = 30

[mcp_servers.aktoolsMcp.env]
AKTOOLS_BASE_URL = '$baseUrl'
"@

$config = Get-Content -Raw $configPath

if ($config -match "\[mcp_servers\.aktoolsMcp\]") {
  $updated = $config -replace "(?s)\[mcp_servers\.aktoolsMcp\].*?(?=\r?\n\[|$)", $block.Trim()
  Write-Host "aktoolsMcp already existed; config block refreshed."
} else {
  $updated = $config.TrimEnd() + "`r`n`r`n" + $block.Trim() + "`r`n"
  Write-Host "aktoolsMcp added to config."
}

Copy-Item -LiteralPath $configPath -Destination "$configPath.aktools.bak" -Force
Set-Content -LiteralPath $configPath -Value $updated -Encoding UTF8

Write-Host "Done. Restart Codex or open a new thread so the aktoolsMcp tools are loaded."
