"""Optional production SQL storage backend.

When DATABASE_URL is unset, the project keeps its zero-cost SQLite files for
personal mode. When set (for example PostgreSQL), shared operational data is
created in one database so multiple API workers can safely use it.
"""

import config

DATABASE_URL = getattr(config, "DATABASE_URL", "").strip()
_engine = None
_tables = None


def enabled() -> bool:
    return bool(DATABASE_URL)


def init():
    global _engine, _tables
    if not enabled():
        return None
    if _engine is not None:
        return _engine

    from sqlalchemy import (
        Boolean, Column, DateTime, Integer, MetaData, String, Table, Text,
        create_engine,
    )

    kwargs = {"pool_pre_ping": True}
    if DATABASE_URL.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    _engine = create_engine(DATABASE_URL, **kwargs)
    metadata = MetaData()
    _tables = {
        "chat_history": Table(
            "chat_history", metadata,
            Column("id", Integer, primary_key=True), Column("role", String(32), nullable=False),
            Column("message", Text, nullable=False), Column("timestamp", DateTime(timezone=True), nullable=False),
            Column("tenant_id", String(255), nullable=False), Column("user_id", String(255), nullable=False),
        ),
        "reminders": Table(
            "reminders", metadata,
            Column("id", Integer, primary_key=True), Column("text", Text, nullable=False),
            Column("remind_at", String(255), nullable=False), Column("created_at", DateTime(timezone=True), nullable=False),
            Column("done", Boolean, nullable=False, default=False), Column("tenant_id", String(255), nullable=False),
            Column("user_id", String(255), nullable=False),
        ),
        "pending_actions": Table(
            "pending_actions", metadata,
            Column("id", Integer, primary_key=True), Column("tenant_id", String(255), nullable=False),
            Column("user_id", String(255), nullable=False), Column("action_type", String(100), nullable=False),
            Column("payload_json", Text, nullable=False), Column("status", String(32), nullable=False, default="pending"),
            Column("created_at", DateTime(timezone=True), nullable=False), Column("reviewed_at", DateTime(timezone=True)),
            Column("reviewed_by", String(255)),
        ),
        "document_submissions": Table(
            "document_submissions", metadata,
            Column("id", Integer, primary_key=True), Column("tenant_id", String(255), nullable=False),
            Column("user_id", String(255), nullable=False), Column("filename", String(512), nullable=False),
            Column("quarantine_path", String(1024), nullable=False), Column("category", String(255), nullable=False),
            Column("department_id", String(255), nullable=False, default=""),
            Column("required_role", String(64), nullable=False, default="shared"),
            Column("status", String(32), nullable=False, default="pending"),
            Column("created_at", DateTime(timezone=True), nullable=False),
            Column("reviewed_at", DateTime(timezone=True)), Column("reviewed_by", String(255)),
            Column("review_note", Text),
        ),
        "audit_events": Table(
            "audit_events", metadata,
            Column("id", Integer, primary_key=True), Column("timestamp", DateTime(timezone=True), nullable=False),
            Column("tenant_id", String(255), nullable=False), Column("user_id", String(255), nullable=False),
            Column("event_type", String(150), nullable=False), Column("status", String(32), nullable=False),
            Column("metadata_json", Text, nullable=False),
        ),
    }
    metadata.create_all(_engine)
    return _engine


def table(name: str):
    init()
    return _tables[name]

