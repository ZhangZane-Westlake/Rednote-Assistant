"""GUI 入口 — 在原生窗口中显示小红书笔记助手。

启动 Flask 服务器（后台线程），然后用 macOS 原生 WebView
嵌入页面。用户双击 App 就直接看到操作界面，无需浏览器。
"""

import threading
import sys
import webview

from app import app as flask_app


def run_flask():
    """在后台线程启动 Flask，关闭 reloader 避免与线程冲突。"""
    flask_app.run(
        host="127.0.0.1",
        port=5001,
        debug=False,           # 关闭 reloader，否则线程里会冲突
        use_reloader=False,
    )


def main():
    # 启动 Flask
    t = threading.Thread(target=run_flask, daemon=True)
    t.start()

    # 创建原生窗口，嵌入 Web 页面
    window = webview.create_window(
        title="📕 小红书笔记助手",
        url="http://127.0.0.1:5001",
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
