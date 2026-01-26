import time
from db import backend, connect, exec_commit, fetchone
from typing import Dict

def now() -> int:
    return int(time.time())

def migrate() -> None:
    conn = connect()
    b = backend()
    cur = conn.cursor() if b == "postgres" else conn
    cur.execute("""CREATE TABLE IF NOT EXISTS usage(
        workspace_id INTEGER NOT NULL,
        day_key TEXT NOT NULL,
        grades_used INTEGER NOT NULL DEFAULT 0,
        api_calls_used INTEGER NOT NULL DEFAULT 0,
        updated_at INTEGER NOT NULL,
        PRIMARY KEY(workspace_id, day_key)
    )""" if b == "sqlite" else """CREATE TABLE IF NOT EXISTS usage(
        workspace_id BIGINT NOT NULL,
        day_key TEXT NOT NULL,
        grades_used BIGINT NOT NULL DEFAULT 0,
        api_calls_used BIGINT NOT NULL DEFAULT 0,
        updated_at BIGINT NOT NULL,
        PRIMARY KEY(workspace_id, day_key)
    )""")
    conn.commit()
    try: conn.close()
    except Exception: pass

def count_last_24h(workspace_id: int, event_type: str) -> int:
    migrate()
    conn = _db()
    cutoff = now() - 24*3600
    cur = conn.execute("SELECT COUNT(1) FROM usage_events WHERE workspace_id=? AND event_type=? AND created_at>=?",
                       (int(workspace_id), event_type, cutoff))
    return int(cur.fetchone()[0] or 0)

def record(workspace_id: int, user_id: int, event_type: str) -> None:
    migrate()
    conn = _db()
    conn.execute("INSERT INTO usage_events(created_at, workspace_id, user_id, event_type) VALUES(?,?,?,?)",
                 (now(), int(workspace_id), int(user_id), event_type))
    conn.commit()
