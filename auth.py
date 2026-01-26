import time
from db import backend, connect, exec_commit, fetchone, fetchall, insert_returning_id
import secrets
import hashlib
from typing import Optional, Dict, Any, List, Tuple

def now() -> int:
    return int(time.time())

def migrate() -> None:
    conn = connect()
    b = backend()
    cur = conn.cursor() if b == "postgres" else conn

    if b == "postgres":
        cur.execute("""CREATE TABLE IF NOT EXISTS users(
            id BIGSERIAL PRIMARY KEY,
            created_at BIGINT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            pass_hash TEXT NOT NULL
        )""")
        cur.execute("""CREATE TABLE IF NOT EXISTS workspaces(
            id BIGSERIAL PRIMARY KEY,
            created_at BIGINT NOT NULL,
            name TEXT NOT NULL,
            owner_user_id BIGINT NOT NULL
        )""")
        cur.execute("""CREATE TABLE IF NOT EXISTS memberships(
            user_id BIGINT NOT NULL,
            workspace_id BIGINT NOT NULL,
            role TEXT NOT NULL DEFAULT 'member',
            created_at BIGINT NOT NULL,
            PRIMARY KEY(user_id, workspace_id)
        )""")
        cur.execute("""CREATE TABLE IF NOT EXISTS invites(
            code TEXT PRIMARY KEY,
            workspace_id BIGINT NOT NULL,
            created_at BIGINT NOT NULL,
            created_by BIGINT NOT NULL,
            role TEXT NOT NULL DEFAULT 'member'
        )""")
    else:
        cur.execute("""CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at INTEGER NOT NULL,
            email TEXT NOT NULL UNIQUE,
            pass_hash TEXT NOT NULL
        )""")
        cur.execute("""CREATE TABLE IF NOT EXISTS workspaces(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at INTEGER NOT NULL,
            name TEXT NOT NULL,
            owner_user_id INTEGER NOT NULL
        )""")
        cur.execute("""CREATE TABLE IF NOT EXISTS memberships(
            user_id INTEGER NOT NULL,
            workspace_id INTEGER NOT NULL,
            role TEXT NOT NULL DEFAULT 'member',
            created_at INTEGER NOT NULL,
            PRIMARY KEY(user_id, workspace_id)
        )""")
        cur.execute("""CREATE TABLE IF NOT EXISTS invites(
            code TEXT PRIMARY KEY,
            workspace_id INTEGER NOT NULL,
            created_at INTEGER NOT NULL,
            created_by INTEGER NOT NULL,
            role TEXT NOT NULL DEFAULT 'member'
        )""")

    # Backwards compatible: add role column to invites if missing
    try:
        if b == "postgres":
            cur.execute("ALTER TABLE invites ADD COLUMN IF NOT EXISTS role TEXT NOT NULL DEFAULT 'member'")
        else:
            cols = {r[1] for r in cur.execute("PRAGMA table_info(invites)").fetchall()}
            if "role" not in cols:
                cur.execute("ALTER TABLE invites ADD COLUMN role TEXT NOT NULL DEFAULT 'member'")
    except Exception:
        pass

    conn.commit()
    try:
        conn.close()
    except Exception:
        pass

def _pbkdf2(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 160_000)

def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    dk = _pbkdf2(password, salt)
    return "pbkdf2_sha256$160000$" + salt.hex() + "$" + dk.hex()

def verify_password(password: str, stored: str) -> bool:
    try:
        _, iters, salt_hex, dk_hex = stored.split("$", 3)
        salt = bytes.fromhex(salt_hex)
        dk = bytes.fromhex(dk_hex)
        calc = _pbkdf2(password, salt)
        return secrets.compare_digest(calc, dk)
    except Exception:
        return False

