import importlib
import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture()
def app_modules(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    import database
    import app as app_module

    database = importlib.reload(database)
    app_module = importlib.reload(app_module)
    app_module.app.config.update(TESTING=True)
    return app_module, database


@pytest.fixture()
def client(app_modules):
    app_module, _ = app_modules
    with app_module.app.test_client() as c:
        yield c


def test_model_settings_file_endpoint_returns_editable_json(client):
    resp = client.get("/api/settings/model-file")

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["filename"] == "model_settings.json"
    assert "deepseek" in data["content"]
    assert "vision" in data["content"]
    assert data["settings"]["deepseek"]["model"] == "deepseek-chat"
    assert data["settings"]["vision"]["model"] == "gemma-4"


def test_model_settings_file_endpoint_saves_json_and_updates_runtime_settings(client, app_modules):
    _, database = app_modules
    content = """{
  "deepseek": {
    "api_key": "sk-text",
    "base_url": "https://text.example/v1",
    "model": "deepseek-reasoner",
    "temperature": 0.3,
    "max_tokens": 1234
  },
  "vision": {
    "api_key": "sk-vision",
    "base_url": "https://vision.example/v1",
    "model": "gemma-4-test",
    "temperature": 0.1,
    "max_tokens": 567,
    "prompt": "请描述图片"
  }
}
"""

    resp = client.put("/api/settings/model-file", json={"content": content})

    assert resp.status_code == 200
    assert resp.get_json()["ok"] is True
    assert database.get_config("deepseek_api_key", "") == "sk-text"
    assert database.get_config("deepseek_base_url", "") == "https://text.example/v1"
    assert database.get_config("deepseek_model", "") == "deepseek-reasoner"
    assert database.get_config("deepseek_temperature", "") == "0.3"
    assert database.get_config("deepseek_max_tokens", "") == "1234"
    assert database.get_config("vision_api_key", "") == "sk-vision"
    assert database.get_config("vision_base_url", "") == "https://vision.example/v1"
    assert database.get_config("vision_model", "") == "gemma-4-test"
    assert database.get_config("vision_temperature", "") == "0.1"
    assert database.get_config("vision_max_tokens", "") == "567"
    assert database.get_config("vision_prompt", "") == "请描述图片"


def test_model_settings_file_endpoint_rejects_invalid_json(client):
    resp = client.put("/api/settings/model-file", json={"content": "{not json"})

    assert resp.status_code == 400
    assert "JSON" in resp.get_json()["error"]
