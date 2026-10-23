"""Append-oriented audit events without storing sensitive content."""

import hashlib
import json
import os
import sqlite3
from datetime import datetime, timezone
import storage

AUDIT_DB = "memory/audit.db"


def _connect():
    os.makedirs(os.path.dirname(AUDIT_DB), exist_ok=True)
    conn = sqlite3.connect(AUDIT_DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS audit_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            tenant_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            status TEXT NOT NULL,
            metadata_json TEXT NOT NULL
        )
    """)
    return conn


def digest(value: str) -> str:
    """Return a non-reversible identifier for correlation without raw content."""
    return hashlib.sha256((value or "").encode("utf-8")).hexdigest()[:16]


def record_event(tenant_id: str, user_id: str, event_type: str, status: str = "ok", metadata=None):
    safe_metadata = metadata if isinstance(metadata, dict) else {}
    if storage.enabled():
        table = storage.table("audit_events")
        with storage.init().begin() as conn:
            conn.execute(table.insert().values(
                timestamp=datetime.now(timezone.utc), tenant_id=str(tenant_id), user_id=str(user_id),
                event_type=str(event_type), status=str(status),
                metadata_json=json.dumps(safe_metadata, ensure_ascii=True, sort_keys=True),
            ))
        return
    conn = _connect()
    conn.execute(
        "INSERT INTO audit_events (timestamp, tenant_id, user_id, event_type, status, metadata_json) VALUES (?, ?, ?, ?, ?, ?)",
        (
            datetime.now(timezone.utc).isoformat(),
            str(tenant_id), str(user_id), str(event_type), str(status),
            json.dumps(safe_metadata, ensure_ascii=True, sort_keys=True),
        ),
    )
    conn.commit()
    conn.close()


def list_events(tenant_id: str, limit: int = 100):
    if storage.enabled():
        from sqlalchemy import select
        table = storage.table("audit_events")
        with storage.init().connect() as conn:
            rows = conn.execute(select(table).where(table.c.tenant_id == tenant_id).order_by(table.c.id.desc()).limit(max(1, min(int(limit), 500)))).fetchall()
        return [
            {"id": row.id, "timestamp": row.timestamp.isoformat() if hasattr(row.timestamp, "isoformat") else str(row.timestamp),
             "user_id": row.user_id, "event_type": row.event_type, "status": row.status,
             "metadata": json.loads(row.metadata_json)}
            for row in rows
        ]
    conn = _connect()
    rows = conn.execute(
        "SELECT id, timestamp, user_id, event_type, status, metadata_json FROM audit_events WHERE tenant_id=? ORDER BY id DESC LIMIT ?",
        (tenant_id, max(1, min(int(limit), 500))),
    ).fetchall()
    conn.close()
    return [
        {
            "id": row[0], "timestamp": row[1], "user_id": row[2],
            "event_type": row[3], "status": row[4],
            "metadata": json.loads(row[5]),
        }
        for row in rows
    ]