def create_user(email: str, password: str) -> int:
    migrate()
    email_n = email.lower().strip()
    uid = insert_returning_id(
        "INSERT INTO users(created_at, email, pass_hash) VALUES(?,?,?)",
        (now(), email_n, hash_password(password)),
        sql_postgres="INSERT INTO users(created_at, email, pass_hash) VALUES(%s,%s,%s) RETURNING id",
    )

    # Create personal workspace
    wname = email_n.split("@")[0][:24] + "'s Workspace"
    wid = insert_returning_id(
        "INSERT INTO workspaces(created_at, name, owner_user_id) VALUES(?,?,?)",
        (now(), wname, uid),
        sql_postgres="INSERT INTO workspaces(created_at, name, owner_user_id) VALUES(%s,%s,%s) RETURNING id",
    )

    # Owner membership
    exec_commit("INSERT INTO memberships(user_id, workspace_id, role, created_at) VALUES(?,?,?,?) "
                "ON CONFLICT(user_id, workspace_id) DO NOTHING",
                (uid, wid, "owner", now()))
    return uid

def authenticate(email: str, password: str) -> Optional[Dict[str, Any]]:
    migrate()
    row = fetchone("SELECT id, email, pass_hash FROM users WHERE email=?", (email.lower().strip(),))
    if not row:
        return None
    if not verify_password(password, row[2]):
        return None
    return {"id": row[0], "email": row[1]}

def list_workspaces(user_id: int) -> List[Dict[str, Any]]:
    migrate()
    rows = fetchall("""SELECT w.id, w.name, m.role
                           FROM memberships m JOIN workspaces w ON w.id=m.workspace_id
                           WHERE m.user_id=? ORDER BY w.created_at DESC""", (int(user_id),))
    return [{"id": r[0], "name": r[1], "role": r[2]} for r in rows]

def create_workspace(user_id: int, name: str) -> int:
    migrate()
    wid = insert_returning_id(
        "INSERT INTO workspaces(created_at, name, owner_user_id) VALUES(?,?,?)",
        (now(), name.strip()[:64], int(user_id)),
        sql_postgres="INSERT INTO workspaces(created_at, name, owner_user_id) VALUES(%s,%s,%s) RETURNING id",
    )
    exec_commit("INSERT INTO memberships(user_id, workspace_id, role, created_at) VALUES(?,?,?,?) "
                "ON CONFLICT(user_id, workspace_id) DO NOTHING",
                (int(user_id), wid, "owner", now()))
    return wid

def create_invite(user_id: int, workspace_id: int, role: str = "member") -> str:
    migrate()
    code = secrets.token_urlsafe(12)
    role_n = (role or "member").lower()
    if role_n not in ("owner","admin","member","viewer"):
        role_n = "member"
    exec_commit("INSERT INTO invites(code, workspace_id, created_at, created_by, role) VALUES(?,?,?,?,?)",
                (code, int(workspace_id), now(), int(user_id), role_n))
    return code


def accept_invite(user_id: int, code: str) -> Optional[int]:
    migrate()
    row = fetchone("SELECT workspace_id, role FROM invites WHERE code=?", (code.strip(),))
    if not row:
        return None
    wid = int(row[0])
    role = (row[1] or "member").lower()
    exec_commit("INSERT INTO memberships(user_id, workspace_id, role, created_at) VALUES(?,?,?,?) "
                "ON CONFLICT(user_id, workspace_id) DO NOTHING",
                (int(user_id), wid, role, now()))
    return wid


def get_role(user_id: int, workspace_id: int) -> str:
    migrate()
    row = fetchone("SELECT role FROM memberships WHERE user_id=? AND workspace_id=?", (int(user_id), int(workspace_id)))
    return (row[0] if row else "none") or "none"

def list_members(workspace_id: int) -> List[Dict[str, Any]]:
    migrate()
    rows = fetchall("""SELECT u.id, u.email, m.role, m.created_at
                      FROM memberships m JOIN users u ON u.id=m.user_id
                      WHERE m.workspace_id=? ORDER BY m.role, u.email""", (int(workspace_id),))
    return [{"user_id": r[0], "email": r[1], "role": r[2], "created_at": r[3]} for r in rows]

def set_member_role(workspace_id: int, user_id: int, role: str) -> None:
    migrate()
    role_n = (role or "member").lower()
    if role_n not in ("owner","admin","member","viewer"):
        role_n = "member"
    exec_commit("UPDATE memberships SET role=? WHERE workspace_id=? AND user_id=?",
                (role_n, int(workspace_id), int(user_id)))

def remove_member(workspace_id: int, user_id: int) -> None:
    migrate()
    exec_commit("DELETE FROM memberships WHERE workspace_id=? AND user_id=?",
                (int(workspace_id), int(user_id)))
