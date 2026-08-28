#!/usr/bin/env bash
#
# Start PuneetBehl.com for local development.
#
#   ./dev.sh                 # http://127.0.0.1:8000, auto-reload on
#   ./dev.sh --port 9000     # a different port
#   ./dev.sh --host 0.0.0.0  # reachable from other devices on your network
#   ./dev.sh --no-reload     # disable auto-reload
#
# The script is idempotent: it creates the virtualenv, installs dependencies,
# and seeds .env only when those are actually missing or out of date.

set -euo pipefail

# Always operate on the repository root, whatever directory you invoke from.
# app/config.py reads .env relative to the working directory.
cd "$(dirname "${BASH_SOURCE[0]}")"

VENV=".venv"
STAMP="$VENV/.deps-stamp"
HOST="127.0.0.1"
PORT="${PORT:-8000}"
RELOAD=1

bold() { printf '\033[1m%s\033[0m\n' "$*"; }
info() { printf '\033[36m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[33mwarning:\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[31merror:\033[0m %s\n' "$*" >&2; exit 1; }

# ---- arguments -------------------------------------------------------------

while [ $# -gt 0 ]; do
  case "$1" in
    --port) PORT="${2:?--port needs a value}"; shift 2 ;;
    --port=*) PORT="${1#*=}"; shift ;;
    --host) HOST="${2:?--host needs a value}"; shift 2 ;;
    --host=*) HOST="${1#*=}"; shift ;;
    --no-reload) RELOAD=0; shift ;;
    # Print the header comment block, stopping at the first non-comment line,
    # so the help text cannot drift out of sync with a fixed line range.
    -h|--help)
      awk 'NR>1 && /^#/ {sub(/^# ?/, ""); print; next} NR>1 {exit}' "${BASH_SOURCE[0]}"
      exit 0 ;;
    *) die "unknown option: $1 (try --help)" ;;
  esac
done

case "$PORT" in
  ''|*[!0-9]*) die "--port must be a number, got: $PORT" ;;
esac

# ---- interpreter -----------------------------------------------------------
# pyproject.toml requires >=3.12; the macOS system python is 3.9, so look for a
# suitable interpreter explicitly rather than trusting bare `python3`.

find_python() {
  local candidate
  for candidate in python3.14 python3.13 python3.12 python3 python; do
    if command -v "$candidate" >/dev/null 2>&1 &&
       "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)' 2>/dev/null; then
      command -v "$candidate"
      return 0
    fi
  done
  return 1
}

# ---- virtualenv ------------------------------------------------------------

if [ ! -x "$VENV/bin/python" ]; then
  PYTHON="$(find_python)" || die "Python 3.12+ not found.
  Install it (macOS: brew install python@3.12, or use pyenv) and re-run.
  Found: $(python3 --version 2>&1 || echo 'no python3')"
  info "Creating virtualenv in $VENV ($("$PYTHON" --version))"
  "$PYTHON" -m venv "$VENV"
fi

# ---- dependencies ----------------------------------------------------------
# Reinstall only when pyproject.toml is newer than the last successful install,
# so the common case is a no-op.

if [ ! -f "$STAMP" ] || [ pyproject.toml -nt "$STAMP" ]; then
  info "Installing dependencies (editable, with dev extras)"
  "$VENV/bin/python" -m pip install --quiet --upgrade pip
  "$VENV/bin/python" -m pip install --quiet -e ".[dev]"
  touch "$STAMP"
fi

# ---- environment file ------------------------------------------------------

if [ ! -f .env ] && [ -f .env.example ]; then
  info "Creating .env from .env.example"
  cp .env.example .env
fi

# ---- port availability -----------------------------------------------------
# Fail here with a clear message rather than letting uvicorn abort on bind.

if command -v lsof >/dev/null 2>&1 && lsof -i ":$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  warn "Port $PORT is already in use by:"
  lsof -i ":$PORT" -sTCP:LISTEN >&2
  die "Stop that process, or pick another port: ./dev.sh --port $((PORT + 1))"
fi

# ---- launch ----------------------------------------------------------------

ARGS=(app.main:app --host "$HOST" --port "$PORT")
[ "$RELOAD" -eq 1 ] && ARGS+=(--reload)

echo
bold "  PuneetBehl.com — development server"
echo  "  http://${HOST}:${PORT}"
echo  "  health: http://${HOST}:${PORT}/healthz"
if [ "$RELOAD" -eq 1 ]; then
  echo "  auto-reload on — but content/ is cached at startup, so restart"
  echo "  the server after editing YAML or Markdown."
fi
echo  "  Ctrl+C to stop."
echo

# exec so uvicorn replaces this shell and receives Ctrl+C / SIGTERM directly.
exec "$VENV/bin/uvicorn" "${ARGS[@]}"
