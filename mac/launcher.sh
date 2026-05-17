#!/bin/bash
# ──────────────────────────────────────────────────
#  XHS 助手 Launcher — macOS .app 入口（GUI 版）
# ──────────────────────────────────────────────────

set -e

LOG_DIR="$HOME/Library/Logs/XHSAssistant"
LOG_FILE="$LOG_DIR/launcher.log"
mkdir -p "$LOG_DIR"
exec >>"$LOG_FILE" 2>&1

show_error() {
    local message="$1"
    osascript -e "display dialog \"$message\n\n日志位置：$LOG_FILE\" buttons {\"OK\"} default button 1 with icon stop" || true
}

trap 'show_error "小红书笔记助手启动失败，请把日志内容发给我。"' ERR

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
RESOURCES_DIR="$(cd "$SCRIPT_DIR/../Resources" && pwd)"
cd "$RESOURCES_DIR"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "$(date '+%Y-%m-%d %H:%M:%S') launcher start"
echo "Resources: $RESOURCES_DIR"

# ── 扩展 PATH（conda / homebrew / 系统） ─────
export PATH="/opt/miniconda3/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

# ── 找 Python 3 ─────────────────────────────
PYTHON=""
for candidate in python3 \
                 /opt/miniconda3/bin/python3 \
                 /opt/homebrew/bin/python3 \
                 /usr/local/bin/python3 \
                 /usr/bin/python3; do
    if [ -x "$candidate" ] && "$candidate" -c "import sys; exit(0)" 2>/dev/null; then
        PYTHON="$candidate"
        break
    fi
done

if [ -z "$PYTHON" ]; then
    show_error "找不到 Python 3。"
    exit 1
fi

echo "Python: $PYTHON"
"$PYTHON" --version

# ── 依赖检查与安装 ───────────────────────────
if ! "$PYTHON" -c "import flask, flask_cors, openai, webview, markdown" 2>/dev/null; then
    echo "Installing dependencies from requirements.txt"
    if ! "$PYTHON" -m pip --version >/dev/null 2>&1; then
        "$PYTHON" -m ensurepip --upgrade
    fi
    if [ "$(uname -s)" = "Darwin" ]; then
        "$PYTHON" -m pip install --quiet --user -r requirements.txt pyobjc
    else
        "$PYTHON" -m pip install --quiet --user -r requirements.txt
    fi
fi

echo "Starting app_gui.py"
"$PYTHON" "$RESOURCES_DIR/app_gui.py"
