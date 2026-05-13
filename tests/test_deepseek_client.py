from types import SimpleNamespace

import deepseek_client


class FakeCompletions:
    def __init__(self):
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="风格建议\n===正文===\n正文"))]
        )


class FakeClient:
    instances = []

    def __init__(self, api_key, base_url):
        self.api_key = api_key
        self.base_url = base_url
        self.chat = SimpleNamespace(completions=FakeCompletions())
        FakeClient.instances.append(self)


def test_generate_content_uses_custom_text_model_settings(monkeypatch):
    FakeClient.instances = []
    monkeypatch.setattr(deepseek_client, "OpenAI", FakeClient)

    result = deepseek_client.generate_content(
        "一张咖啡照片",
        "sk-test",
        base_url="https://proxy.example/v1",
        model="custom-model",
        temperature=0.42,
        max_tokens=321,
    )

    assert result["body_text"] == "正文"
    client = FakeClient.instances[0]
    assert client.api_key == "sk-test"
    assert client.base_url == "https://proxy.example/v1"
    call = client.chat.completions.calls[0]
    assert call["model"] == "custom-model"
    assert call["temperature"] == 0.42
    assert call["max_tokens"] == 321
