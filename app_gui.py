"""GUI 入口 — 在原生窗口中显示小红书笔记助手。

启动 Flask 服务器（后台线程），然后用 macOS 原生 WebView
嵌入页面。用户双击 App 就直接看到操作界面，无需浏览器。
"""

import sys
import threading
import time
import urllib.request

try:
    import webview
except ModuleNotFoundError as exc:
    print("缺少 pywebview 或 macOS 原生后端依赖。", file=sys.stderr)
    raise

from app import APP_HOST, APP_PORT, APP_URL, app as flask_app


def run_flask() -> None:
    """在后台线程启动 Flask，关闭 reloader 避免与线程冲突。"""
    flask_app.run(
        host=APP_HOST,
        port=APP_PORT,
        debug=False,
        use_reloader=False,
        threaded=True,
    )


def wait_for_flask(timeout: float = 10.0) -> bool:
    """等待后台 Flask 启动完成，避免 WebView 先加载导致空白页。"""
    deadline = time.time() + timeout
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(APP_URL, timeout=0.5) as response:
                return 200 <= response.status < 500
        except Exception as exc:
            last_error = exc
            time.sleep(0.1)
    print(f"Flask server did not become ready: {last_error}", file=sys.stderr)
    return False


def main() -> None:
    """启动后台服务并打开原生窗口。"""
    server_thread = threading.Thread(target=run_flask, daemon=True)
    server_thread.start()

    wait_for_flask()

    webview.create_window(
        title="📕 小红书笔记助手",
        url=APP_URL,
        width=1200,
        height=820,
        min_size=(900, 600),
        resizable=True,
        text_select=True,
        easy_drag=False,
    )
    webview.start()


if __name__ == "__main__":
    main()
