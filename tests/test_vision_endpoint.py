import importlib
import io
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


def test_vision_describe_requires_config(client):
    resp = client.post(
        "/api/vision/describe",
        data={"images": (io.BytesIO(b"fake"), "test.jpg")},
        content_type="multipart/form-data",
    )

    assert resp.status_code == 400
    assert "图片识别 API Key" in resp.get_json()["error"]


def test_vision_describe_endpoint_returns_combined_description(client, app_modules, monkeypatch):
    app_module, database = app_modules
    database.set_config("vision_api_key", "sk-vision")
    database.set_config("vision_base_url", "https://vision.example/v1")
    database.set_config("vision_model", "gemma-4-test")
    database.set_config("vision_temperature", "0.1")
    database.set_config("vision_max_tokens", "200")
    database.set_config("vision_prompt", "默认提示")

    captured = {}

    def fake_describe_images(**kwargs):
        captured.update(kwargs)
        return {
            "descriptions": [{"filename": "test.jpg", "description": "图像描述"}],
            "combined": "图1（test.jpg）：\n图像描述",
        }

    monkeypatch.setattr(app_module, "describe_images", fake_describe_images)

    resp = client.post(
        "/api/vision/describe",
        data={"images": (io.BytesIO(b"fake-jpeg"), "test.jpg")},
        content_type="multipart/form-data",
    )

    assert resp.status_code == 200
    assert resp.get_json()["combined"] == "图1（test.jpg）：\n图像描述"
    assert captured["api_key"] == "sk-vision"
    assert captured["base_url"] == "https://vision.example/v1"
    assert captured["model"] == "gemma-4-test"
    assert captured["prompt"] == "默认提示"
    assert captured["temperature"] == 0.1
    assert captured["max_tokens"] == 200
    assert captured["images"][0]["filename"] == "test.jpg"
    assert captured["images"][0]["bytes"] == b"fake-jpeg"
