# Setup for Windows PowerShell. Run from the project root: .\scripts\setup.ps1
$ErrorActionPreference = "Stop"

Write-Host "==> Creating virtual environment (.venv)..."
python -m venv .venv

Write-Host "==> Activating .venv..."
. .\.venv\Scripts\Activate.ps1

Write-Host "==> Upgrading pip..."
python -m pip install --upgrade pip

Write-Host "==> Installing requirements..."
pip install -r requirements.txt

# Secrets live in ~/dev.env. No project-local secrets file is created.
$homeEnv = Join-Path $HOME "dev.env"
if (-Not (Test-Path $homeEnv)) {
    Write-Host "==> Creating $homeEnv from template (edit it to add your keys)..."
    Copy-Item "dev.env.example" $homeEnv
} else {
    Write-Host "==> Using existing secrets file: $homeEnv"
}

Write-Host "==> Building the knowledge base index..."
python scripts\build_kb.py

Write-Host ""
Write-Host "Setup complete. Start the API with:  python main.py"
