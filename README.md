# 🧠 Company AI — Private Data RAG + Agent Foundation

## Enterprise status

The Docker deployment is a private on-prem pilot with tenant-aware storage, OIDC/JWKS-ready authentication, approval-gated external actions, Redis rate limiting, PostgreSQL persistence, audit logging, and a read-only company-share connector. Enterprise connector contracts and release gates are documented in `docs/ENTERPRISE_ROADMAP.md`.

Real OIDC, Vault, TLS, provider accounts, backup/restore drills, and penetration testing must be completed before production use with sensitive data.

Your own AI assistant that can answer from both your documents and the live web, and lets you switch from a free LLM to a paid one (Groq → OpenAI/Claude) without changing any code.

## Features

- 📄 Q&A over your own PDFs, Word docs, TXT and CSV files
- 🌐 Real-time web search (when the answer is not found in your documents)
- 🧭 Smart routing: the agent decides which source to use
- 🧠 Conversation memory: remembers earlier messages
- 🔌 Plug-and-play LLM: Groq (free), OpenAI, Claude, or a local model, switched by editing `.env`
- 🔐 Role-based access control, approval-gated actions, and audit logging
- 🏢 Multi-tenant storage and a read-only company-share (filesystem) connector
- 🐳 Docker Compose deployment with PostgreSQL, Redis and nginx

## Folder structure

```
.
├── app.py                  # Streamlit chat interface
├── api.py                  # FastAPI backend
├── config.py               # all settings
├── llm_provider.py         # LLM switching logic
├── document_processor.py   # loads and splits PDFs/docs
├── vector_store.py         # embeddings + ChromaDB search
├── web_search.py           # Tavily web search
├── memory.py               # SQLite chat history
├── long_term_memory.py     # vector-based long-term memory
├── router_agent.py         # main brain: decides the source and answers
├── auth.py, user_auth.py   # authentication
├── access_policy.py        # access control rules
├── audit_log.py            # audit logging
├── enterprise/             # enterprise connectors and data sources
├── frontend/               # React + Vite + Tailwind web UI
├── deploy/                 # Docker Compose stack, nginx, backup/restore scripts
├── docs/                   # roadmap, RBAC and release documentation
├── tests/
├── data/                   # put your files here (not tracked in Git)
├── vectorstore/            # auto-generated document index (not tracked)
├── memory/                 # auto-generated chat history (not tracked)
├── requirements.txt
└── .env.example
```

## Setup (step by step)

### 1. Create a virtual environment

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
```

### 2. Install the libraries

```bash
pip install -r requirements.txt
```

### 3. Set your API keys

```bash
cp .env.example .env
```

Then open `.env` and add your keys:

- **Groq** (free): https://console.groq.com/keys — just sign up and you get a key
- **Tavily** (free tier, for web search): https://tavily.com

These two are enough to run the whole system completely free.

To switch to OpenAI/Claude later, change only this in `.env`:

```
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-xxxxxxxx
```

Restart the app and nothing else needs to change.

### 4. Add your files

Put your PDFs, notes and documents in the `data/` folder.

### 5. Run the app

```bash
streamlit run app.py
```

It opens in your browser automatically (localhost:8501).

### 6. Process your documents

After the app opens, upload your files from the sidebar and click **Process Documents**. Once processed, you can ask questions about them.

## How it works (in simple words)

1. You ask a question.
2. The system decides whether the answer is in your documents, on the web, or needs both.
3. It retrieves the information from the right place.
4. The LLM (Groq/OpenAI/Claude/local) reads that information and writes a clear, accurate answer.
5. The whole conversation is saved in memory.

## Next steps you can add

- **Voice input/output**: add Whisper (speech-to-text) so you can talk to the assistant
- **Actions/tools**: send email, create calendar events (agentic upgrade)
- **Multi-user support**: for friends or a business
- **Better memory**: long-term, vector-based memory instead of only recent messages

## Privacy-first production mode

The safe default is local-first: cloud LLM providers are disabled unless you explicitly set `ALLOW_CLOUD_PROVIDERS=true`. If an older `.env` selects Groq/OpenAI/Claude while cloud is disabled, the application fails closed to the local provider. External web search, cloud voice transcription, and cloud text-to-speech are also disabled in local-only mode.

For a production FastAPI deployment, set:

```env
APP_ENV=production
API_AUTH_TOKEN=use-a-long-random-secret
API_CORS_ORIGINS=https://your-frontend.example.com
ALLOW_CLOUD_PROVIDERS=false
LOCAL_MODEL_PATH=models/Llama-3.2-3B-Instruct-Q4_K_M.gguf
COMPANY_DATA_ROOT=/mounted/company-share
```

Clients must send `Authorization: Bearer <API_AUTH_TOKEN>`. This is only the first security layer. Before handling real company data, add identity-based user/tenant isolation, document ACLs, encrypted storage, secret management, audit logs, connector-specific permissions, and human approval for external actions such as email, booking, messaging, and payment.

For a small multi-user private deployment, `API_TOKENS_JSON` can map separate bearer tokens to separate `tenant_id`, `user_id`, and `roles` values. Replace this bootstrap mechanism with an OIDC/JWT identity provider before exposing the service to the public internet.

The filesystem connector is read-only and indexes a mounted local/NAS folder. After setting `COMPANY_DATA_ROOT`, an administrator can call `POST /api/connectors/filesystem/sync`. The folder must already be mounted on the same private host; the connector does not upload the source files to a third-party service.

Authorized documents can be downloaded through `GET /api/documents/download?filename=...`; the API checks the authenticated tenant/user visibility before serving the file.

## Container deployment

The `deploy/` directory contains a private backend/frontend/PostgreSQL Compose stack, health probes and deployment notes. It is suitable for an on-prem pilot; enterprise production still requires TLS, secret management, OIDC, backups and an operational monitoring setup.

## Troubleshooting

- **"API key error"**: check your `.env` file and make sure the key was copied correctly
- **"Module not found"**: run `pip install -r requirements.txt` again
- **Slow response**: Groq is the fastest of the free options; OpenAI/Claude may be a bit slower
