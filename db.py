import os
import sqlite3
from typing import Any, Iterable, Optional, Tuple, List, Dict

_BACKEND = None  # "sqlite" or "postgres"

def backend() -> str:
    global _BACKEND
    if _BACKEND:
        return _BACKEND
    url = os.getenv("DATABASE_URL", "").strip()
    if url.startswith("postgres://") or url.startswith("postgresql://"):
        _BACKEND = "postgres"
    else:
        _BACKEND = "sqlite"
    return _BACKEND

def _sqlite_conn() -> sqlite3.Connection:
    path = os.getenv("SQLITE_PATH", "aire.db")
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn

def _pg_conn():
    import psycopg2  # installed via requirements when using Postgres
    url = os.getenv("DATABASE_URL")
    # psycopg2 supports both postgres:// and postgresql://
    conn = psycopg2.connect(url)
    conn.autocommit = False
    return conn

def connect():
    if backend() == "postgres":
        return _pg_conn()
    return _sqlite_conn()

def _adapt_sql(sql: str) -> str:
    # Convert SQLite qmark placeholders to psycopg2 %s placeholders
    if backend() == "postgres":
        return sql.replace("?", "%s")
    return sql

def execute(sql: str, params: Optional[Iterable[Any]] = None, *, commit: bool = False):
    conn = connect()
    cur = conn.cursor() if backend() == "postgres" else conn
    q = _adapt_sql(sql)
    if params is None:
        params = ()
    if backend() == "postgres":
        cur.execute(q, tuple(params))
        if commit:
            conn.commit()
        return conn, cur
    else:
        cur = conn.execute(q, tuple(params))
        if commit:
            conn.commit()
        return conn, cur

def fetchone(sql: str, params: Optional[Iterable[Any]] = None):
    conn, cur = execute(sql, params)
    row = cur.fetchone()
    try:
        conn.close()
    except Exception:
        pass
    return row

def fetchall(sql: str, params: Optional[Iterable[Any]] = None):
    conn, cur = execute(sql, params)
    rows = cur.fetchall()
    try:
        conn.close()
    except Exception:
        pass
    return rows

def exec_commit(sql: str, params: Optional[Iterable[Any]] = None) -> None:
    conn, cur = execute(sql, params, commit=True)
    try:
        conn.close()
    except Exception:
        pass

def insert_returning_id(sql_sqlite: str, params: Iterable[Any], *, sql_postgres: Optional[str] = None) -> int:
    """Insert and return integer id for both backends."""
    if backend() == "postgres":
        q = sql_postgres or (sql_sqlite + " RETURNING id")
        conn = connect()
        cur = conn.cursor()
        cur.execute(_adapt_sql(q), tuple(params))
        row = cur.fetchone()
        conn.commit()
        conn.close()
        return int(row[0])
    # sqlite
    conn = connect()
    cur = conn.execute(sql_sqlite, tuple(params))
    conn.commit()
    rid = cur.lastrowid
    conn.close()
    return int(rid)

def ensure_column(table: str, col: str, coldef_sqlite: str, coldef_postgres: Optional[str] = None) -> None:
    if backend() == "postgres":
        coldef = coldef_postgres or coldef_sqlite
        exec_commit(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {coldef}")
        return
    conn = connect()
    cur = conn.execute(f"PRAGMA table_info({table})")
    cols = {r[1] for r in cur.fetchall()}
    if col not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {coldef_sqlite}")
        conn.commit()
    conn.close()
