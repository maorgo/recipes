#!/usr/bin/env bash
#
# Startup script for the Recipes web app.
# Detects OS, ensures Python 3 exists, creates venv, installs deps,
# initialises the DB, creates required directories, and runs the app.
#

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

VENV_DIR="venv"
PYTHON=""
MIN_PYTHON_MAJOR=3
MIN_PYTHON_MINOR=10

# ─── Colours ──────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[✓]${NC} $1"; }
warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
fail()  { echo -e "${RED}[✗]${NC} $1"; exit 1; }

# ─── Detect OS ────────────────────────────────────────────────────────
detect_os() {
    case "$(uname -s)" in
        Linux*)   OS="linux";;
        Darwin*)  OS="macos";;
        MINGW*|MSYS*|CYGWIN*) OS="windows";;
        *)        fail "Unsupported OS: $(uname -s)";;
    esac
    info "Detected OS: $OS"
}

# ─── Find or install Python ──────────────────────────────────────────
find_python() {
    for candidate in python3 python; do
        if command -v "$candidate" &>/dev/null; then
            local ver
            ver="$("$candidate" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null)" || continue
            local major="${ver%%.*}"
            local minor="${ver#*.}"
            if [ "$major" -ge "$MIN_PYTHON_MAJOR" ] && [ "$minor" -ge "$MIN_PYTHON_MINOR" ]; then
                PYTHON="$candidate"
                info "Found $PYTHON ($ver)"
                return
            fi
        fi
    done
}

install_python() {
    warn "Python >= ${MIN_PYTHON_MAJOR}.${MIN_PYTHON_MINOR} not found. Attempting to install..."

    case "$OS" in
        macos)
            if command -v brew &>/dev/null; then
                info "Installing Python via Homebrew..."
                brew install python3
            else
                fail "Homebrew not found. Install Python 3 manually: https://www.python.org/downloads/"
            fi
            ;;
        linux)
            if command -v apt-get &>/dev/null; then
                info "Installing Python via apt..."
                sudo apt-get update -qq && sudo apt-get install -y python3 python3-venv python3-pip
            elif command -v dnf &>/dev/null; then
                info "Installing Python via dnf..."
                sudo dnf install -y python3 python3-pip
            elif command -v yum &>/dev/null; then
                info "Installing Python via yum..."
                sudo yum install -y python3 python3-pip
            elif command -v pacman &>/dev/null; then
                info "Installing Python via pacman..."
                sudo pacman -Sy --noconfirm python python-pip
            else
                fail "No supported package manager found. Install Python 3 manually: https://www.python.org/downloads/"
            fi
            ;;
        windows)
            if command -v winget &>/dev/null; then
                info "Installing Python via winget..."
                winget install -e --id Python.Python.3.12 --accept-source-agreements --accept-package-agreements
            elif command -v choco &>/dev/null; then
                info "Installing Python via Chocolatey..."
                choco install python3 -y
            else
                fail "No package manager found. Install Python 3 from https://www.python.org/downloads/"
            fi
            ;;
    esac

    # Re-hash PATH to pick up newly installed binary
    hash -r 2>/dev/null || true

    find_python
    [ -n "$PYTHON" ] || fail "Python installation succeeded but binary not found in PATH. Restart your terminal and try again."
}

# ─── Virtual environment ─────────────────────────────────────────────
ensure_venv() {
    if [ ! -d "$VENV_DIR" ]; then
        info "Creating virtual environment..."
        "$PYTHON" -m venv "$VENV_DIR"
    else
        info "Virtual environment already exists."
    fi
}

# ─── Install dependencies ────────────────────────────────────────────
install_deps() {
    info "Installing / updating dependencies..."
    "$VENV_DIR/bin/pip" install --quiet --upgrade pip
    "$VENV_DIR/bin/pip" install --quiet -r requirements.txt
    info "Dependencies installed."
}

# ─── Required directories ────────────────────────────────────────────
ensure_directories() {
    for dir in static/uploads static/videos instance; do
        if [ ! -d "$dir" ]; then
            mkdir -p "$dir"
            info "Created directory: $dir"
        fi
    done
}

# ─── Database ────────────────────────────────────────────────────────
ensure_database() {
    if [ ! -f "instance/recipes.db" ]; then
        info "Initialising database..."
        "$VENV_DIR/bin/python" init_db.py
    else
        info "Database already exists."
    fi
}

# ─── Run ──────────────────────────────────────────────────────────────
run_app() {
    info "Starting the app on http://localhost:5000 ..."
    echo ""
    "$VENV_DIR/bin/python" app.py
}

# ─── Main ─────────────────────────────────────────────────────────────
main() {
    echo ""
    echo "==============================="
    echo "   מתכונים — Recipes Startup"
    echo "==============================="
    echo ""

    detect_os
    find_python
    [ -n "$PYTHON" ] || install_python
    ensure_venv
    install_deps
    ensure_directories
    ensure_database
    run_app
}

main
