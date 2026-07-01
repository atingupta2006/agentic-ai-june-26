#!/usr/bin/env bash
# Setup for macOS / Linux. Run from the project root: bash scripts/setup.sh
set -euo pipefail

echo "==> Creating virtual environment (.venv)..."
python3 -m venv .venv

echo "==> Activating .venv..."
# shellcheck disable=SC1091
source .venv/bin/activate

echo "==> Upgrading pip..."
python -m pip install --upgrade pip

echo "==> Installing requirements..."
pip install -r requirements.txt

# Secrets live in ~/dev.env. No project-local secrets file is created.
if [ ! -f "$HOME/dev.env" ]; then
  echo "==> Creating $HOME/dev.env from template (edit it to add your keys)..."
  cp dev.env.example "$HOME/dev.env"
else
  echo "==> Using existing secrets file: $HOME/dev.env"
fi

echo "==> Building the knowledge base index..."
python scripts/build_kb.py

echo ""
echo "Setup complete. Start the API with:  python main.py"
