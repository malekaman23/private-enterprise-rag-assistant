"""
tools.py
--------
Yeh saare "Tools" define karta hai jo LLM khud call kar sakta hai
jab user koi ACTION maange (sirf information nahi).

@tool decorator LangChain ko batata hai "ye ek function hai jo
LLM ko dikhega, aur LLM decide karega isko kab call karna hai."
"""

from contextvars import ContextVar
from datetime import datetime

from langchain_core.tools import tool

import config
import reminders as reminders_db
import action_store
import audit_log
import integration_actions

_tenant_id = ContextVar("assistant_tenant_id", default="personal")
_user_id = ContextVar("assistant_user_id", default="personal-user")


def set_execution_scope(tenant_id: str, user_id: str):
    _tenant_id.set(tenant_id)
    _user_id.set(user_id)


@tool
def send_email(to_email: str, subject: str, body: str) -> str:
    """
    Ek email bhejta hai. Isko tabhi use karo jab user clearly
    email bhejne ko bole, aur to_email, subject, body pata ho.

    Args:
        to_email: Jisko email bhejni hai uska email address
        subject: Email ka subject
        body: Email ka message
    """
    if not config.EMAIL_ADDRESS or not config.EMAIL_APP_PASSWORD:
        return ("Email bhejne ke liye .env file mein EMAIL_ADDRESS aur "
                "EMAIL_APP_PASSWORD set nahi hai.")

    action_id = action_store.create_action(
        _tenant_id.get(), _user_id.get(), "send_email",
        {"to_email": to_email, "subject": subject, "body": body},
    )
    audit_log.record_event(
        _tenant_id.get(), _user_id.get(), "action.created", "pending",
        {"action_id": action_id, "action_type": "send_email", "recipient_hash": audit_log.digest(to_email)},
    )
    return f"Email direct nahi bheja gaya. Approval ke liye action #{action_id} queue mein hai."


@tool
def add_reminder(text: str, remind_at: str) -> str:
    """
    Ek naya reminder set karta hai.

    Args:
        text: Reminder ka content (kis baare mein yaad dilana hai)
        remind_at: Kab yaad dilana hai (e.g. '2026-09-20 10:00' ya 'kal shaam 6 baje')
    """
    return reminders_db.add_reminder(text, remind_at, _tenant_id.get(), _user_id.get())


@tool
def list_reminders() -> str:
    """Saare pending reminders ki list deta hai."""
    return reminders_db.list_reminders(tenant_id=_tenant_id.get(), user_id=_user_id.get())


@tool
def send_whatsapp_message(to: str, message: str) -> str:
    """WhatsApp Business message ko approval queue mein rakhta hai."""
    return integration_actions.queue_action(
        _tenant_id.get(), _user_id.get(), "send_whatsapp_message",
        {"to": to, "message": message},
    )


@tool
def create_calendar_event(title: str, start: str, end: str, attendees: str = "") -> str:
    """Calendar event ko approval queue mein rakhta hai."""
    return integration_actions.queue_action(
        _tenant_id.get(), _user_id.get(), "create_calendar_event",
        {"title": title, "start": start, "end": end, "attendees": attendees},
    )


@tool
def update_crm_record(record_type: str, record_id: str, fields_json: str) -> str:
    """CRM update ko approval queue mein rakhta hai."""
    return integration_actions.queue_action(
        _tenant_id.get(), _user_id.get(), "update_crm_record",
        {"record_type": record_type, "record_id": record_id, "fields_json": fields_json},
    )


@tool
def create_booking(service: str, start: str, customer: str, notes: str = "") -> str:
    """Booking request ko approval queue mein rakhta hai."""
    return integration_actions.queue_action(
        _tenant_id.get(), _user_id.get(), "create_booking",
        {"service": service, "start": start, "customer": customer, "notes": notes},
    )


@tool
def create_payment_link(amount: str, currency: str, description: str) -> str:
    """Payment-link request queue karta hai; raw card data kabhi accept nahi karta."""
    return integration_actions.queue_action(
        _tenant_id.get(), _user_id.get(), "create_payment_link",
        {"amount": amount, "currency": currency, "description": description},
    )


@tool
def get_current_datetime() -> str:
    """Aaj ki date aur current time deta hai."""
    return datetime.now().strftime("%A, %d %B %Y, %I:%M %p")


# Saare tools ki list - agent ko yahi list di jaayegi
ALL_TOOLS = [
    send_email, add_reminder, list_reminders, get_current_datetime,
    send_whatsapp_message, create_calendar_event, update_crm_record,
    create_booking, create_payment_link,
]
