"""Role and department policy for company RAG documents.

This is deliberately deny-by-default for non-personal tenants.  A document's
``required_role`` and ``department_id`` are stored in vector metadata and are
checked before retrieval, listing, or download.
"""

ROLE_ORDER = {
    "viewer": 0,
    "employee": 10,
    "hr": 40,
    "finance": 40,
    "sales": 40,
    "manager": 50,
    "executive": 80,
    "admin": 100,
}

ROLE_ALIASES = {
    "administrator": "admin",
    "superadmin": "admin",
    "main_employee": "executive",
    "senior_employee": "manager",
    "normal_employee": "employee",
}

VALID_REQUIRED_ROLES = set(ROLE_ORDER) | {"shared"}


def normalize_roles(roles: tuple[str, ...] | list[str] | None) -> set[str]:
    result = set()
    for role in roles or ():
        value = ROLE_ALIASES.get(str(role).strip().lower(), str(role).strip().lower())
        if value in VALID_REQUIRED_ROLES:
            result.add(value)
    return result or {"employee"}


def is_admin(roles) -> bool:
    return "admin" in normalize_roles(roles)


def allowed_required_roles(roles, departments=()) -> set[str]:
    """Return document audiences visible to this principal."""
    current = normalize_roles(roles)
    if "admin" in current:
        return set(VALID_REQUIRED_ROLES)
    if "executive" in current:
        return {"shared", "employee", "hr", "finance", "sales", "manager", "executive"}
    visible = {"shared", "employee"}
    if "manager" in current:
        visible.add("manager")
        visible.update({str(item).strip().lower() for item in departments if str(item).strip().lower() in {"hr", "finance", "sales"}})
    for role in ("hr", "finance", "sales"):
        if role in current:
            visible.add(role)
    return visible


def default_required_role(category: str, department: str = "") -> str:
    """Conservative audience for common company categories."""
    value = (category or "").strip().lower()
    department_value = (department or "").strip().lower()
    for role in ("hr", "finance", "sales"):
        if role in value or role in department_value:
            return role
    if any(word in value for word in ("it", "security", "legal")) or any(
        word in department_value for word in ("it", "security", "legal")
    ):
        return "manager"
    if any(word in value for word in ("executive", "management", "board", "strategy")):
        return "executive"
    if any(word in value for word in ("manager", "operations", "internal")):
        return "manager"
    return "shared"


def validate_required_role(value: str) -> str:
    normalized = ROLE_ALIASES.get((value or "shared").strip().lower(), (value or "shared").strip().lower())
    if normalized not in VALID_REQUIRED_ROLES:
        raise ValueError("Invalid document access role")
    return normalized


def accessible_departments(roles, departments: tuple[str, ...] = ()) -> set[str]:
    current = normalize_roles(roles)
    if current & {"admin", "executive"}:
        return {"*"}
    result = {str(item).strip().lower() for item in departments if str(item).strip()}
    result.update(current & {"hr", "finance", "sales"})
    return result
