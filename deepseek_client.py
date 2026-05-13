"""DeepSeek API client for LLM-powered analysis."""

from openai import OpenAI

# DeepSeek's API is OpenAI-compatible
BASE_URL = "https://api.deepseek.com/v1"


def _get_client(api_key: str, base_url: str = BASE_URL) -> OpenAI:
    return OpenAI(api_key=api_key, base_url=base_url or BASE_URL)


def _float(value, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _int(value, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _notes_to_text(notes: list[dict]) -> str:
    """Convert notes list to a structured text block for prompts."""
    parts = []
    for i, n in enumerate(notes, 1):
        parts.append(
            f"--- 笔记 {i} ---\n"
            f"标题: {n['title']}\n"
            f"话题标签: {n['topics']}\n"
            f"类型: {'视频' if n['content_type']=='video' else '图文'}\n"
            f"发布日期: {n['publish_date']}\n"
            f"正文:\n{n['text_content']}\n"
            f"图片描述:\n{n['image_description']}\n"
            f"数据: 阅读{n['views']} 点赞{n['likes']} 收藏{n['saves']} "
            f"评论{n['comments']} 分享{n['shares']}\n"
        )
    return "\n\n".join(parts)


def _build_context(bio: str, extra: str) -> str:
    """Build additional context blocks for prompt injection."""
    blocks = []
    if bio and bio.strip():
        blocks.append(f"博主主页简介：\n{bio.strip()}")
    if extra and extra.strip():
        blocks.append(f"用户额外要求：\n{extra.strip()}")
    return "\n\n".join(blocks)


# ═══════════════════════════════════════════════════════════
#  Profile generation
# ═══════════════════════════════════════════════════════════

PROFILE_PROMPT = """你是一位小红书内容分析师。请根据以下博主全部笔记，生成一份**博主画像**。

{context}

请严格按照以下 Markdown 格式输出（不要输出多余的开场白或结尾语）：

## 博主定位
(一句话概括这个博主的赛道和独特卖点)

## 内容领域
- (领域1)：占比约X%，简述
- (领域2)：占比约Y%，简述
...

## 写作风格
- 语气特征：
- 句式特点：
- emoji 使用习惯：
- 开头套路：
- 结尾套路：

## 视觉风格
- 图片/视频内容模式：
- 色调倾向：
- 构图偏好：
- 封面特点：

## 高频关键词 Top 5
1. XX
2. XX
3. XX
4. XX
5. XX

## 粉丝互动特征
- 高互动笔记的共同特征：
- 低互动笔记的可能原因：

---

以下是笔记内容：

{notes_text}"""


def generate_profile(notes: list[dict], api_key: str, base_url: str = BASE_URL,
                     model: str = "deepseek-chat", temperature=0.5,
                     max_tokens=4096, bio: str = "", extra: str = "") -> str:
    """Generate blogger profile in Markdown. Returns profile text."""
    if not notes:
        return "# 博主画像\n\n暂无笔记数据。请先在「笔记管理」中添加笔记。"

    client = _get_client(api_key, base_url)
    notes_text = _notes_to_text(notes)
    context = _build_context(bio, extra)

    response = client.chat.completions.create(
        model=model or "deepseek-chat",
        messages=[
            {"role": "system", "content": "你是一位专业的小红书内容分析专家。"},
            {"role": "user", "content": PROFILE_PROMPT.format(
                notes_text=notes_text, context=context
            )},
        ],
        temperature=_float(temperature, 0.5),
        max_tokens=_int(max_tokens, 4096),
    )
    return response.choices[0].message.content.strip()


# ═══════════════════════════════════════════════════════════
#  Content suggestions
# ═══════════════════════════════════════════════════════════

SUGGESTION_PROMPT = """你是一位小红书内容策划师。请根据博主的画像和过往笔记，生成 **5 个**接下来可发布的选题建议。

{context}

博主画像：

{profile}

过往笔记摘要：

{notes_text}

请严格按照以下格式输出（每个选题之间用 --- 分隔）：

### 选题 1：{{标题}}
- **推荐形式**：图文 / 视频，理由：
- **拍摄思路**：
  - 场景：
  - 构图：
  - 需要准备的道具/对象：
- **文案大纲**：
  - 开头钩子：
  - 正文结构：
  - 结尾互动引导：
- **与过往的关联**：

---
### 选题 2：...
"""


def generate_suggestions(notes: list[dict], profile: str, api_key: str,
                         base_url: str = BASE_URL, model: str = "deepseek-chat",
                         temperature=0.8, max_tokens=4096,
                         bio: str = "", extra: str = "") -> str:
    """Generate 5 content suggestions in Markdown."""
    if not notes:
        return "暂无笔记数据，无法生成选题建议。"

    client = _get_client(api_key, base_url)
    notes_text = _notes_to_text(notes[:10])
    context = _build_context(bio, extra)

    response = client.chat.completions.create(
        model=model or "deepseek-chat",
        messages=[
            {"role": "system", "content": "你是一位专业的小红书内容策划师。"},
            {"role": "user", "content": SUGGESTION_PROMPT.format(
                profile=profile, notes_text=notes_text, context=context
            )},
        ],
        temperature=_float(temperature, 0.8),
        max_tokens=_int(max_tokens, 4096),
    )
    return response.choices[0].message.content.strip()


# ═══════════════════════════════════════════════════════════
#  Deep analysis (data-driven)
# ═══════════════════════════════════════════════════════════

ANALYSIS_PROMPT = """你是一位小红书数据分析师。请根据以下笔记数据，分析用户偏好和内容策略。

{context}

所有笔记数据：

{notes_text}

请输出以下分析（Markdown 格式）：

## 互动数据概览
- 总体情况（总阅读、总互动等）

## 爆款 vs 冷门
- 互动最高的 3 篇分别是什么？有什么共同点？
- 互动最低的 3 篇可能的原因是什么？

## 内容形式分析
- 图文 vs 视频，哪种形式表现更好？

## 话题表现
- 哪些话题互动率更高？

## 发布时间建议
- 是否有明显的时间规律？

## 优化建议
- 3 条具体可执行的改进建议
"""


def deep_analyze(notes: list[dict], api_key: str, base_url: str = BASE_URL,
                 model: str = "deepseek-chat", temperature=0.5,
                 max_tokens=4096, bio: str = "", extra: str = "") -> str:
    """Deep analysis of note performance."""
    if not notes:
        return "暂无笔记数据，无法分析。"

    client = _get_client(api_key, base_url)
    notes_text = _notes_to_text(notes)
    context = _build_context(bio, extra)

    response = client.chat.completions.create(
        model=model or "deepseek-chat",
        messages=[
            {"role": "system", "content": "你是一位小红书运营数据分析师。"},
            {"role": "user", "content": ANALYSIS_PROMPT.format(
                notes_text=notes_text, context=context
            )},
        ],
        temperature=_float(temperature, 0.5),
        max_tokens=_int(max_tokens, 4096),
    )
    return response.choices[0].message.content.strip()


# ═══════════════════════════════════════════════════════════
#  Content Creation — 根据照片/视频描述生成风格建议 + 笔记正文
# ═══════════════════════════════════════════════════════════

CONTENT_CREATION_PROMPT = """你是一位小红书内容创作专家。用户提供了一组照片/视频的描述，请根据这些素材生成两部分内容：

{context}

照片/视频素材描述：
{content_description}

请严格按照以下格式输出（两部分之间用 ===正文=== 分隔）：

## 🎨 剪辑与排版风格建议
- **整体风格**：(如：清新治愈风、暗调高级感、vlog 日常感…)
- **色调/滤镜建议**：(如：低饱和度暖调、冷白皮调、胶片感…)
- **图片排版**：(如：封面大图+细节拼接、九宫格、上下对比…)
- **视频剪辑节奏**：(如：快剪卡点、慢镜头特写、转场建议…)
- **BGM 推荐**：(如：轻快钢琴、Lo-fi、热门卡点音乐…)
- **封面制作要点**：(标题字体、配色、关键元素…)

===正文===

## 📝 笔记正文

(这里输出完整的、可直接发布的小红书笔记文案，包含 emoji、话题标签、互动引导)"""


def generate_content(description: str, api_key: str, profile: str = "",
                     bio: str = "", extra: str = "", base_url: str = BASE_URL,
                     model: str = "deepseek-chat", temperature=0.75,
                     max_tokens=4096) -> dict:
    """根据照片/视频描述生成风格建议和笔记正文。
    Returns {"style_advice": "...", "body_text": "..."}"""
    if not description or not description.strip():
        return {"error": "请提供照片/视频的描述内容"}

    client = _get_client(api_key, base_url)

    context_parts = []
    if bio and bio.strip():
        context_parts.append(f"博主主页简介：\n{bio.strip()}")
    if profile and profile.strip():
        # 截取画像前 1500 字避免 prompt 过长
        context_parts.append(f"博主画像参考：\n{profile.strip()[:1500]}")
    if extra and extra.strip():
        context_parts.append(f"用户额外要求：\n{extra.strip()}")
    context = "\n\n".join(context_parts)

    response = client.chat.completions.create(
        model=model or "deepseek-chat",
        messages=[
            {"role": "system", "content": "你是一位专业的小红书内容创作专家，擅长视觉风格设计和文案撰写。"},
            {"role": "user", "content": CONTENT_CREATION_PROMPT.format(
                content_description=description.strip(),
                context=context,
            )},
        ],
        temperature=_float(temperature, 0.75),
        max_tokens=_int(max_tokens, 4096),
    )
    full = response.choices[0].message.content.strip()

    # Split by ===正文===
    if "===正文===" in full:
        parts = full.split("===正文===", 1)
        style_advice = parts[0].strip()
        body_text = parts[1].strip()
    else:
        style_advice = full
        body_text = ""

    return {
        "style_advice": style_advice,
        "body_text": body_text,
        "raw": full,
    }


# ═══════════════════════════════════════════════════════════
#  Chat — 自由对话
# ═══════════════════════════════════════════════════════════

CHAT_SYSTEM_PROMPT = """你是一位小红书运营顾问，精通内容创作、账号运营、数据分析、平台算法。
你了解用户是一名小红书博主，會用亲切但专业的方式回答问题。
回答问题时：
- 优先结合用户自己的笔记数据和博主画像给出针对性建议
- 对于平台运营类问题，给出具体可执行的建议而非空泛理论
- 保持温暖鼓励的语气，像一位有经验的同行
- 用中文回答"""


def chat(api_key: str, messages: list[dict], notes_context: str = "",
         profile_context: str = "", bio: str = "", base_url: str = BASE_URL,
         model: str = "deepseek-chat", temperature=0.8, max_tokens=2048) -> str:
    """自由对话，支持多轮。messages 格式: [{"role":"user","content":"..."}, ...]
    注意：messages 只应包含最近的对话轮次（不含 system prompt）。
    """
    client = _get_client(api_key, base_url)

    # Build system prompt with context
    context_blocks = []
    if bio and bio.strip():
        context_blocks.append(f"博主的账号简介：\n{bio.strip()}")
    if profile_context and profile_context.strip():
        context_blocks.append(f"博主的画像：\n{profile_context.strip()[:2000]}")
    if notes_context and notes_context.strip():
        context_blocks.append(f"博主最近的笔记数据：\n{notes_context.strip()[:2000]}")

    system_content = CHAT_SYSTEM_PROMPT
    if context_blocks:
        system_content += "\n\n---\n\n以下是该博主的背景信息，请结合这些信息给出针对性建议：\n\n" + "\n\n".join(context_blocks)

    full_messages = [{"role": "system", "content": system_content}] + messages

    response = client.chat.completions.create(
        model=model or "deepseek-chat",
        messages=full_messages,
        temperature=_float(temperature, 0.8),
        max_tokens=_int(max_tokens, 2048),
    )
    return response.choices[0].message.content.strip()
