"""Optional provider gateway executor for approved integration actions."""

import json
import urllib.error
import urllib.request

import config
from enterprise.connectors import get as get_connector, validate_enabled

URL_SETTINGS = {
    "send_whatsapp_message": "WHATSAPP_CONNECTOR_URL",
    "create_calendar_event": "CALENDAR_CONNECTOR_URL",
    "update_crm_record": "CRM_CONNECTOR_URL",
    "create_booking": "BOOKING_CONNECTOR_URL",
    "create_payment_link": "PAYMENT_CONNECTOR_URL",
}


def execute(action_type: str, payload: dict) -> str:
    spec = get_connector(action_type)
    url, token = validate_enabled(spec)

    body = json.dumps({"action_type": action_type, "payload": payload}).encode("utf-8")
    request = urllib.request.Request(
        url, data=body, method="POST",
        headers={"Content-Type": "application/json", "User-Agent": "private-ai-assistant/1.0"},
    )
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            if response.status < 200 or response.status >= 300:
                raise RuntimeError(f"Connector returned HTTP {response.status}")
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Connector returned HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError("Connector request failed") from exc
    return f"{action_type} connector action completed"
