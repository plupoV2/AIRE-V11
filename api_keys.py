import time
from db import backend, connect, exec_commit, fetchall, fetchone, insert_returning_id
import secrets
import hashlib
from typing import List, Dict, Any, Optional

def now() -> int:
    return int(time.time())

def migrate() -> None:
    conn = connect()
    b = backend()
    cur = conn.cursor() if b == "postgres" else conn
    cur.execute("""CREATE TABLE IF NOT EXISTS api_keys(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at INTEGER NOT NULL,
        name TEXT NOT NULL,
        key_hash TEXT NOT NULL,
        last4 TEXT NOT NULL,
        workspace_id INTEGER NOT NULL,
        created_by INTEGER NOT NULL,
        revoked INTEGER NOT NULL DEFAULT 0
    )""" if b == "sqlite" else """CREATE TABLE IF NOT EXISTS api_keys(
        id BIGSERIAL PRIMARY KEY,
        created_at BIGINT NOT NULL,
        name TEXT NOT NULL,
        key_hash TEXT NOT NULL,
        last4 TEXT NOT NULL,
        workspace_id BIGINT NOT NULL,
        created_by BIGINT NOT NULL,
        revoked INTEGER NOT NULL DEFAULT 0
    )""")
    conn.commit()
    try: conn.close()
    except Exception: pass

def _hash(k: str) -> str:
    return hashlib.sha256(k.encode("utf-8")).hexdigest()

def create_key(workspace_id: int, label: str) -> Dict[str, str]:
    migrate()
    raw = "aire_" + secrets.token_urlsafe(24)
    prefix = raw[:12]
    conn = _db()
    conn.execute("INSERT INTO api_keys(created_at, workspace_id, label, key_prefix, key_hash) VALUES(?,?,?,?,?)",
                 (now(), int(workspace_id), label.strip()[:64], prefix, _hash(raw)))
    conn.commit()
    return {"api_key": raw, "prefix": prefix}

def list_keys(workspace_id: int) -> List[Dict[str, Any]]:
    migrate()
    conn = _db()
    cur = conn.execute("SELECT id, created_at, label, key_prefix, revoked_at FROM api_keys WHERE workspace_id=? ORDER BY created_at DESC",
                       (int(workspace_id),))
    return [{"id": r[0], "created_at": r[1], "label": r[2], "prefix": r[3], "revoked_at": r[4]} for r in cur.fetchall()]

def revoke_key(workspace_id: int, key_id: int) -> None:
    migrate()
    conn = _db()
    conn.execute("UPDATE api_keys SET revoked_at=? WHERE id=? AND workspace_id=?", (now(), int(key_id), int(workspace_id)))
    conn.commit()

def verify_key(workspace_id: int, api_key: str) -> bool:
    migrate()
    conn = _db()
    h = _hash(api_key.strip())
    cur = conn.execute("SELECT 1 FROM api_keys WHERE workspace_id=? AND key_hash=? AND revoked_at IS NULL", (int(workspace_id), h))
    return cur.fetchone() is not None

def resolve_workspace(api_key: str) -> Optional[int]:
    migrate()
    conn = _db()
    h = _hash(api_key.strip())
    cur = conn.execute("SELECT workspace_id FROM api_keys WHERE key_hash=? AND revoked_at IS NULL", (h,))
    row = cur.fetchone()
    return int(row[0]) if row else None
