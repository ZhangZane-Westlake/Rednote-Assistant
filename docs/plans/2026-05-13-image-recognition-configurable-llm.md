# Image Recognition and Configurable LLM Implementation Plan

> **For Hermes:** Implement directly in this repository with tests and manual debug verification before pushing.

**Goal:** Add image recognition for user-uploaded images through an OpenAI-compatible Gemma/Vision model, and make both text LLM and vision model settings configurable from the app settings page.

**Architecture:** Keep the current Flask + SQLite key/value config design. Add a small `vision_client.py` for OpenAI-compatible vision chat completions. Extend `deepseek_client.py` to accept base URL, model, temperature, and max token settings instead of hardcoding them. Frontend uploads images to a new backend endpoint and appends generated descriptions into existing textareas.

**Tech Stack:** Python Flask, SQLite config table, OpenAI Python SDK, vanilla JavaScript, HTML/CSS.

---

### Task 1: Add backend tests for settings and model config

**Objective:** Ensure `/api/settings` returns defaults and saves both text and vision model settings.

**Files:**
- Create: `tests/test_settings.py`
- Use: `app.py`, `database.py`

**Steps:**
1. Add pytest-based Flask client tests with isolated `HOME` using `tmp_path` and module reload.
2. Verify GET `/api/settings` includes defaults for:
   - `deepseek_base_url`
   - `deepseek_model`
   - `deepseek_temperature`
   - `deepseek_max_tokens`
   - `vision_base_url`
   - `vision_model`
   - `vision_temperature`
   - `vision_max_tokens`
   - `vision_prompt`
3. Verify PUT `/api/settings` persists those fields.
4. Run targeted tests and confirm they fail before implementation.

### Task 2: Add tests for text client configurability

**Objective:** Prove text LLM helper functions pass user-configured base URL/model/temperature/max_tokens into OpenAI SDK calls.

**Files:**
- Create: `tests/test_deepseek_client.py`
- Modify: `deepseek_client.py`

**Steps:**
1. Mock `deepseek_client.OpenAI` with a fake client.
2. Call `generate_content()` or `chat()` with custom `base_url`, `model`, `temperature`, `max_tokens`.
3. Assert the fake client receives the custom base URL and model params.
4. Run the test and confirm RED.
5. Implement minimal changes in `deepseek_client.py`.

### Task 3: Add Vision client tests

**Objective:** Prove image bytes are converted to data URLs and sent in OpenAI-compatible vision message format.

**Files:**
- Create: `tests/test_vision_client.py`
- Create: `vision_client.py`

**Steps:**
1. Mock `vision_client.OpenAI`.
2. Call `describe_image()` with fake JPEG bytes and settings.
3. Assert `messages[1].content` contains text plus `image_url.url` beginning with `data:image/jpeg;base64,`.
4. Assert custom model/base_url/temperature/max_tokens are passed through.
5. Run RED, then implement `vision_client.py`.

### Task 4: Add backend image describe endpoint

**Objective:** Let the frontend POST one or more images and receive combined descriptions.

**Files:**
- Modify: `app.py`
- Test: `tests/test_vision_endpoint.py`

**Steps:**
1. Add `/api/vision/describe` accepting `multipart/form-data` with `images` files and optional `prompt`.
2. Add config validation errors for missing `vision_api_key`, `vision_base_url`, and `vision_model`.
3. Enforce image count and size limits.
4. Call `vision_client.describe_images()` and return `descriptions` plus `combined`.
5. Add tests for missing config and happy path using monkeypatch.

### Task 5: Update settings UI

**Objective:** Allow users to configure both DeepSeek/text LLM and Gemma/Vision advanced settings.

**Files:**
- Modify: `templates/index.html`
- Modify: `static/app.js`

**Steps:**
1. Replace readonly DeepSeek base URL with editable input.
2. Add fields for text model name, temperature, max tokens.
3. Add a new image recognition/Gemma card with base URL, API key, model, temperature, max tokens, default prompt.
4. Update `loadSettings()` and save handler to read/write all fields.

### Task 6: Add upload-and-describe UI in Notes and Content Creation

**Objective:** Let users upload images and auto-fill image/material descriptions.

**Files:**
- Modify: `templates/index.html`
- Modify: `static/app.js`
- Modify: `static/style.css`

**Steps:**
1. Add image file input and button near the note image description textarea.
2. Add image file input and button near the content creation description textarea.
3. Add JS helper to build `FormData`, call `/api/vision/describe`, and append result to the target textarea.
4. Show loading state and toast errors.
5. Keep selected images local only; do not persist files.

### Task 7: Debug and verify

**Objective:** Confirm tests, syntax, and app startup work.

**Commands:**
- `python3 -m pytest -q`
- `python3 -m py_compile app.py deepseek_client.py vision_client.py database.py`
- Start Flask app and smoke-test `/api/settings` and `/api/vision/describe` validation.

### Task 8: Commit and push

**Objective:** Upload final changes to GitHub.

**Commands:**
- `git status --short`
- `git diff --check`
- `git add ...`
- `git commit -m "feat: add configurable vision image descriptions"`
- `git push origin main`
