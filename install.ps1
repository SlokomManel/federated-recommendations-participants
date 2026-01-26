Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Ensure-Uv {
  if (Get-Command uv -ErrorAction SilentlyContinue) {
    return
  }

  Write-Host ""
  Write-Host "uv not found. Installing uv (https://docs.astral.sh/uv/)..."
  Write-Host ""

  powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

  # Best-effort: uv commonly installs to $HOME\.local\bin on Windows.
  $localBin = Join-Path $HOME ".local\bin"
  if (Test-Path $localBin) {
    $env:PATH = "$localBin;$env:PATH"
  }

  if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw "uv was installed but isn't on PATH yet. Close/reopen PowerShell, then rerun .\install.ps1"
  }
}

function Ensure-EnvFile {
  if (Test-Path ".\.env") { return }

  Write-Host ".env not found. Creating from .env.example..."
  if (-not (Test-Path ".\.env.example")) {
    throw ".env.example not found. Cannot create .env."
  }

  Copy-Item ".\.env.example" ".\.env"
  Write-Host ".env created."
}

Ensure-Uv
Ensure-EnvFile

if (-not (Test-Path ".\.venv")) {
  Write-Host "Creating virtual environment..."
  uv venv -p 3.12
}

Write-Host "Installing dependencies..."
uv pip install -e .

Write-Host ""
Write-Host "Starting FastAPI server on http://0.0.0.0:8082"
uv run python app.py

