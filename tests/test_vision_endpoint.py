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


def configure_vision(database):
    database.set_config("vision_api_key", "sk-vision")
    database.set_config("vision_base_url", "https://vision.example/v1")
    database.set_config("vision_model", "gemma-4-test")


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
    configure_vision(database)
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


def test_vision_describe_endpoint_accepts_multiple_images(client, app_modules, monkeypatch):
    app_module, database = app_modules
    configure_vision(database)

    captured = {}

    def fake_describe_images(**kwargs):
        captured.update(kwargs)
        return {
            "descriptions": [
                {"filename": "one.jpg", "description": "第一张"},
                {"filename": "two.png", "description": "第二张"},
            ],
            "combined": "图1（one.jpg）：\n第一张\n\n图2（two.png）：\n第二张",
        }

    monkeypatch.setattr(app_module, "describe_images", fake_describe_images)

    resp = client.post(
        "/api/vision/describe",
        data={
            "images": [
                (io.BytesIO(b"fake-jpeg-1"), "one.jpg"),
                (io.BytesIO(b"fake-png-2"), "two.png"),
            ]
        },
        content_type="multipart/form-data",
    )

    assert resp.status_code == 200
    assert resp.get_json()["combined"] == "图1（one.jpg）：\n第一张\n\n图2（two.png）：\n第二张"
    assert [image["filename"] for image in captured["images"]] == ["one.jpg", "two.png"]
    assert [image["bytes"] for image in captured["images"]] == [b"fake-jpeg-1", b"fake-png-2"]


def test_vision_describe_rejects_more_than_max_images(client, app_modules):
    app_module, database = app_modules
    configure_vision(database)

    resp = client.post(
        "/api/vision/describe",
        data={
            "images": [
                (io.BytesIO(f"fake-{idx}".encode()), f"{idx}.jpg")
                for idx in range(app_module.MAX_VISION_IMAGES + 1)
            ]
        },
        content_type="multipart/form-data",
    )

    assert resp.status_code == 400
    assert f"一次最多识别 {app_module.MAX_VISION_IMAGES} 张图片" in resp.get_json()["error"]


def test_vision_describe_compresses_large_images_before_describing(client, app_modules, monkeypatch):
    app_module, database = app_modules
    configure_vision(database)

    from PIL import Image

    source = io.BytesIO()
    image = Image.effect_noise((1800, 1800), 100).convert("RGB")
    image.save(source, format="PNG")
    uploaded = source.getvalue()
    assert len(uploaded) > app_module.TARGET_VISION_IMAGE_BYTES

    captured = {}

    def fake_describe_images(**kwargs):
        captured.update(kwargs)
        return {"descriptions": [], "combined": "压缩后描述"}

    monkeypatch.setattr(app_module, "describe_images", fake_describe_images)

    resp = client.post(
        "/api/vision/describe",
        data={"images": (io.BytesIO(uploaded), "huge.png", "image/png")},
        content_type="multipart/form-data",
    )

    assert resp.status_code == 200
    image = captured["images"][0]
    assert image["filename"] == "huge.png"
    assert image["mime_type"] == "image/jpeg"
    assert len(image["bytes"]) <= app_module.TARGET_VISION_IMAGE_BYTES
    assert len(image["bytes"]) < len(uploaded)


def test_vision_describe_keeps_small_images_unchanged(client, app_modules, monkeypatch):
    app_module, database = app_modules
    configure_vision(database)

    captured = {}

    def fake_describe_images(**kwargs):
        captured.update(kwargs)
        return {"descriptions": [], "combined": "原图描述"}

    monkeypatch.setattr(app_module, "describe_images", fake_describe_images)
    uploaded = b"small-jpeg"

    resp = client.post(
        "/api/vision/describe",
        data={"images": (io.BytesIO(uploaded), "small.jpg")},
        content_type="multipart/form-data",
    )

    assert resp.status_code == 200
    assert captured["images"][0]["mime_type"] == "image/jpeg"
    assert captured["images"][0]["bytes"] == uploaded
