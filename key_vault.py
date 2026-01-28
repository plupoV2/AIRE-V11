from __future__ import annotations

from typing import Dict

from db import backend, exec_commit, fetchall, now


def migrate() -> None:
    exec_commit("""
    CREATE TABLE IF NOT EXISTS integration_keys (
        workspace_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        value TEXT NOT NULL,
        updated_at INTEGER NOT NULL,
        PRIMARY KEY (workspace_id, name)
    );
    """)


def set_key(workspace_id: int, name: str, value: str) -> None:
    migrate()
    ws = int(workspace_id)
    key = name.strip().upper()
    if backend() == "postgres":
        exec_commit(
            """
            INSERT INTO integration_keys(workspace_id, name, value, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT (workspace_id, name)
            DO UPDATE SET value = EXCLUDED.value, updated_at = EXCLUDED.updated_at
            """,
            (ws, key, value, now()),
        )
        return
    exec_commit(
        """
        INSERT OR REPLACE INTO integration_keys(workspace_id, name, value, updated_at)
        VALUES (?, ?, ?, ?)
        """,
        (ws, key, value, now()),
    )


def delete_key(workspace_id: int, name: str) -> None:
    migrate()
    exec_commit(
        "DELETE FROM integration_keys WHERE workspace_id=? AND name=?",
        (int(workspace_id), name.strip().upper()),
    )


def get_keys(workspace_id: int) -> Dict[str, str]:
    migrate()
    rows = fetchall(
        "SELECT name, value FROM integration_keys WHERE workspace_id=?",
        (int(workspace_id),),
    )
    return {str(r[0]).upper(): str(r[1]) for r in rows or []}
