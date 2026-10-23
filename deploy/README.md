# Private deployment

1. Copy `.env.example` to `.env` and set a strong `POSTGRES_PASSWORD` and
   production API identity settings. Do not commit `.env`.
   The deployment defaults to `PRODUCT_MODE=company`.
2. Put the GGUF model under `models/` or mount it read-only.
3. Review `API_CORS_ORIGINS`, `COMPANY_DATA_ROOT`, TLS and firewall rules.
4. Start the stack with Docker Compose:

```bash
docker compose -f deploy/docker-compose.yml up -d --build
```

5. Verify `/health/live` and `/health/ready` before exposing the frontend.

The default Compose stack is local-only. If an approved data-processing policy
allows Groq, create `deploy/secrets/groq_api_key` and explicitly use the
cloud override:

```bash
docker compose -f deploy/docker-compose.yml \
  -f deploy/docker-compose.groq.yml up -d --build
```

Do not put the Groq key in the frontend or commit the secret file. The base
stack keeps `ALLOW_CLOUD_PROVIDERS=false` by design.

For TLS, copy `nginx.tls.conf.example`, replace `DOMAIN`, mount the certificate
directory read-only into the frontend container, and use that configuration.
The sample Compose file also starts Redis for shared rate limiting.

The sample compose file is intended for a private on-prem pilot. For a real
enterprise deployment, replace the compose-managed PostgreSQL password and
application secrets with Docker/Kubernetes secrets or a Vault integration,
put the frontend/API behind TLS, and configure OIDC/JWT.

The enterprise connector contracts, disabled-by-default integration registry,
and acceptance gates are documented in `../enterprise/README.md` and
`../docs/ENTERPRISE_ROADMAP.md`. Use `docker-compose.company.example.yml` only
after reviewing the host share path and read-only permissions.

Use `backup.ps1`/`backup.sh` for a PostgreSQL custom-format backup. Restore is
destructive and requires an explicit confirmation flag; test restore regularly
in an isolated environment.
