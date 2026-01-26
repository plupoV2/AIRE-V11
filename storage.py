import json
import time
from typing import Dict, Any, List, Optional

from db import backend, connect, ensure_column, insert_returning_id, fetchall, fetchone, exec_commit

def now() -> int:
    return int(time.time())

def migrate() -> None:
    conn = connect()
    b = backend()
    cur = conn.cursor() if b == "postgres" else conn

    if b == "postgres":
        cur.execute("""CREATE TABLE IF NOT EXISTS reports (
            id BIGSERIAL PRIMARY KEY,
            created_at BIGINT NOT NULL,
            address TEXT,
            url TEXT,
            grade TEXT,
            score DOUBLE PRECISION,
            confidence DOUBLE PRECISION,
            payload_json TEXT,
            workspace_id BIGINT,
            user_id BIGINT
        )""")
        cur.execute("""CREATE TABLE IF NOT EXISTS templates (
            id BIGSERIAL PRIMARY KEY,
            created_at BIGINT NOT NULL,
            name TEXT NOT NULL,
            template_json TEXT NOT NULL,
            workspace_id BIGINT,
            user_id BIGINT
        )""")
        cur.execute("""CREATE TABLE IF NOT EXISTS watchlist (
            id BIGSERIAL PRIMARY KEY,
            created_at BIGINT NOT NULL,
            updated_at BIGINT NOT NULL,
            address TEXT NOT NULL,
            url TEXT,
            target_grade TEXT,
            target_score DOUBLE PRECISION,
            notes TEXT,
            workspace_id BIGINT,
            user_id BIGINT
        )""")
        cur.execute("""CREATE TABLE IF NOT EXISTS alert_runs (
            id BIGSERIAL PRIMARY KEY,
            created_at BIGINT NOT NULL,
            watchlist_id BIGINT,
            address TEXT,
            url TEXT,
            grade TEXT,
            score DOUBLE PRECISION,
            confidence DOUBLE PRECISION,
            hit INTEGER DEFAULT 0,
            payload_json TEXT,
            workspace_id BIGINT,
            user_id BIGINT
        )""")
    else:
        cur.execute("""CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at INTEGER NOT NULL,
            address TEXT,
            url TEXT,
            grade TEXT,
            score REAL,
            confidence REAL,
            payload_json TEXT,
            workspace_id INTEGER,
            user_id INTEGER
        )""")
        cur.execute("""CREATE TABLE IF NOT EXISTS templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at INTEGER NOT NULL,
            name TEXT NOT NULL,
            template_json TEXT NOT NULL,
            workspace_id INTEGER,
            user_id INTEGER
        )""")
        cur.execute("""CREATE TABLE IF NOT EXISTS watchlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL,
            address TEXT NOT NULL,
            url TEXT,
            target_grade TEXT,
            target_score REAL,
            notes TEXT,
            workspace_id INTEGER,
            user_id INTEGER
        )""")
        cur.execute("""CREATE TABLE IF NOT EXISTS alert_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at INTEGER NOT NULL,
            watchlist_id INTEGER,
            address TEXT,
            url TEXT,
            grade TEXT,
            score REAL,
            confidence REAL,
            hit INTEGER DEFAULT 0,
            payload_json TEXT,
            workspace_id INTEGER,
            user_id INTEGER
        )""")

    conn.commit()
    try:
        conn.close()
    except Exception:
        pass

# ---- Reports ----
def save_report(address: str, url: str, grade: str, score: float, confidence: float, payload: Dict[str, Any], workspace_id: int = 0, user_id: int = 0) -> int:
    migrate()
    payload_json = json.dumps(payload)
    return insert_returning_id(
        "INSERT INTO reports(created_at, address, url, grade, score, confidence, payload_json, workspace_id, user_id) VALUES(?,?,?,?,?,?,?,?,?)",
        (now(), address, url, grade, float(score), float(confidence), payload_json, int(workspace_id), int(user_id)),
        sql_postgres="INSERT INTO reports(created_at, address, url, grade, score, confidence, payload_json, workspace_id, user_id) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
    )

def list_reports(limit: int = 50, workspace_id: int = 0) -> List[Dict[str, Any]]:
    migrate()
    rows = fetchall(
        "SELECT id, created_at, address, url, grade, score, confidence FROM reports WHERE (?=0 OR workspace_id=?) ORDER BY created_at DESC LIMIT ?",
        (int(workspace_id), int(workspace_id), int(limit)),
    )
    return [{"id": r[0], "created_at": r[1], "address": r[2], "url": r[3], "grade": r[4], "score": r[5], "confidence": r[6]} for r in rows]

def read_report(report_id: int) -> Dict[str, Any]:
    migrate()
    row = fetchone("SELECT payload_json FROM reports WHERE id=?", (int(report_id),))
    if not row:
        return {}
    try:
        return json.loads(row[0])
    except Exception:
        return {}

