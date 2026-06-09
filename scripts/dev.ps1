# Start the QuantML frontend (3000) and backend (8000) together.
# Usage:  ./scripts/dev.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent

Write-Host "Starting QuantML backend (FastAPI :8000)..." -ForegroundColor Magenta
$backend = Start-Process -PassThru -WorkingDirectory "$root\backend" -FilePath "powershell" `
  -ArgumentList "-NoProfile", "-Command", "if (Test-Path .venv\Scripts\Activate.ps1) { . .venv\Scripts\Activate.ps1 }; uvicorn main:app --reload --port 8000"

Write-Host "Starting QuantML frontend (Next.js :3000)..." -ForegroundColor Cyan
$frontend = Start-Process -PassThru -WorkingDirectory "$root\frontend" -FilePath "npm" -ArgumentList "run", "dev"

Write-Host "`nQuantML running:" -ForegroundColor Green
Write-Host "  web : http://localhost:3000"
Write-Host "  api : http://localhost:8000/docs"
Write-Host "`nPress Ctrl+C to stop both." -ForegroundColor Yellow

try { Wait-Process -Id $frontend.Id }
finally {
  Stop-Process -Id $backend.Id -Force -ErrorAction SilentlyContinue
  Stop-Process -Id $frontend.Id -Force -ErrorAction SilentlyContinue
}
