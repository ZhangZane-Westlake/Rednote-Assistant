"""GUI 入口 — 在原生窗口中显示小红书笔记助手。

启动 Flask 服务器（后台线程），然后用 macOS 原生 WebView
嵌入页面。用户双击 App 就直接看到操作界面，无需浏览器。
"""

import threading
import sys
import time
import urllib.request
import webview

from app import APP_HOST, APP_PORT, APP_URL, app as flask_app


def run_flask():
    """在后台线程启动 Flask，关闭 reloader 避免与线程冲突。"""
    flask_app.run(
        host=APP_HOST,
        port=APP_PORT,
        debug=False,           # 关闭 reloader，否则线程里会冲突
        use_reloader=False,
        threaded=True,
    )


def wait_for_flask(timeout: float = 10.0) -> bool:
    """等待后台 Flask 启动完成，避免 WebView 先加载导致空白页。"""
    deadline = time.time() + timeout
    last_error = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(APP_URL, timeout=0.5) as response:
                return 200 <= response.status < 500
        except Exception as exc:
            last_error = exc
            time.sleep(0.1)
    print(f"Flask server did not become ready: {last_error}", file=sys.stderr)
    return False


def main():
    # 启动 Flask
    t = threading.Thread(target=run_flask, daemon=True)
    t.start()

    # 等服务实际可访问后再让 WebView 加载，否则在部分 macOS/WebKit
    # 环境会先加载失败并停留在空白页。
    wait_for_flask()

    # 创建原生窗口，嵌入 Web 页面
    window = webview.create_window(
        title="📕 小红书笔记助手",
        url=APP_URL,
        width=1200,
        height=820,
        min_size=(900, 600),
        resizable=True,
        text_select=True,      # 允许文本选择
        easy_drag=False,
    )

    # 进入事件循环（窗口关闭时自动退出）
    webview.start()


if __name__ == "__main__":
    main()
