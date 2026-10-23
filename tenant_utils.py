"""Small, dependency-free helpers for tenant/user scoped storage."""

import re


DEFAULT_TENANT_ID = "personal"
DEFAULT_USER_ID = "personal-user"


def safe_scope(value: str, fallback: str) -> str:
    """Turn an external identity into a safe directory/metadata component."""
    value = str(value or "").strip()
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", value)[:80]
    return cleaned or fallback

