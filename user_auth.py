"""Local demo/company user directory and bearer-session service.

Passwords are stored as salted PBKDF2 hashes. Access tokens are stored only as
SHA-256 hashes. In a real company deployment this module can be replaced by
OIDC/Keycloak without changing the downstream Principal/ACL contract.
"""

import hashlib
import hmac
import os
import secrets
import sqlite3
from datetime import datetime, timezone

import config

DB_PATH = "memory/users.db"
ITERATIONS = 310_000


def _db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL,
        display_name TEXT NOT NULL, password_hash TEXT NOT NULL,
        tenant_id TEXT NOT NULL, roles TEXT NOT NULL, departments TEXT NOT NULL,
        enabled INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS sessions (
        token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL,
        expires_at TEXT NOT NULL, revoked INTEGER NOT NULL DEFAULT 0
    )""")
    conn.commit()
    return conn


def _hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, ITERATIONS)
    return f"pbkdf2${ITERATIONS}${salt.hex()}${digest.hex()}"


def _check_password(password: str, stored: str) -> bool:
    try:
        _, iterations, salt_hex, digest_hex = stored.split("$", 3)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), int(iterations))
        return hmac.compare_digest(digest.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


def _roles(value):
    return tuple(x.strip().lower() for x in str(value or "").split(",") if x.strip())


def ensure_demo_users():
    if not config.DEMO_MODE:
        return
    profiles = (
        ("admin", "Demo Administrator", "AdminDemo!2026", "admin", ""),
    )
    conn = _db()
    # Remove old convenience accounts once. All non-admin accounts must be
    # explicitly created by an administrator.
    conn.execute("CREATE TABLE IF NOT EXISTS system_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    if not conn.execute("SELECT 1 FROM system_meta WHERE key=?", ("demo_accounts_removed_v1",)).fetchone():
        conn.execute("DELETE FROM sessions WHERE user_id IN (SELECT id FROM users WHERE username IN ('employee', 'sales'))")
        conn.execute("DELETE FROM users WHERE username IN ('employee', 'sales')")
        conn.execute("INSERT INTO system_meta(key, value) VALUES(?, ?)", ("demo_accounts_removed_v1", datetime.now(timezone.utc).isoformat()))
    for username, name, password, roles, departments in profiles:
        if not conn.execute("SELECT 1 FROM users WHERE username=?", (username,)).fetchone():
            conn.execute("INSERT INTO users(username,display_name,password_hash,tenant_id,roles,departments,created_at) VALUES(?,?,?,?,?,?,?)",
                         (username, name, _hash_password(password), "company-demo", roles, departments, datetime.now(timezone.utc).isoformat()))
    conn.commit(); conn.close()


def create_user(username, display_name, password, roles, departments, tenant_id="company-demo"):
    username = username.strip().lower()
    if not username or len(password) < 10:
        raise ValueError("Username and a password of at least 10 characters are required")
    conn = _db()
    try:
        cur = conn.execute("INSERT INTO users(username,display_name,password_hash,tenant_id,roles,departments,created_at) VALUES(?,?,?,?,?,?,?)",
                           (username, display_name.strip() or username, _hash_password(password), tenant_id,
                            ",".join(_roles(roles)), ",".join(_roles(departments)), datetime.now(timezone.utc).isoformat()))
        conn.commit(); return cur.lastrowid
    except sqlite3.IntegrityError:
        raise ValueError("Username already exists")
    finally:
        conn.close()


def login(username: str, password: str):
    ensure_demo_users()
    conn = _db(); row = conn.execute("SELECT * FROM users WHERE username=? AND enabled=1", (username.strip().lower(),)).fetchone()
    if not row or not _check_password(password, row["password_hash"]):
        conn.close(); return None
    token = secrets.token_urlsafe(40)
    conn.execute("INSERT INTO sessions(token_hash,user_id,expires_at) VALUES(?,?,?)",
                 (hashlib.sha256(token.encode()).hexdigest(), row["id"], "2099-01-01T00:00:00+00:00"))
    conn.commit(); conn.close()
    return token


def principal_for_token(token: str):
    if not token:
        return None
    conn = _db()
    row = conn.execute("""SELECT u.* FROM sessions s JOIN users u ON u.id=s.user_id
        WHERE s.token_hash=? AND s.revoked=0 AND u.enabled=1""", (hashlib.sha256(token.encode()).hexdigest(),)).fetchone()
    conn.close()
    if not row:
        return None
    from auth import Principal
    return Principal(row["tenant_id"], row["username"], _roles(row["roles"]), _roles(row["departments"]))


def list_users(tenant_id):
    conn = _db(); rows = conn.execute("SELECT id,username,display_name,roles,departments,enabled,created_at FROM users WHERE tenant_id=? ORDER BY username", (tenant_id,)).fetchall(); conn.close()
    return [{"id": row["id"], "username": row["username"], "display_name": row["display_name"],
             "roles": list(_roles(row["roles"])), "departments": list(_roles(row["departments"])),
             "enabled": bool(row["enabled"]), "created_at": row["created_at"]} for row in rows]


def set_enabled(user_id: int, tenant_id: str, enabled: bool) -> bool:
    conn = _db(); cur = conn.execute("UPDATE users SET enabled=? WHERE id=? AND tenant_id=?", (1 if enabled else 0, user_id, tenant_id)); conn.commit(); changed = cur.rowcount == 1; conn.close(); return changed


def update_user(user_id: int, tenant_id: str, username: str, display_name: str,
                password: str | None, roles, departments) -> bool:
    username = username.strip().lower()
    if not username or (password is not None and password != "" and len(password) < 10):
        raise ValueError("Username is required and a new password must be at least 10 characters")
    conn = _db()
    try:
        current = conn.execute("SELECT id FROM users WHERE id=? AND tenant_id=?", (user_id, tenant_id)).fetchone()
        if not current:
            return False
        if password:
            conn.execute("UPDATE users SET username=?, display_name=?, password_hash=?, roles=?, departments=? WHERE id=? AND tenant_id=?",
                         (username, display_name.strip() or username, _hash_password(password), ",".join(_roles(roles)), ",".join(_roles(departments)), user_id, tenant_id))
            conn.execute("DELETE FROM sessions WHERE user_id=?", (user_id,))
        else:
            conn.execute("UPDATE users SET username=?, display_name=?, roles=?, departments=? WHERE id=? AND tenant_id=?",
                         (username, display_name.strip() or username, ",".join(_roles(roles)), ",".join(_roles(departments)), user_id, tenant_id))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        raise ValueError("Username already exists")
    finally:
        conn.close()


def delete_user(user_id: int, tenant_id: str) -> bool:
    conn = _db()
    conn.execute("DELETE FROM sessions WHERE user_id=?", (user_id,))
    cur = conn.execute("DELETE FROM users WHERE id=? AND tenant_id=?", (user_id, tenant_id))
    conn.commit(); conn.close()
    return cur.rowcount == 1
