"""OpenAI-compatible vision client for image descriptions."""

import base64
from openai import OpenAI


DEFAULT_VISION_PROMPT = """请作为小红书内容创作助手，详细分析这张图片，输出中文描述，尽量简洁。

请包含：
1. 图片主体：画面中最重要的人/物/场景
2. 场景与背景：地点、环境、季节、时间感
3. 构图：近景/远景、俯拍/平拍、主体位置、画面层次
4. 色彩与光线：主色调、明暗、滤镜感、氛围

输出格式：
图像描述：
..."""


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


def describe_image(
    image_bytes: bytes,
    mime_type: str,
    api_key: str,
    base_url: str,
    model: str,
    prompt: str = DEFAULT_VISION_PROMPT,
    temperature=0.2,
    max_tokens=2048,
    filename: str = "",
) -> str:
    """Describe one image using an OpenAI-compatible vision model."""
    if not image_bytes:
        raise ValueError("图片内容为空")
    if not api_key:
        raise ValueError("请先在设置中配置图片识别 API Key")
    if not base_url:
        raise ValueError("请先在设置中配置图片识别 Base URL")
    if not model:
        raise ValueError("请先在设置中配置图片识别模型名")

    mime_type = mime_type or "image/jpeg"
    prompt = (prompt or DEFAULT_VISION_PROMPT).strip()
    if filename:
        prompt = f"文件名：{filename}\n\n{prompt}"

    data_url = "data:{};base64,{}".format(
        mime_type,
        base64.b64encode(image_bytes).decode("ascii"),
    )

    client = OpenAI(api_key=api_key, base_url=base_url)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "你是专业的小红书图片分析和内容创作助手。"},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            },
        ],
        temperature=_float(temperature, 0.2),
        max_tokens=_int(max_tokens, 2048),
    )
    return response.choices[0].message.content.strip()


def describe_images(
    images: list[dict],
    api_key: str,
    base_url: str,
    model: str,
    prompt: str = DEFAULT_VISION_PROMPT,
    temperature=0.2,
    max_tokens=2048,
) -> dict:
    """Describe multiple images and return per-file and combined text."""
    descriptions = []
    combined_parts = []
    for idx, image in enumerate(images, 1):
        filename = image.get("filename") or f"image-{idx}"
        description = describe_image(
            image_bytes=image.get("bytes", b""),
            mime_type=image.get("mime_type", "image/jpeg"),
            api_key=api_key,
            base_url=base_url,
            model=model,
            prompt=prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            filename=filename,
        )
        descriptions.append({"filename": filename, "description": description})
        combined_parts.append(f"图{idx}（{filename}）：\n{description}")

    return {"descriptions": descriptions, "combined": "\n\n".join(combined_parts)}
