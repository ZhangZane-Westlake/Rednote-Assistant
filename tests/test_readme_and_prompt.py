from pathlib import Path

import vision_client


EXPECTED_DEFAULT_VISION_PROMPT = """请作为小红书内容创作助手，详细分析这张图片，输出中文描述。

请包含：
1. 图片主体：画面中最重要的人/物/场景
2. 场景与背景：地点、环境、季节、时间感
3. 构图：近景/远景、俯拍/平拍、主体位置、画面层次
4. 色彩与光线：主色调、明暗、滤镜感、氛围
5. 风格关键词：如治愈、松弛、精致、生活感、复古、高级感等
6. 可用于小红书文案的细节：能引发共鸣或种草的具体点
7. 如果适合作为封面，请给出封面标题建议

输出格式：
图像描述：
...

小红书可用细节：
- ...
- ...

风格关键词：
#关键词1 #关键词2 #关键词3"""


def test_default_vision_prompt_matches_xiaohongshu_content_assistant_template():
    assert vision_client.DEFAULT_VISION_PROMPT == EXPECTED_DEFAULT_VISION_PROMPT


def test_readme_marks_vision_models_as_openai_compatible_first():
    readme = Path(__file__).resolve().parents[1].joinpath("README.md").read_text(encoding="utf-8")

    assert "图片识别优先支持 OpenAI 兼容视觉接口" in readme
    assert "Gemma 4 / OpenAI 兼容视觉模型" not in readme
