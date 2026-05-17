# Rednote Assistant

一个本地运行的 AI 创作工具，帮助小红书 / Rednote 博主分析笔记风格、生成选题建议、复盘运营数据。

## 功能

- **笔记管理**：记录标题、文案、图片描述和互动数据，支持多账号隔离
- **AI 识图**：上传图片后调用 OpenAI 兼容视觉模型自动生成图片描述
- **博主画像**：基于历史笔记生成 Markdown 风格画像，支持手动编辑，可附加额外提示词定制分析方向
- **选题建议**：每次生成 5 个选题、拍摄思路和文案大纲，**自动保存历史记录**，可查看/删除
- **数据分析**：互动数据图表（柱状图）+ LLM 深度分析（含表格、建议），分析结果自动持久化
- **内容创作**：根据素材描述生成风格建议和笔记正文，支持历史记录
- **AI 对话**：多轮自由对话，支持对话历史持久化和中断取消
- **本地存储**：数据保存在本机 SQLite，多账号数据完全隔离
- **macOS 打包**：支持构建本地 `.app` 和 `.dmg`
- **Markdown 表格支持**：服务端使用 `markdown` 库渲染，分析报告中的表格可正确显示

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
http://localhost:5001
```

也可以使用 GUI 启动脚本：

```bash
python app_gui.py
```

## 使用流程

1. **设置**：填入文本 LLM（DeepSeek / OpenAI 兼容）的 API Key、Base URL 和模型名；如需识图，再填入图片识别的 API Key、Base URL 和模型名
2. **笔记管理**：逐篇添加笔记，包括标题、文案、图片描述、互动数据；可上传图片自动生成描述
3. **博主画像**：点击生成，AI 根据所有笔记输出风格画像；可使用额外提示词定制分析角度
4. **选题建议**：生成 5 个选题、拍摄思路和文案大纲；每次生成自动保存历史，可点击历史项回溯或删除
5. **内容创作**：上传图片识图或手动描述素材，生成风格建议和笔记正文；支持历史记录查看/删除
6. **数据分析**：查看互动数据图表，点击"LLM 深度分析"获取 AI 复盘（含表格）
7. **AI 对话**：自由提问运营相关问题，AI 会结合你的笔记数据给出针对性建议

### 额外提示词

以下模块支持输入额外提示词，在生成请求时自动附加：

- 博主画像（`extra_prompt`）：如"重点关注封面风格"
- 选题建议（`extra_prompt`）：如"侧重夏日穿搭、母婴好物"
- 数据分析（`extra_prompt`）：如"重点分析收藏率偏低的原因"
- 内容创作（`extra_prompt`）：如"偏可爱风格、需要 SEO 关键词"

### 数据清除

设置页提供按模块清除数据的功能，支持清除：博主画像、数据分析、选题建议历史、内容创作历史，以及一键清除以上全部。笔记本身不受影响。

## 模型接口说明

- 文本模型和图片识别均使用 OpenAI 兼容接口：在设置页填写对应服务商的 API Key、Base URL 和模型名即可
- 默认文本模型为 `deepseek-chat`，Base URL 为 `https://api.deepseek.com/v1`
- 默认视觉模型名为 `gemma-4`，可在设置页或 `model_settings.json` 编辑入口中改为任意兼容服务商提供的视觉模型名
- 上传图片会先压缩到适合视觉模型调用的大小，再发送到用户配置的图片识别模型服务
- 设置页还提供「模型调用 setting 文件」编辑入口，支持以 JSON 格式批量编辑文本和视觉模型的调用参数

## 数据存储与隐私

当前版本使用用户主目录下的隐藏数据目录：

```text
~/.xhs-assistant/
├── master.db                 # 主数据库：账号列表、当前账号指针
└── accounts/
    └── <account_id>/
        └── notes.db          # 账号笔记数据库：笔记、配置、画像、历史记录等
```

说明：

- `~/.xhs-assistant/master.db` 是应用启动时读取的入口数据库
- 当前账号的笔记数据存储在 `~/.xhs-assistant/accounts/<account_id>/notes.db`
- 如果旧版 `~/.xhs-assistant/notes.db` 存在，首次初始化时会迁移到默认账号目录
- 项目根目录下的 `notes.db` 不再作为当前版本的数据源，也已在 `.gitignore` 中忽略
- 所有数据默认保存在本地
- 调用文本 LLM API 时，会发送用于分析的笔记内容到用户配置的文本模型服务
- 上传图片识图时，图片会发送到用户配置的图片识别模型服务；应用不会把上传图片长期保存到本地

## 技术栈

- **后端**：Python Flask
- **数据库**：SQLite（多账号隔离）
- **前端**：HTML、CSS、原生 JavaScript
- **图表**：Chart.js（CDN 加载）
- **AI 接口**：OpenAI 兼容 Chat Completions API（文本模型 + 视觉模型）
- **Markdown 渲染**：Python `markdown` 库（支持表格、代码块）

## 项目结构

```text
.
├── app.py                 # Flask Web 应用入口
├── app_gui.py             # GUI 启动入口（pywebview）
├── database.py            # SQLite 数据访问（多账号支持）
├── deepseek_client.py     # 文本 LLM API 客户端
├── vision_client.py       # 图片识别 / Vision API 客户端
├── requirements.txt       # Python 依赖
├── static/                # 前端静态资源
│   └── app.js             # 前端业务逻辑
├── templates/             # HTML 模板
│   └── index.html         # 主页面
├── tests/                 # 测试文件
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

首次打开未签名应用时，可能需要右键点击应用并选择"打开"。打包脚本会在 `.app` 首次启动时自动安装 `requirements.txt` 中的完整依赖；如果你是手动运行源码版，仍然需要先执行 `pip install -r requirements.txt`。

如需生成图标，请先安装 Pillow：

```bash
pip3 install Pillow
```

## License

MIT
