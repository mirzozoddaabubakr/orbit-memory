param([switch]$NoBrowser)
$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

function Find-Python {
    $probe = "import sys; print(sys.executable) if sys.version_info >= (3, 10) else sys.exit(1)"
    if (Get-Command py.exe -ErrorAction SilentlyContinue) {
        $exe = & py.exe -3.12 -c $probe
        if ($LASTEXITCODE -eq 0 -and $exe) { return $exe }
    }
    if (Get-Command python.exe -ErrorAction SilentlyContinue) {
        $exe = & python.exe -c $probe
        if ($LASTEXITCODE -eq 0 -and $exe) { return $exe }
    }
}

function Run-Python($exe, $arguments) {
    & $exe @arguments
    if ($LASTEXITCODE -ne 0) { throw "Orbit setup stopped during: $arguments (exit $LASTEXITCODE)." }
}

$python = Find-Python
if (!$python) {
    if (!(Get-Command winget -ErrorAction SilentlyContinue)) {
        throw "Install Python 3.12 from python.org, reopen PowerShell and run this command again."
    }
    & winget install --id Python.Python.3.12 --exact --scope user --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) { throw "Python installation failed. Install Python 3.12 from python.org and retry." }
    $python = Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe"
    if (!(Test-Path -LiteralPath $python)) { throw "Reopen PowerShell to find the installed Python, then run setup again." }
}
Write-Host "Preparing Orbit with $python"
Run-Python $python @("-m", "venv", ".orbit-mcp")
$runtime = Join-Path $PSScriptRoot ".orbit-mcp\Scripts\python.exe"
Run-Python $runtime @("-m", "pip", "--disable-pip-version-check", "install", "-r", "requirements-mcp.txt")
Run-Python $python @("agent_connections.py")
Write-Host "Open http://127.0.0.1:47831 in your browser. Keep this window open while using Orbit."
$serverArgs = @("server.py")
if (!$NoBrowser) { $serverArgs += "--open" }
Run-Python $runtime $serverArgs
