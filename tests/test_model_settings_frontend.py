import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def test_settings_page_has_model_settings_file_editor_controls():
    html = (PROJECT_ROOT / "templates" / "index.html").read_text(encoding="utf-8")

    assert 'id="btn-edit-model-settings"' in html
    assert 'id="model-settings-editor"' in html
    assert 'id="model-settings-file-content"' in html
    assert "编辑模型调用 setting 文件" in html
    assert "保存 setting 文件" in html


def test_frontend_loads_and_saves_model_settings_file():
    js = (PROJECT_ROOT / "static" / "app.js").read_text(encoding="utf-8")

    assert "loadModelSettingsFile" in js
    assert "saveModelSettingsFile" in js
    assert "/api/settings/model-file" in js
