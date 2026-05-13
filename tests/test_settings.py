import importlib
import os
import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    import database
    import app as app_module

    database = importlib.reload(database)
    app_module = importlib.reload(app_module)
    app_module.app.config.update(TESTING=True)
    with app_module.app.test_client() as c:
        yield c


def test_settings_returns_model_defaults(client):
    resp = client.get("/api/settings")
    assert resp.status_code == 200
    data = resp.get_json()

    assert data["deepseek_api_key"] == ""
    assert data["deepseek_base_url"] == "https://api.deepseek.com/v1"
    assert data["deepseek_model"] == "deepseek-chat"
    assert data["deepseek_temperature"] == "0.7"
    assert data["deepseek_max_tokens"] == "4096"

    assert data["vision_api_key"] == ""
    assert data["vision_base_url"] == ""
    assert data["vision_model"] == "gemma-4"
    assert data["vision_temperature"] == "0.2"
    assert data["vision_max_tokens"] == "2048"
    assert "小红书" in data["vision_prompt"]


def test_settings_saves_text_and_vision_model_config(client):
    payload = {
        "deepseek_api_key": "sk-text",
        "deepseek_base_url": "https://text.example/v1",
        "deepseek_model": "custom-text-model",
        "deepseek_temperature": "0.33",
        "deepseek_max_tokens": "1234",
        "vision_api_key": "sk-vision",
        "vision_base_url": "https://vision.example/v1",
        "vision_model": "gemma-4-test",
        "vision_temperature": "0.11",
        "vision_max_tokens": "567",
        "vision_prompt": "请描述图片",
        "blogger_bio": "测试博主",
    }

    resp = client.put("/api/settings", json=payload)
    assert resp.status_code == 200
    assert resp.get_json() == {"ok": True}

    saved = client.get("/api/settings").get_json()
    for key, value in payload.items():
        assert saved[key] == value