# ---- Templates ----
def upsert_template(name: str, template: Dict[str, Any], template_id: Optional[int] = None, workspace_id: int = 0, user_id: int = 0) -> int:
    migrate()
    tjson = json.dumps(template)
    if template_id:
        exec_commit("UPDATE templates SET name=?, template_json=? WHERE id=?", (name, tjson, int(template_id)))
        return int(template_id)
    return insert_returning_id(
        "INSERT INTO templates(created_at, name, template_json, workspace_id, user_id) VALUES(?,?,?,?,?)",
        (now(), name, tjson, int(workspace_id), int(user_id)),
        sql_postgres="INSERT INTO templates(created_at, name, template_json, workspace_id, user_id) VALUES(%s,%s,%s,%s,%s) RETURNING id",
    )

def list_templates(workspace_id: int = 0) -> List[Dict[str, Any]]:
    migrate()
    rows = fetchall("SELECT id, created_at, name, template_json FROM templates WHERE (?=0 OR workspace_id=?) ORDER BY created_at DESC", (int(workspace_id), int(workspace_id)))
    out: List[Dict[str, Any]] = []
    for r in rows:
        try:
            tj = json.loads(r[3])
        except Exception:
            tj = {}
        out.append({"id": r[0], "created_at": r[1], "name": r[2], "template": tj})
    return out

def delete_template(template_id: int) -> None:
    migrate()
    exec_commit("DELETE FROM templates WHERE id=?", (int(template_id),))

# ---- Watchlist & Alerts ----
def add_watchlist(address: str, url: str = "", target_grade: str = "B", target_score: float = 80.0, notes: str = "", workspace_id: int = 0, user_id: int = 0) -> int:
    migrate()
    return insert_returning_id(
        "INSERT INTO watchlist(created_at, updated_at, address, url, target_grade, target_score, notes, workspace_id, user_id) VALUES(?,?,?,?,?,?,?,?,?)",
        (now(), now(), address, url, target_grade, float(target_score), notes, int(workspace_id), int(user_id)),
        sql_postgres="INSERT INTO watchlist(created_at, updated_at, address, url, target_grade, target_score, notes, workspace_id, user_id) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
    )

def update_watchlist(item_id: int, **fields) -> None:
    migrate()
    allowed = {"address","url","target_grade","target_score","notes"}
    sets = []
    vals = []
    for k,v in fields.items():
        if k in allowed:
            sets.append(f"{k}=?")
            vals.append(v)
    sets.append("updated_at=?")
    vals.append(now())
    vals.append(int(item_id))
    exec_commit(f"UPDATE watchlist SET {', '.join(sets)} WHERE id=?", vals)

def delete_watchlist(item_id: int) -> None:
    migrate()
    exec_commit("DELETE FROM watchlist WHERE id=?", (int(item_id),))

def list_watchlist(workspace_id: int = 0) -> List[Dict[str, Any]]:
    migrate()
    rows = fetchall("SELECT id, created_at, updated_at, address, url, target_grade, target_score, notes FROM watchlist WHERE (?=0 OR workspace_id=?) ORDER BY updated_at DESC", (int(workspace_id), int(workspace_id)))
    return [{
        "id": r[0], "created_at": r[1], "updated_at": r[2], "address": r[3], "url": r[4],
        "target_grade": r[5], "target_score": r[6], "notes": r[7]
    } for r in rows]

def save_alert_run(watchlist_id: int, address: str, url: str, grade: str, score: float, confidence: float, hit: int, payload: Dict[str, Any], workspace_id: int = 0, user_id: int = 0) -> int:
    migrate()
    payload_json = json.dumps(payload)
    return insert_returning_id(
        "INSERT INTO alert_runs(created_at, watchlist_id, address, url, grade, score, confidence, hit, payload_json, workspace_id, user_id) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
        (now(), int(watchlist_id), address, url, grade, float(score), float(confidence), int(hit), payload_json, int(workspace_id), int(user_id)),
        sql_postgres="INSERT INTO alert_runs(created_at, watchlist_id, address, url, grade, score, confidence, hit, payload_json, workspace_id, user_id) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
    )

def list_alert_runs(limit: int = 100, workspace_id: int = 0) -> List[Dict[str, Any]]:
    migrate()
    rows = fetchall(
        "SELECT id, created_at, watchlist_id, address, url, grade, score, confidence, hit FROM alert_runs WHERE (?=0 OR workspace_id=?) ORDER BY created_at DESC LIMIT ?",
        (int(workspace_id), int(workspace_id), int(limit)),
    )
    return [{
        "id": r[0], "created_at": r[1], "watchlist_id": r[2], "address": r[3], "url": r[4],
        "grade": r[5], "score": r[6], "confidence": r[7], "hit": r[8]
    } for r in rows]

def read_alert_run(run_id: int) -> Dict[str, Any]:
    migrate()
    row = fetchone("SELECT payload_json FROM alert_runs WHERE id=?", (int(run_id),))
    if not row:
        return {}
    try:
        return json.loads(row[0])
    except Exception:
        return {}
