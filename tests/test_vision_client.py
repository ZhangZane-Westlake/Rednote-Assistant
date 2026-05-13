from types import SimpleNamespace

import vision_client


class FakeCompletions:
    def __init__(self):
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="图像描述：一杯咖啡"))]
        )


class FakeClient:
    instances = []

    def __init__(self, api_key, base_url):
        self.api_key = api_key
        self.base_url = base_url
        self.chat = SimpleNamespace(completions=FakeCompletions())
        FakeClient.instances.append(self)


def test_describe_image_sends_openai_compatible_image_url(monkeypatch):
    FakeClient.instances = []
    monkeypatch.setattr(vision_client, "OpenAI", FakeClient)

    description = vision_client.describe_image(
        image_bytes=b"\xff\xd8\xfffakejpeg",
        mime_type="image/jpeg",
        api_key="sk-vision",
        base_url="https://vision.example/v1",
        model="gemma-4-test",
        prompt="请描述",
        temperature=0.12,
        max_tokens=456,
    )

    assert description == "图像描述：一杯咖啡"
    client = FakeClient.instances[0]
    assert client.api_key == "sk-vision"
    assert client.base_url == "https://vision.example/v1"
    call = client.chat.completions.calls[0]
    assert call["model"] == "gemma-4-test"
    assert call["temperature"] == 0.12
    assert call["max_tokens"] == 456
    content = call["messages"][1]["content"]
    assert content[0] == {"type": "text", "text": "请描述"}
    assert content[1]["type"] == "image_url"
    assert content[1]["image_url"]["url"].startswith("data:image/jpeg;base64,")


def test_describe_images_combines_numbered_results(monkeypatch):
    monkeypatch.setattr(vision_client, "describe_image", lambda **kwargs: f"描述{kwargs['filename']}")

    result = vision_client.describe_images(
        images=[
            {"filename": "a.jpg", "bytes": b"a", "mime_type": "image/jpeg"},
            {"filename": "b.png", "bytes": b"b", "mime_type": "image/png"},
        ],
        api_key="k",
        base_url="u",
        model="m",
        prompt="p",
        temperature=0.1,
        max_tokens=100,
    )

    assert result["descriptions"] == [
        {"filename": "a.jpg", "description": "描述a.jpg"},
        {"filename": "b.png", "description": "描述b.png"},
    ]
    assert result["combined"] == "图1（a.jpg）：\n描述a.jpg\n\n图2（b.png）：\n描述b.png"
