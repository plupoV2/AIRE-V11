import json
import time
from typing import Dict, Any, Optional, List

from db import backend, connect, fetchall, insert_returning_id

def now() -> int:
    return int(time.time())

def migrate() -> None:
    conn = connect()
    b = backend()
    cur = conn.cursor() if b == "postgres" else conn
    if b == "postgres":
        cur.execute("""CREATE TABLE IF NOT EXISTS feedback(
            id BIGSERIAL PRIMARY KEY,
            created_at BIGINT NOT NULL,
            workspace_id BIGINT NOT NULL,
            user_id BIGINT NOT NULL,
            report_id BIGINT,
            address TEXT,
            url TEXT,
            label INTEGER NOT NULL,
            outcome_json TEXT
        )""")
    else:
        cur.execute("""CREATE TABLE IF NOT EXISTS feedback(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at INTEGER NOT NULL,
            workspace_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            report_id INTEGER,
            address TEXT,
            url TEXT,
            label INTEGER NOT NULL,
            outcome_json TEXT
        )""")
    conn.commit()
    try: conn.close()
    except Exception: pass

def add_feedback(workspace_id: int, user_id: int, label: int, report_id: int = 0, address: str = "", url: str = "", outcome: Optional[Dict[str, Any]] = None) -> int:
    migrate()
    return insert_returning_id(
        "INSERT INTO feedback(created_at, workspace_id, user_id, report_id, address, url, label, outcome_json) VALUES(?,?,?,?,?,?,?,?)",
        (now(), int(workspace_id), int(user_id), (int(report_id) if report_id else None), address, url, int(label), json.dumps(outcome or {})),
        sql_postgres="INSERT INTO feedback(created_at, workspace_id, user_id, report_id, address, url, label, outcome_json) VALUES(%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
    )

def list_feedback(workspace_id: int, limit: int = 500) -> List[Dict[str, Any]]:
    migrate()
    rows = fetchall("SELECT id, created_at, report_id, address, url, label, outcome_json FROM feedback WHERE workspace_id=? ORDER BY created_at DESC LIMIT ?",
                    (int(workspace_id), int(limit)))
    out: List[Dict[str, Any]] = []
    for r in rows:
        try:
            oj = json.loads(r[6] or "{}")
        except Exception:
            oj = {}
        out.append({"id": r[0], "created_at": r[1], "report_id": r[2] or 0, "address": r[3] or "", "url": r[4] or "", "label": int(r[5]), "outcome": oj})
    return out
