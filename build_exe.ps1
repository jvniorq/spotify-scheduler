
$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

if (-not (Test-Path ".venv")) {
    py -3.12 -m venv .venv
}

& ".\.venv\Scripts\Activate.ps1"
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"

pyinstaller `
  --noconfirm `
  --clean `
  --windowed `
  --name "Spoxu" `
  --collect-all keyring `
  --collect-all pystray `
  --collect-all spotipy `
  --paths "src" `
  "src\spotify_scheduler_pro\__main__.py"

Write-Host ""
Write-Host "EXE generado en: dist\Spoxu\Spoxu.exe"
