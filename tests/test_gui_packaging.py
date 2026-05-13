import importlib
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def test_app_gui_uses_flask_app_configured_url_and_server_kwargs(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))

    import database
    import app as app_module
    import app_gui

    importlib.reload(database)
    importlib.reload(app_module)
    app_gui = importlib.reload(app_gui)

    calls = []

    def fake_run(**kwargs):
        calls.append(kwargs)

    monkeypatch.setattr(app_gui.flask_app, "run", fake_run)

    app_gui.run_flask()

    assert calls == [
        {
            "host": "127.0.0.1",
            "port": app_module.APP_PORT,
            "debug": False,
            "use_reloader": False,
            "threaded": True,
        }
    ]
    assert app_gui.APP_URL == f"http://127.0.0.1:{app_module.APP_PORT}"


def test_build_script_copies_vision_client_for_packaged_app():
    build_script = (PROJECT_ROOT / "mac" / "build.sh").read_text(encoding="utf-8")
    assert 'cp "$PROJECT_DIR/vision_client.py" "$APP_BUNDLE/Contents/Resources/"' in build_script
