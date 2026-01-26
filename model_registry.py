import json
import time
from typing import Dict, Any, Optional, List

from db import backend, connect, fetchone, fetchall, exec_commit, insert_returning_id

def now() -> int:
    return int(time.time())

def migrate() -> None:
    conn = connect()
    b = backend()
    cur = conn.cursor() if b == "postgres" else conn
    if b == "postgres":
        cur.execute("""CREATE TABLE IF NOT EXISTS models(
            id BIGSERIAL PRIMARY KEY,
            created_at BIGINT NOT NULL,
            workspace_id BIGINT NOT NULL,
            name TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'candidate',
            weights_json TEXT NOT NULL,
            metrics_json TEXT,
            notes TEXT
        )""")
    else:
        cur.execute("""CREATE TABLE IF NOT EXISTS models(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at INTEGER NOT NULL,
            workspace_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'candidate',
            weights_json TEXT NOT NULL,
            metrics_json TEXT,
            notes TEXT
        )""")
    conn.commit()
    try: conn.close()
    except Exception: pass

def list_models(workspace_id: int) -> List[Dict[str, Any]]:
    migrate()
    rows = fetchall("SELECT id, created_at, name, status, metrics_json, notes FROM models WHERE workspace_id=? ORDER BY created_at DESC",
                    (int(workspace_id),))
    out: List[Dict[str, Any]] = []
    for r in rows:
        try:
            mj = json.loads(r[4] or "{}")
        except Exception:
            mj = {}
        out.append({"id": r[0], "created_at": r[1], "name": r[2], "status": r[3], "metrics": mj, "notes": r[5] or ""})
    return out

def get_model(model_id: int) -> Optional[Dict[str, Any]]:
    migrate()
    row = fetchone("SELECT id, created_at, workspace_id, name, status, weights_json, metrics_json, notes FROM models WHERE id=?",
                   (int(model_id),))
    if not row:
        return None
    try:
        w = json.loads(row[5] or "{}")
    except Exception:
        w = {}
    try:
        mj = json.loads(row[6] or "{}")
    except Exception:
        mj = {}
    return {"id": row[0], "created_at": row[1], "workspace_id": row[2], "name": row[3], "status": row[4], "weights": w, "metrics": mj, "notes": row[7] or ""}

def get_active_model(workspace_id: int) -> Optional[Dict[str, Any]]:
    migrate()
    row = fetchone("SELECT id FROM models WHERE workspace_id=? AND status='active' ORDER BY created_at DESC LIMIT 1",
                   (int(workspace_id),))
    if not row:
        return None
    return get_model(int(row[0]))

def create_candidate_model(workspace_id: int, name: str, weights: Dict[str, float], metrics: Optional[Dict[str, Any]] = None, notes: str = "") -> int:
    migrate()
    return insert_returning_id(
        "INSERT INTO models(created_at, workspace_id, name, status, weights_json, metrics_json, notes) VALUES(?,?,?,?,?,?,?)",
        (now(), int(workspace_id), name[:64], "candidate", json.dumps(weights), json.dumps(metrics or {}), (notes or "")[:500]),
        sql_postgres="INSERT INTO models(created_at, workspace_id, name, status, weights_json, metrics_json, notes) VALUES(%s,%s,%s,%s,%s,%s,%s) RETURNING id",
    )

def activate_model(workspace_id: int, model_id: int) -> None:
    migrate()
    exec_commit("UPDATE models SET status='archived' WHERE workspace_id=? AND status='active'", (int(workspace_id),))
    exec_commit("UPDATE models SET status='active' WHERE id=? AND workspace_id=?", (int(model_id), int(workspace_id)))
