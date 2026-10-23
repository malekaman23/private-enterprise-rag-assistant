"""Executes only already-approved actions."""

import smtplib
from email.mime.text import MIMEText

import config
import integration_executor


def execute_send_email(payload: dict) -> str:
    if not config.EMAIL_ADDRESS or not config.EMAIL_APP_PASSWORD:
        raise RuntimeError("Email credentials are not configured")
    to_email = str(payload.get("to_email", "")).strip()
    subject = str(payload.get("subject", ""))
    body = str(payload.get("body", ""))
    if not to_email or not subject or not body:
        raise ValueError("Email action is missing required fields")

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = config.EMAIL_ADDRESS
    msg["To"] = to_email
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(config.EMAIL_ADDRESS, config.EMAIL_APP_PASSWORD)
        server.sendmail(config.EMAIL_ADDRESS, to_email, msg.as_string())
    return f"Email sent to {to_email}"


def execute(action_type: str, payload: dict) -> str:
    if action_type == "send_email":
        return execute_send_email(payload)
    return integration_executor.execute(action_type, payload)
