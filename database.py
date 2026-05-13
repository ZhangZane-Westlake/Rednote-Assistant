"""SQLite database layer for XHS Assistant — multi-account support.

Architecture:
  ~/.xhs-assistant/
    master.db           ← Account list + current account pointer
    accounts/
      <uuid>/
        notes.db        ← Per-account: notes + config tables
"""

import os
import uuid
import sqlite3
import datetime
from pathlib import Path

DATA_DIR = Path.home() / ".xhs-assistant"
MASTER_DB = DATA_DIR / "master.db"

# ── Current account cache ──────────────────────────────────
_current_account_id = None


def _get_master_db():
    conn = sqlite3.connect(str(MASTER_DB))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _init_master():
    """Ensure master DB exists with accounts + config tables."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = _get_master_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)
    conn.commit()

    # Migrate: if no accounts exist, create "默认账号" and
    # if old notes.db exists at DATA_DIR root, rename it
    count = conn.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]
    if count == 0:
        old_db = DATA_DIR / "notes.db"
        account_id = str(uuid.uuid4())[:8]
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

        # Create account
        conn.execute(
            "INSERT INTO accounts (id, name, created_at) VALUES (?, ?, ?)",
            (account_id, "默认账号", now),
        )
        conn.execute(
            "INSERT INTO config (key, value) VALUES (?, ?)",
            ("current_account", account_id),
        )
        conn.commit()

        # Migrate old DB if it exists
        if old_db.exists():
            account_dir = DATA_DIR / "accounts" / account_id
            account_dir.mkdir(parents=True, exist_ok=True)
            old_db.rename(account_dir / "notes.db")

    conn.close()


def _account_db_path(account_id: str) -> Path:
    return DATA_DIR / "accounts" / account_id / "notes.db"


# ── Account management ─────────────────────────────────────

def list_accounts() -> list[dict]:
    conn = _get_master_db()
    rows = conn.execute("SELECT * FROM accounts ORDER BY created_at").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_current_account_id() -> str:
    global _current_account_id
    if _current_account_id:
        return _current_account_id
    conn = _get_master_db()
    row = conn.execute("SELECT value FROM config WHERE key='current_account'").fetchone()
    conn.close()
    _current_account_id = row["value"] if row else ""
    return _current_account_id


def set_current_account(account_id: str):
    global _current_account_id
    conn = _get_master_db()
    # Verify account exists
    row = conn.execute("SELECT id FROM accounts WHERE id=?", (account_id,)).fetchone()
    if not row:
        conn.close()
        raise ValueError(f"账号不存在: {account_id}")
    conn.execute(
        "INSERT INTO config (key, value) VALUES ('current_account', ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (account_id,),
    )
    conn.commit()
    conn.close()
    _current_account_id = account_id


def add_account(name: str) -> dict:
    account_id = str(uuid.uuid4())[:8]
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    conn = _get_master_db()
    conn.execute(
        "INSERT INTO accounts (id, name, created_at) VALUES (?, ?, ?)",
        (account_id, name, now),
    )
    conn.commit()
    conn.close()

    # Create the per-account DB
    account_dir = DATA_DIR / "accounts" / account_id
    account_dir.mkdir(parents=True, exist_ok=True)
    _init_account_db(account_id)

    return {"id": account_id, "name": name, "created_at": now}


def delete_account(account_id: str):
    conn = _get_master_db()
    conn.execute("DELETE FROM accounts WHERE id=?", (account_id,))
    conn.commit()

    # If this was current, switch to another account or clear
    current = get_current_account_id()
    if current == account_id:
        remaining = conn.execute("SELECT id FROM accounts ORDER BY created_at LIMIT 1").fetchone()
        if remaining:
            set_current_account(remaining["id"])
        else:
            conn.execute("DELETE FROM config WHERE key='current_account'")
            conn.commit()
            global _current_account_id
            _current_account_id = ""

    conn.close()

    # Delete account directory
    import shutil
    account_dir = DATA_DIR / "accounts" / account_id
    if account_dir.exists():
        shutil.rmtree(account_dir)


def rename_account(account_id: str, new_name: str):
    conn = _get_master_db()
    conn.execute("UPDATE accounts SET name=? WHERE id=?", (new_name, account_id))
    conn.commit()
    conn.close()


# ── Per-account DB ─────────────────────────────────────────

def _init_account_db(account_id: str):
    """Create tables in the account's own DB."""
    db_path = _account_db_path(account_id)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            text_content TEXT NOT NULL DEFAULT '',
            image_description TEXT NOT NULL DEFAULT '',
            topics TEXT NOT NULL DEFAULT '',
            content_type TEXT NOT NULL DEFAULT 'photo',
            publish_date TEXT NOT NULL DEFAULT '',
            views INTEGER NOT NULL DEFAULT 0,
            likes INTEGER NOT NULL DEFAULT 0,
            saves INTEGER NOT NULL DEFAULT 0,
            comments INTEGER NOT NULL DEFAULT 0,
            shares INTEGER NOT NULL DEFAULT 0,
            notes TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def get_db(account_id: str = None):
    """Get a connection to the current account's DB."""
    if account_id is None:
        account_id = get_current_account_id()
    if not account_id:
        raise RuntimeError("没有选择账号")
    db_path = _account_db_path(account_id)
    # Ensure DB exists
    if not db_path.exists():
        _init_account_db(account_id)
    conn = sqlite3.connect(str(db_path), detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """Initialize master + current account. Called once at startup."""
    _init_master()
    account_id = get_current_account_id()
    if account_id:
        _init_account_db(account_id)


# ── Notes CRUD (unchanged API, routes to current account) ──

def list_notes():
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM notes ORDER BY publish_date DESC, id DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_note(note_id: int):
    conn = get_db()
    row = conn.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def create_note(data: dict):
    conn = get_db()
    cur = conn.execute(
        """INSERT INTO notes
           (title, text_content, image_description, topics, content_type,
            publish_date, views, likes, saves, comments, shares, notes)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            data.get("title", ""),
            data.get("text_content", ""),
            data.get("image_description", ""),
            data.get("topics", ""),
            data.get("content_type", "photo"),
            data.get("publish_date", ""),
            int(data.get("views", 0)),
            int(data.get("likes", 0)),
            int(data.get("saves", 0)),
            int(data.get("comments", 0)),
            int(data.get("shares", 0)),
            data.get("notes", ""),
        ),
    )
    conn.commit()
    note_id = cur.lastrowid
    conn.close()
    return get_note(note_id)


def update_note(note_id: int, data: dict):
    conn = get_db()
    fields = [
        "title", "text_content", "image_description", "topics", "content_type",
        "publish_date", "views", "likes", "saves", "comments", "shares", "notes",
    ]
    sets = [f"{f} = ?" for f in fields if f in data]
    vals = [data[f] for f in fields if f in data]
    if not sets:
        conn.close()
        return get_note(note_id)
    vals.append(note_id)
    conn.execute(f"UPDATE notes SET {', '.join(sets)} WHERE id = ?", vals)
    conn.commit()
    conn.close()
    return get_note(note_id)


def delete_note(note_id: int):
    conn = get_db()
    conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
    conn.commit()
    conn.close()


# ── Config (per-account) ───────────────────────────────────

def get_config(key: str, default=""):
    conn = get_db()
    row = conn.execute("SELECT value FROM config WHERE key = ?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else default


def set_config(key: str, value: str):
    conn = get_db()
    conn.execute(
        "INSERT INTO config (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )
    conn.commit()
    conn.close()
