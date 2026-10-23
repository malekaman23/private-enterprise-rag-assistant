"""Approval queue for external side effects such as email and payments."""

import json
import os
import sqlite3
from datetime import datetime, timezone
import storage

ACTION_DB = "memory/actions.db"


def _connect():
    os.makedirs(os.path.dirname(ACTION_DB), exist_ok=True)
    conn = sqlite3.connect(ACTION_DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS pending_actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            action_type TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL,
            reviewed_at TEXT,
            reviewed_by TEXT
        )
    """)
    return conn


def _ensure_storage():
    if storage.enabled():
        storage.init()
        return storage.table("pending_actions")
    return None


def create_action(tenant_id: str, user_id: str, action_type: str, payload: dict) -> int:
    table = _ensure_storage()
    if table is not None:
        with storage.init().begin() as conn:
            result = conn.execute(table.insert().values(
                tenant_id=tenant_id, user_id=user_id, action_type=action_type,
                payload_json=json.dumps(payload, ensure_ascii=True),
                status="pending", created_at=datetime.now(timezone.utc),
            ))
            return int(result.inserted_primary_key[0])
    conn = _connect()
    cursor = conn.execute(
        "INSERT INTO pending_actions (tenant_id, user_id, action_type, payload_json, created_at) VALUES (?, ?, ?, ?, ?)",
        (tenant_id, user_id, action_type, json.dumps(payload, ensure_ascii=True), datetime.now(timezone.utc).isoformat()),
    )
    action_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return action_id


def list_actions(tenant_id: str, user_id: str = None, include_completed: bool = False):
    table = _ensure_storage()
    if table is not None:
        from sqlalchemy import select
        condition = table.c.tenant_id == tenant_id
        if user_id:
            condition = condition & (table.c.user_id == user_id)
        if not include_completed:
            condition = condition & (table.c.status == "pending")
        with storage.init().connect() as conn:
            rows = conn.execute(select(table).where(condition).order_by(table.c.id.desc())).fetchall()
        return [_row_sql(row, table) for row in rows]
    conn = _connect()
    query = "SELECT id, user_id, action_type, payload_json, status, created_at, reviewed_at, reviewed_by FROM pending_actions WHERE tenant_id=?"
    params = [tenant_id]
    if user_id:
        query += " AND user_id=?"
        params.append(user_id)
    if not include_completed:
        query += " AND status='pending'"
    query += " ORDER BY id DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [_row(row) for row in rows]


def _row(row):
    return {
        "id": row[0], "user_id": row[1], "action_type": row[2],
        "payload": json.loads(row[3]), "status": row[4], "created_at": row[5],
        "reviewed_at": row[6], "reviewed_by": row[7],
    }


def _row_sql(row, table):
    return {
        "id": row.id, "user_id": row.user_id, "action_type": row.action_type,
        "payload": json.loads(row.payload_json), "status": row.status,
        "created_at": row.created_at.isoformat() if hasattr(row.created_at, "isoformat") else str(row.created_at),
        "reviewed_at": row.reviewed_at.isoformat() if row.reviewed_at and hasattr(row.reviewed_at, "isoformat") else row.reviewed_at,
        "reviewed_by": row.reviewed_by,
    }


def get_action(action_id: int, tenant_id: str):
    table = _ensure_storage()
    if table is not None:
        from sqlalchemy import select
        with storage.init().connect() as conn:
            row = conn.execute(select(table).where(table.c.id == action_id, table.c.tenant_id == tenant_id)).fetchone()
        return _row_sql(row, table) if row else None
    conn = _connect()
    row = conn.execute(
        "SELECT id, user_id, action_type, payload_json, status, created_at, reviewed_at, reviewed_by FROM pending_actions WHERE id=? AND tenant_id=?",
        (action_id, tenant_id),
    ).fetchone()
    conn.close()
    return _row(row) if row else None


def review_action(action_id: int, tenant_id: str, status: str, reviewed_by: str):
    if status not in {"approved", "rejected"}:
        raise ValueError("Invalid review status")
    table = _ensure_storage()
    if table is not None:
        with storage.init().begin() as conn:
            result = conn.execute(table.update().where(
                table.c.id == action_id, table.c.tenant_id == tenant_id, table.c.status == "pending"
            ).values(status=status, reviewed_at=datetime.now(timezone.utc), reviewed_by=reviewed_by))
        return result.rowcount == 1
    conn = _connect()
    cursor = conn.execute(
        "UPDATE pending_actions SET status=?, reviewed_at=?, reviewed_by=? WHERE id=? AND tenant_id=? AND status='pending'",
        (status, datetime.now(timezone.utc).isoformat(), reviewed_by, action_id, tenant_id),
    )
    conn.commit()
    changed = cursor.rowcount
    conn.close()
    return changed == 1


def set_status(action_id: int, tenant_id: str, status: str):
    """Internal finalization after an approved action is executed."""
    table = _ensure_storage()
    if table is not None:
        with storage.init().begin() as conn:
            conn.execute(table.update().where(table.c.id == action_id, table.c.tenant_id == tenant_id).values(status=status))
        return
    conn = _connect()
    conn.execute(
        "UPDATE pending_actions SET status=? WHERE id=? AND tenant_id=?",
        (status, action_id, tenant_id),
    )
    conn.commit()
    conn.close()
