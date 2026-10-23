# Security and privacy baseline

This project is designed for a private, self-hosted deployment. It is not a
claim that an LLM can make sensitive data risk-free; the deployment boundary,
identity system, operating system and network controls remain essential.

## Safe defaults

- Cloud LLM providers are disabled unless `ALLOW_CLOUD_PROVIDERS=true`.
- Local-only mode also disables Tavily web search, Groq transcription and
  Google TTS because those services receive data outside the host.
- Production API requests require a bearer identity token.
- Chat, long-term memory, reminders and vector stores carry tenant/user scope.
- External side effects such as email enter an approval queue first.
- Audit events avoid storing raw questions, message bodies and credentials.

## Production deployment requirements

1. Run the API and model on a private network or on-prem host.
2. Use OIDC/JWT or an enterprise identity provider with `OIDC_JWKS_URL`,
   `OIDC_ISSUER`, `OIDC_AUDIENCE`, and a tenant claim; bootstrap token mapping
   is only for a controlled private installation. OIDC-only production mode is
   supported; no long-lived API token is required in that mode.
3. Give the service account read-only access to company shares by default.
4. Encrypt disks, backups and database volumes; keep secrets in a vault.
5. Keep `ALLOW_CLOUD_PROVIDERS=false` unless a documented data-processing
   policy allows a specific provider.
6. Restrict `API_CORS_ORIGINS` to the exact frontend origin.
7. Put the API behind TLS, a reverse proxy, rate limiting and network ACLs.
   Set `REDIS_URL` for a shared limiter when running multiple API replicas;
   without it, the built-in limiter is only a per-process safety net.
8. Review audit events and pending actions; require a human for irreversible
   actions, payments, external messages and document deletion.
9. Never store passwords, CVV, OTPs or raw payment-card data. Use a compliant
   payment provider/tokenization service instead.
10. Run dependency scanning, backup/restore tests, authorization tests and a
    penetration test before handling real customer data.

## Connector rule

Every new connector must enforce the authenticated principal's tenant and
user/department permissions before returning data. A connector must not pass
whole repositories to the LLM; it should return only the minimum authorized
records needed for the request and must record access in the audit log.

The built-in WhatsApp, calendar, CRM, booking and payment actions are
provider-neutral and approval-gated. They call administrator-configured HTTPS
connector gateways only after approval. Payment actions carry amount/currency
and description, never card numbers, CVV, OTP or PIN.
