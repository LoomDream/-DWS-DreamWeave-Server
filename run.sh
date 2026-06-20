#!/usr/bin/env sh
set -eu

cd "$(dirname "$0")"

VENV_PY=".venv/bin/python"
PYTHON_CMD=""
HOST="127.0.0.1"
PORT="7777"
export TMPDIR="$PWD/.tmp"
export PIP_CACHE_DIR="$PWD/.pip-cache"
mkdir -p "$TMPDIR"

export DREAMWEAVE_SERVER_SECRET="${DREAMWEAVE_SERVER_SECRET:-change-me-dreamweave-server-secret}"
export DREAMWEAVE_DEVELOPER_SECRET="${DREAMWEAVE_DEVELOPER_SECRET:-change-me-dreamweave-developer-secret}"
export DREAMWEAVE_ADMIN_TOKEN="${DREAMWEAVE_ADMIN_TOKEN:-change-me-dreamweave-admin-token}"

if command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_CMD="python"
else
    echo "Python 3.11+ is required but was not found in PATH." >&2
    exit 1
fi

if [ "${SKIP_INSTALL:-}" = "1" ]; then
    echo "SKIP_INSTALL=1, using system Python."
    VENV_PY="$PYTHON_CMD"
fi

if [ "${SKIP_INSTALL:-}" != "1" ] && [ ! -x "$VENV_PY" ]; then
    echo "Creating virtual environment..."
    "$PYTHON_CMD" -m venv .venv
fi

if [ "${SKIP_INSTALL:-}" != "1" ] && [ ! -x "$VENV_PY" ]; then
    echo "Failed to create virtual environment." >&2
    exit 1
fi

if [ "${SKIP_INSTALL:-}" != "1" ]; then
echo "Installing dependencies..."
if ! "$VENV_PY" -m pip --version >/dev/null 2>&1; then
    echo "Bootstrapping pip..."
    "$VENV_PY" -m ensurepip --upgrade || true
fi

if ! "$VENV_PY" -m pip --version >/dev/null 2>&1; then
    echo "pip is unavailable after bootstrap. Recreating virtual environment..."
    rm -rf .venv
    "$PYTHON_CMD" -m venv .venv
fi

if ! "$VENV_PY" -m pip --version >/dev/null 2>&1; then
    echo "pip is still unavailable in the virtual environment." >&2
    echo "Free disk space or run with SKIP_INSTALL=1 if dependencies are already installed globally." >&2
    exit 1
fi

"$VENV_PY" -m pip install --upgrade pip
"$VENV_PY" -m pip install -r requirements.txt
fi

echo
echo "Starting Dreamweave Server"
echo "API:   http://$HOST:$PORT/docs"
echo "Admin: http://$HOST:$PORT/admin"
echo "Admin token: $DREAMWEAVE_ADMIN_TOKEN"
echo

"$VENV_PY" main.py
