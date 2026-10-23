"""Minimal identity boundary for the API.

Production deployments can map multiple bearer tokens to separate principals
with API_TOKENS_JSON. A real deployment should replace this with OIDC/JWT
verification, but all downstream storage already receives tenant/user scope.
"""

import json
import os
import secrets
from dataclasses import dataclass

import config
from tenant_utils import DEFAULT_TENANT_ID, DEFAULT_USER_ID


@dataclass(frozen=True)
class Principal:
    tenant_id: str
    user_id: str
    roles: tuple[str, ...] = ()
    departments: tuple[str, ...] = ()


def _configured_tokens() -> dict:
    try:
        value = json.loads(config.API_TOKENS_JSON or "{}")
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def authenticate(token: str) -> Principal | None:
    """Resolve a bearer token without ever logging or returning the token."""
    if not token:
        return None

    # Local username/password sessions (used for the demo and small private
    # installs) are checked before static bootstrap tokens.
    try:
        from user_auth import principal_for_token
        principal = principal_for_token(token)
        if principal is not None:
            return principal
    except Exception:
        pass

    if config.DEMO_MODE:
        for identity in config.DEMO_USERS.values():
            if secrets.compare_digest(token, identity["token"]):
                return Principal(
                    tenant_id=getattr(config, "API_TENANT_ID", "company-demo"),
                    user_id=identity["user_id"],
                    roles=tuple(identity["roles"]),
                    departments=tuple(identity["departments"]),
                )

    # Enterprise mode: validate an OIDC JWT against the provider's JWKS.
    # PyJWT is imported lazily so the zero-cost local token mode stays usable
    # in minimal development environments.
    if config.OIDC_JWKS_URL:
        try:
            import jwt
            from jwt import PyJWKClient

            jwks_client = PyJWKClient(config.OIDC_JWKS_URL)
            signing_key = jwks_client.get_signing_key_from_jwt(token)
            decode_options = {
                "key": signing_key.key,
                "algorithms": ["RS256", "RS384", "RS512", "ES256", "ES384", "ES512"],
            }
            if config.OIDC_AUDIENCE:
                decode_options["audience"] = config.OIDC_AUDIENCE
            else:
                decode_options["options"] = {"verify_aud": False}
            if config.OIDC_ISSUER:
                decode_options["issuer"] = config.OIDC_ISSUER
            claims = jwt.decode(token, **decode_options)
            tenant_id = str(claims.get(config.OIDC_TENANT_CLAIM, "")).strip()
            user_id = str(claims.get("sub", "")).strip()
            roles_value = claims.get(config.OIDC_ROLES_CLAIM, [])
            if isinstance(roles_value, str):
                roles_value = [roles_value]
            departments_value = claims.get(config.OIDC_DEPARTMENTS_CLAIM, [])
            if isinstance(departments_value, str):
                departments_value = [departments_value]
            if tenant_id and user_id:
                return Principal(
                    tenant_id=tenant_id, user_id=user_id,
                    roles=tuple(map(str, roles_value)),
                    departments=tuple(map(str, departments_value)),
                )
        except Exception:
            # Fall through to the explicitly configured break-glass token, if
            # one exists. OIDC-only deployments still reject the token below.
            pass

    # Single-token deployments remain supported for a simple private install.
    if config.API_AUTH_TOKEN and secrets.compare_digest(token, config.API_AUTH_TOKEN):
        return Principal(
            tenant_id=getattr(config, "API_TENANT_ID", DEFAULT_TENANT_ID),
            user_id=getattr(config, "API_USER_ID", DEFAULT_USER_ID),
            roles=("admin",),
        )

    # Multi-principal bootstrap mode: {"secret": {"tenant_id": ..., ...}}
    for configured_token, identity in _configured_tokens().items():
        if not isinstance(identity, dict) or not secrets.compare_digest(token, configured_token):
            continue
        tenant_id = str(identity.get("tenant_id", "")).strip()
        user_id = str(identity.get("user_id", "")).strip()
        if not tenant_id or not user_id:
            return None
        roles = tuple(str(r) for r in identity.get("roles", []))
        departments = tuple(str(d) for d in identity.get("departments", []))
        return Principal(tenant_id=tenant_id, user_id=user_id, roles=roles, departments=departments)
    return None
