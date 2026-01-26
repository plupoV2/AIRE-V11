from __future__ import annotations
from typing import Any, Dict, List, Optional
import json

from db import exec_commit, fetchall, fetchone, now

def migrate():
    exec_commit("""
    CREATE TABLE IF NOT EXISTS audit_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        workspace_id INTEGER NOT NULL,
        actor_user_id INTEGER NOT NULL,
        event_type TEXT NOT NULL,
        created_at TEXT NOT NULL,
        payload_json TEXT NOT NULL
    );
    """)
    exec_commit("CREATE INDEX IF NOT EXISTS idx_audit_ws_time ON audit_events(workspace_id, created_at DESC);")

def log_event(workspace_id: int, actor_user_id: int, event_type: str, payload: Dict[str, Any]) -> int:
    migrate()
    payload_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    exec_commit(
        "INSERT INTO audit_events(workspace_id, actor_user_id, event_type, created_at, payload_json) VALUES (?,?,?,?,?)",
        (int(workspace_id), int(actor_user_id), str(event_type), now(), payload_json),
    )
    row = fetchone("SELECT last_insert_rowid()")
    return int(row[0]) if row else 0

def list_events(workspace_id: int, limit: int = 200) -> List[Dict[str, Any]]:
    migrate()
    rows = fetchall(
        "SELECT id, created_at, actor_user_id, event_type, payload_json FROM audit_events WHERE workspace_id=? ORDER BY created_at DESC LIMIT ?",
        (int(workspace_id), int(limit)),
    )
    out: List[Dict[str, Any]] = []
    for r in rows:
        try:
            payload = json.loads(r[4]) if r[4] else {}
        except Exception:
            payload = {}
        out.append({
            "id": r[0],
            "created_at": r[1],
            "actor_user_id": r[2],
            "event_type": r[3],
            "payload": payload,
        })
    return out
