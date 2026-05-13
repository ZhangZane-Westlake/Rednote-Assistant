"""Flask backend for XHS Assistant."""

import io
import json
import traceback
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS

import database as db
from deepseek_client import generate_profile, generate_suggestions, deep_analyze, generate_content, chat
from vision_client import DEFAULT_VISION_PROMPT, describe_images

app = Flask(__name__)
CORS(app)

db.init_db()

APP_HOST = "127.0.0.1"
APP_PORT = 5001
APP_URL = f"http://{APP_HOST}:{APP_PORT}"


# ═══════════════════════════════════════════════════════════
#  AI Settings helpers
# ═══════════════════════════════════════════════════════════

DEFAULT_TEXT_BASE_URL = "https://api.deepseek.com/v1"
DEFAULT_TEXT_MODEL = "deepseek-chat"
DEFAULT_TEXT_TEMPERATURE = "0.7"
DEFAULT_TEXT_MAX_TOKENS = "4096"
DEFAULT_VISION_MODEL = "gemma-4"
DEFAULT_VISION_TEMPERATURE = "0.2"
DEFAULT_VISION_MAX_TOKENS = "2048"
MAX_VISION_IMAGES = 20
MAX_IMAGE_BYTES = 100 * 1024 * 1024
TARGET_VISION_IMAGE_BYTES = 1 * 1024 * 1024


def _cfg(key: str, default: str = "") -> str:
    return db.get_config(key, default)


def _to_float(value, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_int(value, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _text_llm_settings(default_temperature=0.7, default_max_tokens=4096):
    return {
        "api_key": _cfg("deepseek_api_key", ""),
        "base_url": _cfg("deepseek_base_url", DEFAULT_TEXT_BASE_URL),
        "model": _cfg("deepseek_model", DEFAULT_TEXT_MODEL),
        "temperature": _to_float(_cfg("deepseek_temperature", str(default_temperature)), default_temperature),
        "max_tokens": _to_int(_cfg("deepseek_max_tokens", str(default_max_tokens)), default_max_tokens),
    }


def _vision_settings():
    return {
        "api_key": _cfg("vision_api_key", ""),
        "base_url": _cfg("vision_base_url", ""),
        "model": _cfg("vision_model", DEFAULT_VISION_MODEL),
        "temperature": _to_float(_cfg("vision_temperature", DEFAULT_VISION_TEMPERATURE), 0.2),
        "max_tokens": _to_int(_cfg("vision_max_tokens", DEFAULT_VISION_MAX_TOKENS), 2048),
        "prompt": _cfg("vision_prompt", DEFAULT_VISION_PROMPT),
    }


def _model_settings_file_data() -> dict:
    """Return the model-call settings as an editable JSON-like object."""
    return {
        "deepseek": {
            "api_key": db.get_config("deepseek_api_key", ""),
            "base_url": db.get_config("deepseek_base_url", DEFAULT_TEXT_BASE_URL),
            "model": db.get_config("deepseek_model", DEFAULT_TEXT_MODEL),
            "temperature": _to_float(db.get_config("deepseek_temperature", DEFAULT_TEXT_TEMPERATURE), 0.7),
            "max_tokens": _to_int(db.get_config("deepseek_max_tokens", DEFAULT_TEXT_MAX_TOKENS), 4096),
        },
        "vision": {
            "api_key": db.get_config("vision_api_key", ""),
            "base_url": db.get_config("vision_base_url", ""),
            "model": db.get_config("vision_model", DEFAULT_VISION_MODEL),
            "temperature": _to_float(db.get_config("vision_temperature", DEFAULT_VISION_TEMPERATURE), 0.2),
            "max_tokens": _to_int(db.get_config("vision_max_tokens", DEFAULT_VISION_MAX_TOKENS), 2048),
            "prompt": db.get_config("vision_prompt", DEFAULT_VISION_PROMPT),
        },
    }


def _apply_model_settings_file_data(settings: dict):
    """Persist supported keys from the editable model settings object."""
    mappings = {
        "deepseek": {
            "api_key": "deepseek_api_key",
            "base_url": "deepseek_base_url",
            "model": "deepseek_model",
            "temperature": "deepseek_temperature",
            "max_tokens": "deepseek_max_tokens",
        },
        "vision": {
            "api_key": "vision_api_key",
            "base_url": "vision_base_url",
            "model": "vision_model",
            "temperature": "vision_temperature",
            "max_tokens": "vision_max_tokens",
            "prompt": "vision_prompt",
        },
    }
    for section, keys in mappings.items():
        values = settings.get(section, {})
        if values is None:
            values = {}
        if not isinstance(values, dict):
            raise ValueError(f"{section} 必须是对象")
        for source_key, config_key in keys.items():
            if source_key in values:
                db.set_config(config_key, str(values[source_key]))


def _compress_image_for_vision(content: bytes, mime_type: str) -> tuple[bytes, str]:
    """Compress oversized uploads before sending them to the vision model."""
    if len(content) <= TARGET_VISION_IMAGE_BYTES:
        return content, mime_type or "image/jpeg"

    try:
        from PIL import Image, ImageOps

        with Image.open(io.BytesIO(content)) as image:
            image = ImageOps.exif_transpose(image)
            if image.mode != "RGB":
                image = image.convert("RGB")

            max_side = max(image.size)
            quality = 85
            while True:
                output = io.BytesIO()
                image.save(output, format="JPEG", quality=quality, optimize=True)
                compressed = output.getvalue()
                if len(compressed) <= TARGET_VISION_IMAGE_BYTES:
                    return compressed, "image/jpeg"

                if quality > 45:
                    quality -= 10
                    continue

                if max_side <= 768:
                    return compressed, "image/jpeg"

                scale = max(0.65, (TARGET_VISION_IMAGE_BYTES / len(compressed)) ** 0.5 * 0.92)
                max_side = max(768, int(max_side * scale))
                ratio = max_side / max(image.size)
                new_size = (
                    max(1, int(image.size[0] * ratio)),
                    max(1, int(image.size[1] * ratio)),
                )
                image = image.resize(new_size, Image.Resampling.LANCZOS)
                quality = 85
    except Exception as exc:
        raise ValueError(f"图片压缩失败: {exc}") from exc


# ═══════════════════════════════════════════════════════════
#  Static / Frontend
# ═══════════════════════════════════════════════════════════

@app.route("/")
def index():
    return render_template("index.html")


# ═══════════════════════════════════════════════════════════
#  Account API
# ═══════════════════════════════════════════════════════════

@app.route("/api/accounts", methods=["GET"])
def api_list_accounts():
    accounts = db.list_accounts()
    current = db.get_current_account_id()
    return jsonify({
        "accounts": accounts,
        "current_id": current,
    })


@app.route("/api/accounts", methods=["POST"])
def api_add_account():
    data = request.get_json(force=True)
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "账号名称不能为空"}), 400
    try:
        acct = db.add_account(name)
        return jsonify(acct), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/accounts/<account_id>", methods=["DELETE"])
