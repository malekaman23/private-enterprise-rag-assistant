# Enterprise readiness roadmap

This project is currently a private on-prem pilot. The Docker stack, local
RAG, bearer-token bootstrap, Redis limiter, PostgreSQL persistence, audit log,
approval queue, and read-only filesystem connector are implemented. The gates
below define what must be completed before handling real company or personal
financial data.

## Gate 0 — Local acceptance

- [x] Docker Compose builds and all services become healthy.
- [x] API authentication is required in production mode.
- [x] Documents are tenant-scoped and department/role-aware in vector metadata.
- [x] Employee uploads use quarantine plus administrator approval before indexing.
- [x] External side effects are approval-gated.
- [x] PostgreSQL and Redis are used by the deployment stack.
- [ ] Run the full smoke test after every image build.

## Gate 1 — Identity and authorization

- [x] OIDC/JWKS validation code and tenant/user/department claims exist.
- [ ] Test against the organisation's real IdP in staging.
- [ ] Deny tokens with wrong issuer, audience, tenant, expired signature, or
  missing subject in an integration test.
- [ ] Replace the bootstrap bearer token for production users.
- [ ] Verify every document, history, reminder, action, audit, and connector
  request with a multi-user ACL test matrix.

## Data-source coverage

The source catalog in `enterprise/data_sources.py` intentionally covers the
common locations where a company may keep data: local folders, SMB/NAS, NFS,
S3-compatible storage, Azure Blob, GCS, SharePoint/OneDrive, Google Drive,
Dropbox/Box, SQL databases, ERP/CRM, and private APIs. A source must be
connected through an approved read-only gateway, mapped to tenant/department
ACLs, indexed with provenance, and re-synced with deletion/change detection.
The catalog is not a claim that credentials or provider access are configured.

## Gate 2 — Secrets, network, and data protection

- [x] Docker secrets paths are supported and cloud providers fail closed.
- [ ] Use Vault/KMS or Kubernetes Secrets in production; rotate all existing
  development credentials first.
- [ ] TLS at a reverse proxy with HSTS, secure cookies, and restricted CORS.
- [ ] Encrypt PostgreSQL, backups, NAS shares, and host disks according to the
  organisation policy.
- [ ] Define retention/deletion/legal-hold rules for documents, embeddings,
  chat, audit data, and connector payloads.

## Gate 3 — Reliability and operations

- [ ] PostgreSQL backup and isolated restore drill, with measured RPO/RTO.
- [ ] Redis failure behavior and API-gateway rate-limit test.
- [ ] Centralized structured logs, metrics, traces, alerting, and on-call runbook.
- [ ] Health/readiness, graceful shutdown, worker count, resource limits, and
  capacity test with realistic document volumes.
- [ ] Disaster recovery test from a clean host.

## Gate 4 — Connector rollout

The code exposes provider-neutral, disabled-by-default contracts in
`enterprise/connectors.py`. For each connector, deploy a private gateway and
complete: sandbox test, HTTPS allowlist, secret rotation, webhook signature
verification, idempotency, approval test, audit test, retry/dead-letter test,
and least-privilege provider scopes.

- [ ] WhatsApp Business API
- [ ] Calendar (Google/Microsoft)
- [ ] CRM
- [ ] Booking
- [ ] Payment links only; never accept raw card/CVV/OTP/PIN data

## Gate 5 — Security assurance

- [ ] Dependency and image scanning in CI.
- [ ] SAST/secret scan and container hardening.
- [ ] Threat model covering prompt injection, data exfiltration, SSRF,
  cross-tenant access, malicious files, and connector replay.
- [ ] Independent penetration test and remediation report.
- [ ] Privacy impact assessment and incident-response exercise.

## Performance note

The bundled 3B GGUF model is suitable for private functional testing but is
not ChatGPT-speed on a CPU-only laptop. Production latency requires a GPU,
an on-prem inference server, or an approved cloud provider. Benchmark p50/p95
latency, context size, concurrent users, and document ingestion before choosing
the model and worker topology.

