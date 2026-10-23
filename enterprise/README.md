# Enterprise integration boundary

The assistant owns identity, tenant/department filtering, approval queues,
audit events, and the RAG index. External systems are reached only through a
connector gateway. Each connector is disabled by default and every side-effect
action requires an administrator approval before execution.

Supported contracts:

- `send_whatsapp_message`
- `create_calendar_event`
- `update_crm_record`
- `create_booking`
- `create_payment_link`

The gateway payload is provider-neutral:

```json
{"action_type":"create_calendar_event","payload":{}}
```

Deploy a small private gateway per organisation to translate that contract to
Meta WhatsApp, Google/Microsoft Calendar, CRM, booking, or payment APIs. Do not
put provider credentials in this repository. Enable a connector only after
TLS, allowlisting, secret rotation, webhook verification, audit retention, and
human approval are configured.

