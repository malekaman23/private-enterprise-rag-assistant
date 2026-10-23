"""
memory.py
---------
Yeh module assistant ko "yaad rakhne" ki capability deta hai.
Har conversation SQLite database mein save hoti hai, taaki:
1. Purani chats dubara dekh sako
2. Assistant ko pichhle context ka pata rahe (thoda sa)

SQLite isliye use kiya kyunki yeh ek chhoti file hoti hai,
bina alag se database server chalaye kaam karti hai.
"""

import sqlite3
import os
from datetime import datetime

import config
import storage


def init_db():
    if storage.enabled():
        storage.init()
        return
    """Database aur table pehli baar banata hai (agar nahi hai to)."""
    os.makedirs(os.path.dirname(config.MEMORY_DB), exist_ok=True)
    conn = sqlite3.connect(config.MEMORY_DB)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT,
            message TEXT,
            timestamp TEXT,
            tenant_id TEXT NOT NULL DEFAULT 'personal',
            user_id TEXT NOT NULL DEFAULT 'personal-user'
        )
    """)
    # Upgrade databases created by older versions without deleting history.
    columns = {row[1] for row in cursor.execute("PRAGMA table_info(chat_history)")}
    if "tenant_id" not in columns:
        cursor.execute("ALTER TABLE chat_history ADD COLUMN tenant_id TEXT NOT NULL DEFAULT 'personal'")
    if "user_id" not in columns:
        cursor.execute("ALTER TABLE chat_history ADD COLUMN user_id TEXT NOT NULL DEFAULT 'personal-user'")
    conn.commit()
    conn.close()


def save_message(role: str, message: str, tenant_id: str = "personal", user_id: str = "personal-user"):
    """Ek message (user ya assistant ka) database mein save karta hai."""
    if storage.enabled():
        from datetime import datetime, timezone
        table = storage.table("chat_history")
        with storage.init().begin() as conn:
            conn.execute(table.insert().values(
                role=role, message=message, timestamp=datetime.now(timezone.utc),
                tenant_id=tenant_id, user_id=user_id,
            ))
        return
    conn = sqlite3.connect(config.MEMORY_DB)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO chat_history (role, message, timestamp, tenant_id, user_id) VALUES (?, ?, ?, ?, ?)",
        (role, message, datetime.now().isoformat(), tenant_id, user_id),
    )
    conn.commit()
    conn.close()


def get_recent_history(limit: int = 10, tenant_id: str = "personal", user_id: str = "personal-user"):
    """Recent 'limit' messages wapas laata hai - context ke liye use hota hai."""
    if storage.enabled():
        from sqlalchemy import select
        table = storage.table("chat_history")
        with storage.init().connect() as conn:
            rows = conn.execute(
                select(table.c.role, table.c.message)
                .where(table.c.tenant_id == tenant_id, table.c.user_id == user_id)
                .order_by(table.c.id.desc()).limit(limit)
            ).fetchall()
        return list(reversed([(row[0], row[1]) for row in rows]))
    conn = sqlite3.connect(config.MEMORY_DB)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT role, message FROM chat_history WHERE tenant_id=? AND user_id=? ORDER BY id DESC LIMIT ?",
        (tenant_id, user_id, limit),
    )
    rows = cursor.fetchall()
    conn.close()
    return list(reversed(rows))  # purane se naye order mein


def clear_history(tenant_id: str = "personal", user_id: str = "personal-user"):
    """Poori history delete kar deta hai (fresh start ke liye)."""
    if storage.enabled():
        table = storage.table("chat_history")
        with storage.init().begin() as conn:
            conn.execute(table.delete().where(table.c.tenant_id == tenant_id, table.c.user_id == user_id))
        return
    conn = sqlite3.connect(config.MEMORY_DB)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM chat_history WHERE tenant_id=? AND user_id=?", (tenant_id, user_id))
    conn.commit()
    conn.close()
