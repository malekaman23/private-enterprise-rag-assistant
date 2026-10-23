# Company RAG access model

Company tenants use deny-by-default document retrieval. Every approved chunk
has a `required_role` and optional `department_id`; the same policy is used
for vector search, document listing, and downloads.

## Audiences

- `shared`: approved company-wide information
- `employee`: normal employee information
- `manager`: manager and operational information
- `hr`, `finance`, `sales`: department-specific information
- `executive`: leadership information
- `admin`: unrestricted administration

An employee upload is written to `data/quarantine/<tenant>/` and creates a
pending submission. It is not indexed or searchable until an administrator
approves it. Rejection removes the quarantined copy and records an audit event.

The approval operation assigns the requested category, role and department to
the indexed chunks. An employee cannot assign another department or bypass
approval. Existing source-server mounts remain read-only.

For a demo, use `API_TOKENS_JSON` with synthetic tokens. For production,
replace it with OIDC/JWKS and claims for `tenant_id`, `roles`, and
`departments`. Do not put real credentials or real company documents in a
public demo.