def api_delete_account(account_id):
    accounts = db.list_accounts()
    if len(accounts) <= 1:
        return jsonify({"error": "至少保留一个账号"}), 400
    try:
        db.delete_account(account_id)
        return jsonify({"ok": True, "current_id": db.get_current_account_id()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/accounts/<account_id>", methods=["PUT"])
def api_rename_account(account_id):
    data = request.get_json(force=True)
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "名称不能为空"}), 400
    try:
        db.rename_account(account_id, name)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/accounts/switch", methods=["POST"])
def api_switch_account():
    data = request.get_json(force=True)
    account_id = data.get("account_id", "")
    if not account_id:
        return jsonify({"error": "请指定账号"}), 400
    try:
        db.set_current_account(account_id)
        return jsonify({"ok": True, "current_id": account_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


# ═══════════════════════════════════════════════════════════
#  Notes API
# ═══════════════════════════════════════════════════════════

@app.route("/api/notes", methods=["GET"])
def api_list_notes():
    return jsonify(db.list_notes())


@app.route("/api/notes", methods=["POST"])
def api_create_note():
    data = request.get_json(force=True)
    if not data.get("title"):
        return jsonify({"error": "标题不能为空"}), 400
    note = db.create_note(data)
    return jsonify(note), 201


@app.route("/api/notes/<int:note_id>", methods=["PUT"])
def api_update_note(note_id):
    note = db.get_note(note_id)
    if not note:
        return jsonify({"error": "笔记不存在"}), 404
    data = request.get_json(force=True)
    note = db.update_note(note_id, data)
    return jsonify(note)


@app.route("/api/notes/<int:note_id>", methods=["DELETE"])
def api_delete_note(note_id):
    note = db.get_note(note_id)
    if not note:
        return jsonify({"error": "笔记不存在"}), 404
    db.delete_note(note_id)
    return jsonify({"ok": True})


# ═══════════════════════════════════════════════════════════
#  Profile API
# ═══════════════════════════════════════════════════════════

@app.route("/api/profile", methods=["GET"])
def api_get_profile():
    p = db.get_config("profile_md", "")
    return jsonify({"content": p})


@app.route("/api/profile/generate", methods=["POST"])
def api_generate_profile():
    api_key = db.get_config("deepseek_api_key", "")
    if not api_key:
        return jsonify({"error": "请先在设置中配置 DeepSeek API Key"}), 400

    notes = db.list_notes()
    if not notes:
        return jsonify({"error": "暂无笔记数据"}), 400

    data = request.get_json(silent=True) or {}
    bio = db.get_config("blogger_bio", "")
    extra = data.get("extra_prompt", "")

    try:
        llm = _text_llm_settings(default_temperature=0.5, default_max_tokens=4096)
        profile_md = generate_profile(notes, api_key, base_url=llm["base_url"],
                                      model=llm["model"], temperature=llm["temperature"],
                                      max_tokens=llm["max_tokens"], bio=bio, extra=extra)
        db.set_config("profile_md", profile_md)
        return jsonify({"content": profile_md})
    except Exception as e:
        return jsonify({"error": f"生成失败: {str(e)}"}), 500


@app.route("/api/profile", methods=["PUT"])
def api_save_profile():
    data = request.get_json(force=True)
    db.set_config("profile_md", data.get("content", ""))
    return jsonify({"ok": True})


# ═══════════════════════════════════════════════════════════
#  Suggestions API
# ═══════════════════════════════════════════════════════════

@app.route("/api/suggestions", methods=["POST"])
def api_generate_suggestions():
    api_key = db.get_config("deepseek_api_key", "")
    if not api_key:
        return jsonify({"error": "请先在设置中配置 DeepSeek API Key"}), 400

    notes = db.list_notes()
    profile = db.get_config("profile_md", "")

    data = request.get_json(silent=True) or {}
    bio = db.get_config("blogger_bio", "")
    extra = data.get("extra_prompt", "")

    try:
        llm = _text_llm_settings(default_temperature=0.8, default_max_tokens=4096)
        result = generate_suggestions(notes, profile, api_key, base_url=llm["base_url"],
                                      model=llm["model"], temperature=llm["temperature"],
                                      max_tokens=llm["max_tokens"], bio=bio, extra=extra)
        return jsonify({"content": result})
    except Exception as e:
        return jsonify({"error": f"生成失败: {str(e)}"}), 500


# ═══════════════════════════════════════════════════════════
#  Analytics API
# ═══════════════════════════════════════════════════════════

@app.route("/api/analytics/stats", methods=["GET"])
def api_analytics_stats():
    notes = db.list_notes()
    if not notes:
        return jsonify({"total_notes": 0})

    total = len(notes)
    total_views = sum(n["views"] for n in notes)
    total_likes = sum(n["likes"] for n in notes)
    total_saves = sum(n["saves"] for n in notes)
    total_comments = sum(n["comments"] for n in notes)
    total_shares = sum(n["shares"] for n in notes)

    # Per note data for charts
    chart_data = [
        {
            "title": n["title"],
            "views": n["views"],
            "likes": n["likes"],
            "saves": n["saves"],
            "comments": n["comments"],
            "shares": n["shares"],
            "content_type": n["content_type"],
            "topics": n["topics"],
            "publish_date": n["publish_date"],
        }
        for n in notes
    ]

    # Content type comparison
    photo_notes = [n for n in notes if n["content_type"] == "photo"]
    video_notes = [n for n in notes if n["content_type"] == "video"]
    photo_avg_likes = (
        sum(n["likes"] for n in photo_notes) / len(photo_notes) if photo_notes else 0
    )
    video_avg_likes = (
        sum(n["likes"] for n in video_notes) / len(video_notes) if video_notes else 0
    )

    # Topic stats — split by , ， #
    topic_stats = {}
    for n in notes:
        for t in n["topics"].replace("，", ",").replace("#", ",").replace(" ", "").split(","):
            t = t.strip()
            if not t:
                continue
            if t not in topic_stats:
                topic_stats[t] = {"count": 0, "total_likes": 0}
            topic_stats[t]["count"] += 1
            topic_stats[t]["total_likes"] += n["likes"]

    topic_list = sorted(
        [{"topic": k, **v, "avg_likes": round(v["total_likes"] / v["count"], 1)} for k, v in topic_stats.items()],
        key=lambda x: x["count"],
        reverse=True,
    )

    return jsonify(
        {
            "total_notes": total,
            "total_views": total_views,
            "total_likes": total_likes,
            "total_saves": total_saves,
            "total_comments": total_comments,
            "total_shares": total_shares,
            "photo_count": len(photo_notes),
            "video_count": len(video_notes),
            "photo_avg_likes": round(photo_avg_likes, 1),
            "video_avg_likes": round(video_avg_likes, 1),
            "chart_data": chart_data,
            "topic_stats": topic_list,
            # Also return the persisted deep analysis
            "analysis_md": db.get_config("analysis_md", ""),
        }
    )


@app.route("/api/analytics/deep", methods=["GET"])
def api_get_deep_analysis():
    """Return existing deep analysis (for auto-load on tab open)."""
    return jsonify({"content": db.get_config("analysis_md", "")})


@app.route("/api/analytics/deep", methods=["POST"])
def api_deep_analyze():
    api_key = db.get_config("deepseek_api_key", "")
    if not api_key:
        return jsonify({"error": "请先在设置中配置 DeepSeek API Key"}), 400

    notes = db.list_notes()
    if not notes:
        return jsonify({"error": "暂无笔记数据"}), 400

    data = request.get_json(silent=True) or {}
    bio = db.get_config("blogger_bio", "")
    extra = data.get("extra_prompt", "")

    try:
        llm = _text_llm_settings(default_temperature=0.5, default_max_tokens=4096)
        result = deep_analyze(notes, api_key, base_url=llm["base_url"],
                              model=llm["model"], temperature=llm["temperature"],
                              max_tokens=llm["max_tokens"], bio=bio, extra=extra)
        # Persist the analysis so it survives across sessions
        db.set_config("analysis_md", result)
        return jsonify({"content": result})
    except Exception as e:
        return jsonify({"error": f"分析失败: {str(e)}"}), 500


@app.route("/api/analytics/deep", methods=["PUT"])
def api_save_deep_analysis():
    """Manually edit the persisted deep analysis."""
    data = request.get_json(force=True)
    db.set_config("analysis_md", data.get("content", ""))
    return jsonify({"ok": True})


# ═══════════════════════════════════════════════════════════
#  Content Creation API
# ═══════════════════════════════════════════════════════════

def _get_content_history():
    raw = db.get_config("content_history", "[]")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return []


def _save_content_history(history):
    db.set_config("content_history", json.dumps(history, ensure_ascii=False))


@app.route("/api/content/history", methods=["GET"])
def api_content_history():
    return jsonify({"items": _get_content_history()})


@app.route("/api/content/history/<int:index>", methods=["DELETE"])
def api_content_history_delete(index):
    history = _get_content_history()
    if 0 <= index < len(history):
        history.pop(index)
        _save_content_history(history)
        return jsonify({"ok": True})
    return jsonify({"error": "记录不存在"}), 404


@app.route("/api/content/create", methods=["POST"])
def api_create_content():
    api_key = db.get_config("deepseek_api_key", "")
    if not api_key:
        return jsonify({"error": "请先在设置中配置 DeepSeek API Key"}), 400

    data = request.get_json(force=True)
    description = data.get("description", "")
    if not description.strip():
        return jsonify({"error": "请描述你的照片/视频内容"}), 400

    profile = db.get_config("profile_md", "")
    bio = db.get_config("blogger_bio", "")
    extra = data.get("extra_prompt", "")

    try:
        llm = _text_llm_settings(default_temperature=0.75, default_max_tokens=4096)
        result = generate_content(description, api_key,
                                  profile=profile, bio=bio, extra=extra,
                                  base_url=llm["base_url"], model=llm["model"],
                                  temperature=llm["temperature"], max_tokens=llm["max_tokens"])
        if "error" in result:
            return jsonify(result), 400

        # Save to history
        history = _get_content_history()
        import datetime
        history.insert(0, {
            "id": datetime.datetime.now().strftime("%Y%m%d%H%M%S"),
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "description": description[:200],
            "style_advice": result.get("style_advice", ""),
            "body_text": result.get("body_text", ""),
        })
        # Keep at most 50 entries
        _save_content_history(history[:50])

        return jsonify(result)
    except Exception as e:
        return jsonify({"error": f"生成失败: {str(e)}"}), 500


# ═══════════════════════════════════════════════════════════
#  Chat API
# ═══════════════════════════════════════════════════════════

def _get_chat_history():
    raw = db.get_config("chat_history", "[]")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return []


def _save_chat_history(history):
    # Keep at most 200 messages
    db.set_config("chat_history", json.dumps(history[-200:], ensure_ascii=False))


@app.route("/api/chat/history", methods=["GET"])
def api_chat_history():
    return jsonify({"messages": _get_chat_history()})


@app.route("/api/chat/history", methods=["POST"])
def api_save_chat_history():
    data = request.get_json(force=True)
    messages = data.get("messages", [])
    _save_chat_history(messages)
    return jsonify({"ok": True})


@app.route("/api/chat/history", methods=["DELETE"])
def api_clear_chat_history():
    _save_chat_history([])
    return jsonify({"ok": True})


@app.route("/api/chat", methods=["POST"])
def api_chat():
    api_key = db.get_config("deepseek_api_key", "")
    if not api_key:
        return jsonify({"error": "请先在设置中配置 DeepSeek API Key"}), 400

    data = request.get_json(force=True)
    messages = data.get("messages", [])
    if not messages:
        return jsonify({"error": "消息不能为空"}), 400

    # Build context from notes & profile
    notes = db.list_notes()
    profile = db.get_config("profile_md", "")
    bio = db.get_config("blogger_bio", "")

    notes_context = ""
    if notes:
        recent = notes[:5]
        lines = []
        for n in recent:
            lines.append(f"- [{n['content_type']}] {n['title']} | 赞{n['likes']} 藏{n['saves']}")
        notes_context = "\n".join(lines)

    try:
        llm = _text_llm_settings(default_temperature=0.8, default_max_tokens=2048)
        reply = chat(api_key, messages,
                     notes_context=notes_context,
                     profile_context=profile,
                     bio=bio, base_url=llm["base_url"], model=llm["model"],
                     temperature=llm["temperature"], max_tokens=llm["max_tokens"])
        return jsonify({"reply": reply})
    except Exception as e:
        return jsonify({"error": f"对话失败: {str(e)}"}), 500



# ═══════════════════════════════════════════════════════════
#  Vision / Image Description API
# ═══════════════════════════════════════════════════════════

@app.route("/api/vision/describe", methods=["POST"])
def api_vision_describe():
    settings = _vision_settings()
    if not settings["api_key"]:
        return jsonify({"error": "请先在设置中配置图片识别 API Key"}), 400
    if not settings["base_url"]:
        return jsonify({"error": "请先在设置中配置图片识别 Base URL"}), 400
    if not settings["model"]:
        return jsonify({"error": "请先在设置中配置图片识别模型名"}), 400

    files = request.files.getlist("images")
    if not files:
        return jsonify({"error": "请先选择图片"}), 400
    if len(files) > MAX_VISION_IMAGES:
        return jsonify({"error": f"一次最多识别 {MAX_VISION_IMAGES} 张图片"}), 400

    images = []
    for file in files:
        filename = file.filename or "image"
        mime_type = file.mimetype or ""
        if not mime_type.startswith("image/"):
            return jsonify({"error": f"{filename} 不是支持的图片文件"}), 400
        content = file.read()
        if not content:
            return jsonify({"error": f"{filename} 内容为空"}), 400
        if len(content) > MAX_IMAGE_BYTES:
            return jsonify({"error": f"{filename} 超过 10MB 限制"}), 400
        try:
            content, mime_type = _compress_image_for_vision(content, mime_type)
        except ValueError as e:
            return jsonify({"error": f"{filename} {str(e)}"}), 400
        images.append({"filename": filename, "mime_type": mime_type, "bytes": content})

    prompt = (request.form.get("prompt") or settings["prompt"] or DEFAULT_VISION_PROMPT).strip()

    try:
        result = describe_images(
            images=images,
            api_key=settings["api_key"],
            base_url=settings["base_url"],
            model=settings["model"],
            prompt=prompt,
            temperature=settings["temperature"],
            max_tokens=settings["max_tokens"],
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": f"识图失败: {str(e)}"}), 500


# ═══════════════════════════════════════════════════════════
#  Settings API
# ═══════════════════════════════════════════════════════════

@app.route("/api/settings", methods=["GET"])
def api_get_settings():
    return jsonify(
        {
            "deepseek_api_key": db.get_config("deepseek_api_key", ""),
            "deepseek_base_url": db.get_config("deepseek_base_url", DEFAULT_TEXT_BASE_URL),
            "deepseek_model": db.get_config("deepseek_model", DEFAULT_TEXT_MODEL),
            "deepseek_temperature": db.get_config("deepseek_temperature", DEFAULT_TEXT_TEMPERATURE),
            "deepseek_max_tokens": db.get_config("deepseek_max_tokens", DEFAULT_TEXT_MAX_TOKENS),
            "vision_api_key": db.get_config("vision_api_key", ""),
            "vision_base_url": db.get_config("vision_base_url", ""),
            "vision_model": db.get_config("vision_model", DEFAULT_VISION_MODEL),
            "vision_temperature": db.get_config("vision_temperature", DEFAULT_VISION_TEMPERATURE),
            "vision_max_tokens": db.get_config("vision_max_tokens", DEFAULT_VISION_MAX_TOKENS),
            "vision_prompt": db.get_config("vision_prompt", DEFAULT_VISION_PROMPT),
            "blogger_bio": db.get_config("blogger_bio", ""),
        }
    )


@app.route("/api/settings", methods=["PUT"])
def api_save_settings():
    data = request.get_json(force=True)
    allowed_keys = [
        "deepseek_api_key", "deepseek_base_url", "deepseek_model",
        "deepseek_temperature", "deepseek_max_tokens",
        "vision_api_key", "vision_base_url", "vision_model",
        "vision_temperature", "vision_max_tokens", "vision_prompt",
        "blogger_bio",
    ]
    for key in allowed_keys:
        if key in data:
            db.set_config(key, str(data[key]))
    return jsonify({"ok": True})


@app.route("/api/settings/model-file", methods=["GET"])
def api_get_model_settings_file():
    settings = _model_settings_file_data()
    return jsonify({
        "filename": "model_settings.json",
        "content": json.dumps(settings, ensure_ascii=False, indent=2),
        "settings": settings,
    })


@app.route("/api/settings/model-file", methods=["PUT"])
def api_save_model_settings_file():
    data = request.get_json(force=True)
    content = data.get("content", "")
    try:
        settings = json.loads(content)
    except json.JSONDecodeError as e:
        return jsonify({"error": f"JSON 格式错误: {e.msg}"}), 400
    if not isinstance(settings, dict):
        return jsonify({"error": "JSON 根节点必须是对象"}), 400

    try:
        _apply_model_settings_file_data(settings)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    saved = _model_settings_file_data()
    return jsonify({
        "ok": True,
        "filename": "model_settings.json",
        "content": json.dumps(saved, ensure_ascii=False, indent=2),
        "settings": saved,
    })


@app.route("/api/settings/clear", methods=["POST"])
def api_clear_module():
    """Clear data for a specific module."""
    data = request.get_json(force=True)
    module = data.get("module", "")

    module_keys = {
        "profile": ["profile_md"],
        "analysis": ["analysis_md"],
        "content_history": ["content_history"],
        "chat": [],  # chat is frontend-only, no backend storage
        "all": ["profile_md", "analysis_md", "content_history"],
    }

    if module not in module_keys:
        return jsonify({"error": f"未知模块: {module}"}), 400

    for key in module_keys[module]:
        db.set_config(key, "")

    return jsonify({"ok": True, "module": module})


# ═══════════════════════════════════════════════════════════
#  Main
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("📕 小红书笔记助手启动中...")
    print(f"   打开浏览器访问 {APP_URL}")
    app.run(debug=True, host=APP_HOST, port=APP_PORT)
