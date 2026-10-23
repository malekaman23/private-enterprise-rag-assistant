"""
reminders.py
------------
Reminders ko SQLite mein store/retrieve karta hai.
"""

import sqlite3
import os
from datetime import datetime
from datetime import timezone

REMINDERS_DB = "memory/reminders.db"
import storage


def init_reminders_db():
    if storage.enabled():
        storage.init()
        return
    os.makedirs(os.path.dirname(REMINDERS_DB), exist_ok=True)
    conn = sqlite3.connect(REMINDERS_DB)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT,
            remind_at TEXT,
            created_at TEXT,
            done INTEGER DEFAULT 0,
            tenant_id TEXT NOT NULL DEFAULT 'personal',
            user_id TEXT NOT NULL DEFAULT 'personal-user'
        )
    """)
    columns = {row[1] for row in cursor.execute("PRAGMA table_info(reminders)")}
    if "tenant_id" not in columns:
        cursor.execute("ALTER TABLE reminders ADD COLUMN tenant_id TEXT NOT NULL DEFAULT 'personal'")
    if "user_id" not in columns:
        cursor.execute("ALTER TABLE reminders ADD COLUMN user_id TEXT NOT NULL DEFAULT 'personal-user'")
    conn.commit()
    conn.close()


def add_reminder(text: str, remind_at: str, tenant_id: str = "personal", user_id: str = "personal-user") -> str:
    """Naya reminder add karta hai. remind_at: free-text date/time (e.g. '2026-09-20 10:00')."""
    if storage.enabled():
        table = storage.table("reminders")
        with storage.init().begin() as conn:
            conn.execute(table.insert().values(
                text=text, remind_at=remind_at, created_at=datetime.now(timezone.utc),
                done=False, tenant_id=tenant_id, user_id=user_id,
            ))
        return f"Reminder set: '{text}' at {remind_at}"
    init_reminders_db()
    conn = sqlite3.connect(REMINDERS_DB)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO reminders (text, remind_at, created_at, tenant_id, user_id) VALUES (?, ?, ?, ?, ?)",
        (text, remind_at, datetime.now().isoformat(), tenant_id, user_id),
    )
    conn.commit()
    conn.close()
    return f"Reminder set: '{text}' at {remind_at}"


def list_reminders(include_done: bool = False, tenant_id: str = "personal", user_id: str = "personal-user") -> str:
    """Saare pending (ya sab, agar include_done=True) reminders return karta hai."""
    if storage.enabled():
        from sqlalchemy import select
        table = storage.table("reminders")
        condition = (table.c.tenant_id == tenant_id) & (table.c.user_id == user_id)
        if not include_done:
            condition = condition & (table.c.done == False)  # noqa: E712
        with storage.init().connect() as conn:
            rows = conn.execute(select(table.c.id, table.c.text, table.c.remind_at, table.c.done).where(condition).order_by(table.c.id)).fetchall()
        if not rows:
            return "Koi reminder nahi mila."
        return "\n".join(f"#{r[0]}: {r[1]} (at {r[2]}){' [DONE]' if r[3] else ''}" for r in rows)
    init_reminders_db()
    conn = sqlite3.connect(REMINDERS_DB)
    cursor = conn.cursor()
    if include_done:
        cursor.execute("SELECT id, text, remind_at, done FROM reminders WHERE tenant_id=? AND user_id=? ORDER BY id", (tenant_id, user_id))
    else:
        cursor.execute("SELECT id, text, remind_at, done FROM reminders WHERE done=0 AND tenant_id=? AND user_id=? ORDER BY id", (tenant_id, user_id))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return "Koi reminder nahi mila."

    lines = [f"#{r[0]}: {r[1]} (at {r[2]}){' [DONE]' if r[3] else ''}" for r in rows]
    return "\n".join(lines)


def mark_done(reminder_id: int, tenant_id: str = "personal", user_id: str = "personal-user") -> str:
    if storage.enabled():
        table = storage.table("reminders")
        with storage.init().begin() as conn:
            conn.execute(table.update().where(
                table.c.id == reminder_id, table.c.tenant_id == tenant_id, table.c.user_id == user_id
            ).values(done=True))
        return f"Reminder #{reminder_id} done mark kar diya."
    init_reminders_db()
    conn = sqlite3.connect(REMINDERS_DB)
    cursor = conn.cursor()
    cursor.execute("UPDATE reminders SET done=1 WHERE id=? AND tenant_id=? AND user_id=?", (reminder_id, tenant_id, user_id))
    conn.commit()
    conn.close()
    return f"Reminder #{reminder_id} done mark kar diya."


def delete_reminder(reminder_id: int, tenant_id: str = "personal", user_id: str = "personal-user") -> str:
    """Ek reminder ko permanently delete kar deta hai."""
    if storage.enabled():
        table = storage.table("reminders")
        with storage.init().begin() as conn:
            conn.execute(table.delete().where(
                table.c.id == reminder_id, table.c.tenant_id == tenant_id, table.c.user_id == user_id
            ))
        return f"Reminder #{reminder_id} delete kar diya."
    init_reminders_db()
    conn = sqlite3.connect(REMINDERS_DB)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM reminders WHERE id=? AND tenant_id=? AND user_id=?", (reminder_id, tenant_id, user_id))
    conn.commit()
    conn.close()
    return f"Reminder #{reminder_id} delete kar diya."


def list_reminders_structured(include_done: bool = True, tenant_id: str = "personal", user_id: str = "personal-user"):
    """
    UI ke liye structured (list of dicts) format mein reminders deta hai -
    taaki frontend har reminder ke saath alag se buttons (done/delete) bana sake.
    """
    if storage.enabled():
        from sqlalchemy import select
        table = storage.table("reminders")
        condition = (table.c.tenant_id == tenant_id) & (table.c.user_id == user_id)
        if not include_done:
            condition = condition & (table.c.done == False)  # noqa: E712
        with storage.init().connect() as conn:
            rows = conn.execute(select(table.c.id, table.c.text, table.c.remind_at, table.c.done).where(condition).order_by(table.c.done, table.c.id)).fetchall()
        return [{"id": r[0], "text": r[1], "remind_at": r[2], "done": bool(r[3])} for r in rows]
    init_reminders_db()
    conn = sqlite3.connect(REMINDERS_DB)
    cursor = conn.cursor()
    if include_done:
        cursor.execute("SELECT id, text, remind_at, done FROM reminders WHERE tenant_id=? AND user_id=? ORDER BY done, id", (tenant_id, user_id))
    else:
        cursor.execute("SELECT id, text, remind_at, done FROM reminders WHERE done=0 AND tenant_id=? AND user_id=? ORDER BY done, id", (tenant_id, user_id))
    rows = cursor.fetchall()
    conn.close()

    return [
        {"id": r[0], "text": r[1], "remind_at": r[2], "done": bool(r[3])}
        for r in rows
    ]
