import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def test_file_inputs_use_chinese_selection_guidance():
    html = (PROJECT_ROOT / "templates" / "index.html").read_text(encoding="utf-8")

    assert "choose file" not in html.lower()
    assert 'id="note-image-files"' in html
    assert 'id="content-image-files"' in html
    assert 'for="note-image-files"' in html
    assert 'for="content-image-files"' in html
    assert "选择图片" in html
    assert "未选择图片" in html


def test_frontend_updates_chinese_file_selection_text():
    js = (PROJECT_ROOT / "static" / "app.js").read_text(encoding="utf-8")

    assert "updateImageFileLabel" in js
    assert "未选择图片" in js
    assert "已选择" in js
    assert "张图片" in js
