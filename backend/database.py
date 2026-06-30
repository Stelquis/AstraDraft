"""
v1.0 SQLite 数据库层 — 图纸管理 + 查询历史。

三张核心表:
  drawings       — 上传图纸的元数据 + 参数索引 JSON
  query_history  — 所有用户的问答记录（公开可查）
"""
import json
import sqlite3
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

DB_PATH = Path("data/deepastradraft.db")


def get_db() -> sqlite3.Connection:
    """获取数据库连接（自动建表，WAL 模式并发优化）"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    _create_tables(conn)
    return conn


def _create_tables(conn: sqlite3.Connection):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS drawings (
            id          TEXT PRIMARY KEY,
            filename    TEXT NOT NULL,
            file_path   TEXT NOT NULL,
            file_size   INTEGER DEFAULT 0,
            status      TEXT DEFAULT 'pending',
            param_count INTEGER DEFAULT 0,
            index_json  TEXT DEFAULT '',
            created_at  TEXT DEFAULT (datetime('now')),
            updated_at  TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS query_history (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            drawing_id  TEXT NOT NULL REFERENCES drawings(id),
            question    TEXT NOT NULL,
            answer      TEXT NOT NULL,
            source      TEXT DEFAULT 'rule',
            session_id  TEXT DEFAULT '',
            created_at  TEXT DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_query_drawing
            ON query_history(drawing_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_drawings_status
            ON drawings(status);
    """)


# ---- 图纸管理 ----

def add_drawing(filename: str, file_path: str, file_size: int = 0) -> str:
    """注册新上传的图纸，返回 drawing_id"""
    drawing_id = uuid.uuid4().hex[:12]
    conn = get_db()
    conn.execute(
        "INSERT INTO drawings (id, filename, file_path, file_size) VALUES (?,?,?,?)",
        (drawing_id, filename, file_path, file_size),
    )
    conn.commit()
    return drawing_id


def update_drawing(drawing_id: str, status: str = "",
                   param_count: int = -1, index_json: str = ""):
    """更新图纸状态/参数"""
    conn = get_db()
    fields = []
    values = []
    if status:
        fields.append("status=?")
        values.append(status)
    if param_count >= 0:
        fields.append("param_count=?")
        values.append(param_count)
    if index_json:
        fields.append("index_json=?")
        values.append(index_json)
    if fields:
        fields.append("updated_at=datetime('now')")
        values.append(drawing_id)
        conn.execute(f"UPDATE drawings SET {', '.join(fields)} WHERE id=?", values)
        conn.commit()


def get_drawing(drawing_id: str) -> Optional[Dict[str, Any]]:
    conn = get_db()
    row = conn.execute("SELECT * FROM drawings WHERE id=?", (drawing_id,)).fetchone()
    return dict(row) if row else None


def list_drawings(status: str = "ready", limit: int = 50) -> List[Dict[str, Any]]:
    conn = get_db()
    rows = conn.execute(
        "SELECT id, filename, file_size, status, param_count, created_at"
        " FROM drawings WHERE status=? ORDER BY created_at DESC LIMIT ?",
        (status, limit),
    ).fetchall()
    return [dict(r) for r in rows]


# ---- 查询历史 ----

def add_query(drawing_id: str, question: str, answer: str,
              source: str = "rule", session_id: str = "") -> int:
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO query_history (drawing_id, question, answer, source, session_id)"
        " VALUES (?,?,?,?,?)",
        (drawing_id, question, answer, source, session_id),
    )
    conn.commit()
    return cur.lastrowid


def get_query_history(drawing_id: str, limit: int = 100) -> List[Dict[str, Any]]:
    conn = get_db()
    rows = conn.execute(
        "SELECT question, answer, source, created_at FROM query_history"
        " WHERE drawing_id=? ORDER BY created_at DESC LIMIT ?",
        (drawing_id, limit),
    ).fetchall()
    return [dict(r) for r in rows]
