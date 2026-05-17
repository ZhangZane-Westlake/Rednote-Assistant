#!/bin/bash
# ──────────────────────────────────────────────────
#  XHS 助手 Launcher — macOS .app 入口（GUI 版）
# ──────────────────────────────────────────────────

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
RESOURCES_DIR="$(cd "$SCRIPT_DIR/../Resources" && pwd)"
cd "$RESOURCES_DIR"

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
    osascript -e 'display dialog "找不到 Python 3。" buttons {"OK"} default button 1 with icon stop'
    exit 1
fi

# ── 依赖检查与安装 ───────────────────────────
if ! "$PYTHON" -c "import flask, flask_cors, openai, webview, markdown" 2>/dev/null; then
    "$PYTHON" -m pip install --quiet -r requirements.txt 2>/dev/null
fi

# ── 启动（不用 exec，保留 shell 作为父进程）──
"$PYTHON" "$RESOURCES_DIR/app_gui.py"
