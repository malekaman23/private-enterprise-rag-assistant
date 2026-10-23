"""Provider-neutral connector registry for approved external actions."""

from dataclasses import dataclass
from typing import Callable

import config


@dataclass(frozen=True)
class ConnectorSpec:
    name: str
    action_type: str
    url_setting: str
    token_setting: str
    description: str
    enabled_setting: str


CONNECTORS = (
    ConnectorSpec(
        "whatsapp", "send_whatsapp_message", "WHATSAPP_CONNECTOR_URL",
        "WHATSAPP_CONNECTOR_URL_TOKEN", "WhatsApp Business message gateway",
        "WHATSAPP_CONNECTOR_ENABLED",
    ),
    ConnectorSpec(
        "calendar", "create_calendar_event", "CALENDAR_CONNECTOR_URL",
        "CALENDAR_CONNECTOR_URL_TOKEN", "Calendar event gateway",
        "CALENDAR_CONNECTOR_ENABLED",
    ),
    ConnectorSpec(
        "crm", "update_crm_record", "CRM_CONNECTOR_URL",
        "CRM_CONNECTOR_URL_TOKEN", "CRM record gateway",
        "CRM_CONNECTOR_ENABLED",
    ),
    ConnectorSpec(
        "booking", "create_booking", "BOOKING_CONNECTOR_URL",
        "BOOKING_CONNECTOR_URL_TOKEN", "Booking gateway",
        "BOOKING_CONNECTOR_ENABLED",
    ),
    ConnectorSpec(
        "payment", "create_payment_link", "PAYMENT_CONNECTOR_URL",
        "PAYMENT_CONNECTOR_URL_TOKEN", "Payment-link gateway; raw card data prohibited",
        "PAYMENT_CONNECTOR_ENABLED",
    ),
)


def _truthy(value: object) -> bool:
    return str(value or "").lower() in {"1", "true", "yes", "on"}


def status() -> list[dict]:
    """Return safe connector metadata without URLs, tokens, or credentials."""
    result = []
    for spec in CONNECTORS:
        url = getattr(config, spec.url_setting, "")
        enabled = _truthy(getattr(config, spec.enabled_setting, "false"))
        configured = bool(url)
        result.append({
            "name": spec.name,
            "action_type": spec.action_type,
            "description": spec.description,
            "enabled": enabled and configured,
            "configured": configured,
            "requires_approval": True,
        })
    return result


def get(action_type: str) -> ConnectorSpec:
    for spec in CONNECTORS:
        if spec.action_type == action_type:
            return spec
    raise ValueError(f"Unsupported integration action: {action_type}")


def validate_enabled(spec: ConnectorSpec) -> tuple[str, str]:
    """Return endpoint/token only for an explicitly enabled connector."""
    url = str(getattr(config, spec.url_setting, "") or "").strip()
    token = str(getattr(config, spec.token_setting, "") or "").strip()
    if not _truthy(getattr(config, spec.enabled_setting, "false")):
        raise RuntimeError(f"{spec.name} connector is disabled by policy")
    if not url:
        raise RuntimeError(f"{spec.name} connector is not configured")
    if config.APP_ENV == "production" and not url.startswith("https://"):
        raise RuntimeError("Production connector URLs must use HTTPS")
    return url, token

