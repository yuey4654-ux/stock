$port = 8080

function Resolve-Python {
  $cmd = Get-Command python -ErrorAction SilentlyContinue
  if ($cmd -and $cmd.Source -notlike "*WindowsApps*") {
    return $cmd.Source
  }

  $commonPaths = @(
    "C:\Users\Administrator\AppData\Local\Programs\Python\Python311\python.exe",
    "C:\Users\Administrator\AppData\Local\Programs\Python\Python310\python.exe"
  )

  foreach ($path in $commonPaths) {
    if (Test-Path $path) {
      return $path
    }
  }

  throw "Python is not installed or not usable from PATH. Install Python 3.10+ first."
}

$pythonExe = Resolve-Python
Write-Host "Using Python: $pythonExe"

# Avoid inheriting broken local proxies into AKShare requests.
$env:HTTP_PROXY = ""
$env:HTTPS_PROXY = ""
$env:ALL_PROXY = ""
$env:NO_PROXY = "*"

Write-Host "Checking AKTools installation..."
try {
  & $pythonExe -m aktools --help *> $null
} catch {
  throw "AKTools is not installed. Run: `"$pythonExe`" -m pip install -U aktools"
}

Write-Host "Starting AKTools on http://127.0.0.1:$port ..."
& $pythonExe -m aktools --host 127.0.0.1 --port $port
