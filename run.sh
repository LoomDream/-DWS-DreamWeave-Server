#!/usr/bin/env sh
set -eu

cd "$(dirname "$0")"

if [ ! -x ".venv/bin/python" ]; then
    echo "Creating virtual environment..."
    if command -v python3 >/dev/null 2>&1; then
        python3 -m venv .venv
    else
        python -m venv .venv
    fi
fi

echo "Installing dependencies..."
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt

echo "Starting Dreamweave Server..."
.venv/bin/python main.py
