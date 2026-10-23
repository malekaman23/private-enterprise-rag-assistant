"""Provider-neutral contracts for external integrations.

These actions are deliberately queued for approval. Provider credentials and
HTTP clients can be added later without changing the assistant's safety model.
"""

import re

import action_store
import audit_log

SUPPORTED_ACTIONS = {
    "send_whatsapp_message",
    "create_calendar_event",
    "update_crm_record",
    "create_booking",
    "create_payment_link",
}


def _reject_sensitive_payment_fields(payload: dict):
    forbidden = {"card_number", "cvv", "otp", "pin", "password", "bank_password"}
    if forbidden.intersection(payload):
        raise ValueError("Raw card, OTP, PIN or password fields are never accepted")


def queue_action(tenant_id: str, user_id: str, action_type: str, payload: dict) -> str:
    if action_type not in SUPPORTED_ACTIONS:
        raise ValueError("Unsupported integration action")
    _reject_sensitive_payment_fields(payload)
    action_id = action_store.create_action(tenant_id, user_id, action_type, payload)
    audit_log.record_event(
        tenant_id, user_id, "integration.action_created", "pending",
        {"action_id": action_id, "action_type": action_type},
    )
    return f"Action direct execute nahi hua. Approval ke liye action #{action_id} queue mein hai."

