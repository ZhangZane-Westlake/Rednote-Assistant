# Rednote Assistant

一个本地运行的 AI 创作工具，帮助小红书 / Rednote 博主分析笔记风格、生成选题建议、复盘运营数据。

## 功能

- 笔记管理：记录标题、文案、图片描述和互动数据
- 博主画像：基于历史笔记生成 Markdown 风格画像，并支持手动编辑
- 选题建议：生成选题、拍摄思路和文案大纲
- 数据分析：用图表和 LLM 深度分析复盘内容表现
- 本地存储：笔记和画像保存在本机 SQLite 数据库中
- macOS 打包：支持构建本地 `.app` 和 `.dmg`

## 快速开始

```bash
cd Rednote-Assistant
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

启动后打开浏览器访问：

```text
http://localhost:5000
```

也可以使用 GUI 启动脚本：

```bash
python app_gui.py
```

## 使用流程

1. 设置：填入 DeepSeek API Key（可从 `platform.deepseek.com` 获取）
2. 笔记管理：逐篇添加笔记，包括标题、文案、图片描述、互动数据
3. 博主画像：点击“重新生成”，AI 会根据所有笔记输出风格画像
4. 选题建议：生成 5 个选题、拍摄思路和文案大纲
5. 数据分析：查看图表，并点击“LLM 深度分析”获取 AI 复盘

## 数据存储与隐私

当前版本使用用户主目录下的隐藏数据目录，不读取项目根目录里的 `notes.db`：

```text
~/.xhs-assistant/
├── master.db                 # 主数据库：账号列表、当前账号指针
└── accounts/
    └── <account_id>/
        └── notes.db          # 账号笔记数据库：笔记、配置、博主画像等
```

说明：

- `~/.xhs-assistant/master.db` 是应用启动时读取的入口数据库
- 当前账号的笔记数据存储在 `~/.xhs-assistant/accounts/<account_id>/notes.db`
- 如果旧版 `~/.xhs-assistant/notes.db` 存在，首次初始化时会迁移到默认账号目录
- 项目根目录下的 `notes.db` 不再作为当前版本的数据源，也已在 `.gitignore` 中忽略
- 所有数据默认保存在本地
- 调用 DeepSeek API 时，会发送用于分析的笔记内容到 DeepSeek 服务

## 技术栈

- 后端：Python Flask
- 数据库：SQLite
- 前端：HTML、CSS、原生 JavaScript
- 图表：Chart.js（CDN 加载）
- AI：DeepSeek API（OpenAI 兼容接口）

## 项目结构

```text
.
├── app.py                 # Flask Web 应用入口
├── app_gui.py             # GUI 启动入口
├── database.py            # SQLite 数据访问
├── deepseek_client.py     # DeepSeek API 客户端
├── requirements.txt       # Python 依赖
├── static/                # 前端静态资源
├── templates/             # HTML 模板
├── mac/                   # macOS 打包脚本与资源
└── ~/.xhs-assistant/      # 本地运行数据目录（不会提交到 Git）
```

## macOS 打包（DMG）

在 macOS 上运行：

```bash
cd mac
chmod +x build.sh
./build.sh
```

生成的 DMG 会输出到 `dist/` 目录。

首次打开未签名应用时，可能需要右键点击应用并选择“打开”。如需生成图标，请先安装 Pillow：

```bash
pip3 install Pillow
```

## License

MIT
