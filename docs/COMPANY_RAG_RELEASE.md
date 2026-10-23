# Company RAG release boundary

This repository is scoped as a company-private RAG foundation. The supported
runtime flow is:

1. An administrator configures a reviewed host/NAS mount.
2. Docker mounts it read-only at `/company-share`.
3. The administrator opens `/admin` and runs a sync.
4. Documents are indexed with tenant, department and source metadata.
5. Users ask questions; retrieval is filtered by their authorization scope.
6. Answers include source provenance where available.

## Safe defaults

- Company mode is the default.
- File-server indexing is read-only.
- Upload and delete operations are administrator-only in company mode.
- Cloud document context is disabled by default.
- External action connectors are disabled until configured and approval-gated.
- API authentication is required in production.

## Real-company configuration

Set `COMPANY_DATA_HOST_PATH` in the deployment environment to a reviewed local
folder or mounted SMB/NFS path. Do not put provider passwords in this folder.
Use Docker secrets/Vault for credentials and keep the mount read-only.

## Not claimed by this release

This does not claim that OIDC, Vault, TLS certificates, cloud-drive adapters,
ERP/CRM adapters, backups or penetration testing have been completed. Those
require the company's real infrastructure, policy decisions and credentials.
