# Private Enterprise RAG Assistant

A production-like, privacy-focused RAG application for querying private company documents with role-based access control, administrator approval workflows and local/on-premise deployment.

## Project status

This repository is suitable for a private demo, development environment and on-premise staging deployment. It is not a certified enterprise production system yet.

Before using real sensitive company data in production, configure and verify:

- OIDC/JWT identity provider
- Vault or KMS-backed secret management
- TLS and a production reverse proxy
- PostgreSQL backup and restore drills
- Monitoring, alerting and incident response
- Independent penetration testing
- Production connector credentials and security reviews

## What the application does

- Answers questions about private PDF, DOCX, TXT and CSV documents
- Retrieves relevant document chunks using semantic search
- Shows source documents with answers
- Supports role- and department-based document access
- Keeps user chat history isolated
- Allows employees to submit documents for administrator approval
- Indexes employee submissions only after approval
- Provides admin user, role, department and document management
- Supports local GGUF models and optional Groq/OpenAI/Anthropic providers
- Uses PostgreSQL and Redis in the Docker deployment
- Provides read-only company-share/filesystem connector support
- Includes audit logging and approval-gated action foundations
- Supports light and dark UI themes

## Technology stack

- Frontend: React, Vite, Tailwind CSS, React Markdown
- Backend: Python, FastAPI and Uvicorn
- Retrieval: ChromaDB and Sentence Transformers
- Local inference: GGUF models through llama.cpp/LangChain
- Databases: PostgreSQL, Redis and local SQLite fallback
- Reverse proxy: Nginx
- Deployment: Docker Compose
- Authentication: password hashing and bearer sessions; OIDC/JWKS-ready foundation

## Architecture

```text
Browser
  -> React frontend
  -> Nginx reverse proxy
  -> FastAPI API
  -> Authentication and role/department ACL
  -> Document retrieval from ChromaDB
  -> Local LLM or explicitly enabled cloud provider
  -> Answer with permitted sources
```

## RAG pipeline

1. A user signs in and receives an authenticated session.
2. The API resolves the user's tenant, role and department.
3. Documents are validated and extracted from PDF, DOCX, TXT or CSV files.
4. Text is split into chunks and converted into embeddings.
5. Chunks are stored in ChromaDB with tenant, department, role and ownership metadata.
6. A question is filtered using the user's permissions before retrieval.
7. Only authorized chunks are sent to the answer-generation model.
8. The response includes source references where available.

## Role-based access

The access policy is deny-by-default and can distinguish between:

- Employee
- Sales
- HR
- Finance
- Manager
- Executive
- Administrator

Documents can be restricted by required role and department. Administrators can create, update, disable and remove users, manage roles and approve or reject submitted documents.

## Employee document workflow

1. An employee submits a document.
2. The document is stored in a quarantine area.
3. An administrator reviews the document and its access scope.
4. The administrator approves or rejects it.
5. Only approved documents are indexed into the RAG knowledge base.

## Privacy model

The recommended safe configuration is local-first:

```env
ALLOW_CLOUD_PROVIDERS=false
ALLOW_CLOUD_DOCUMENT_CONTEXT=false
```

With cloud document context disabled, private company document content is not sent to Groq or another cloud LLM. A local model processes confidential document questions. Groq can be enabled separately for general, non-document questions when the operator accepts that trade-off.

Never commit these files or values:

- `.env`
- `.env.enterprise`
- API keys and passwords
- `deploy/secrets/`
- Personal or real company documents
- Database files and vector indexes

Use synthetic demo data for public demonstrations.

## Run with Docker Compose

Create local configuration from the example files and provide local secrets under `deploy/secrets/`. Do not commit those files.

```powershell
docker compose --env-file .env -f deploy/docker-compose.yml up -d --build
docker compose -f deploy/docker-compose.yml ps
```

Open the application at:

```text
http://localhost
```

The API health endpoint is available through the frontend proxy:

```text
http://localhost/api/health/live
```

Stop the stack:

```powershell
docker compose -f deploy/docker-compose.yml down
```

## Local development

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m pytest -q
```

For the frontend:

```powershell
cd frontend
npm install
npm run dev
```

The Docker Compose deployment is the recommended way to run the complete application because it includes the frontend, API, PostgreSQL, Redis and Nginx services.

## Repository structure

```text
api.py                    FastAPI routes and application API
router_agent.py           Query routing and answer generation
document_processor.py     PDF/DOCX/TXT/CSV extraction and chunking
vector_store.py           ChromaDB indexing and permission-aware retrieval
access_policy.py          Role and department access rules
user_auth.py              Users, password hashing and sessions
document_submissions.py   Employee submission and approval workflow
llm_provider.py           Local and cloud LLM provider selection
privacy_guard.py          Privacy and cloud-context checks
frontend/                 React/Vite web interface
enterprise/               Connector and enterprise foundations
deploy/                   Docker Compose, Nginx and backup scripts
docs/                     Security, roadmap and release documentation
tests/                    Automated security and integration tests
demo-company-server/      Synthetic company demo data
employee-test-documents/  Synthetic role-based test documents
```

Runtime data such as databases, vector indexes, secrets and local model files should remain outside public source control.

## Testing

Run the test suite with:

```powershell
python -m pytest -q
```

The tests cover security foundations and authentication-related behavior. A real enterprise release also requires infrastructure tests, backup/restore verification and an independent security assessment.

## Important limitation

This project is a private, role-aware, document-centric RAG foundation. It should not be described as a fully autonomous enterprise agent until real company connectors, action approvals, OIDC, production secret management, TLS and operational controls have been configured and tested.

## License and demo data

The included company documents are synthetic demonstration data. Replace them only with data that you are authorized to process, and keep confidential data out of public repositories.
