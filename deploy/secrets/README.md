# Runtime secrets

Create these files on the deployment host. They are intentionally ignored by
git and must never be committed:

- `api_auth_token`: a long random token, or use OIDC and keep this as a break-glass token
- `database_url`: for example `postgresql+psycopg://assistant:<password>@postgres:5432/assistant`
- `postgres_password`: the same password used in `database_url`

Use a Vault/Kubernetes Secret provider instead of local files for a managed
enterprise deployment.
