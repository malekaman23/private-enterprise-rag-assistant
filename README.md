# 🧠 Company AI — Private Data RAG + Agent Foundation

## Enterprise status

The Docker deployment is a private on-prem pilot with tenant-aware storage,
OIDC/JWKS-ready authentication, approval-gated external actions, Redis rate
limiting, PostgreSQL persistence, audit logging, and a read-only company-share
connector. Enterprise connector contracts and release gates are documented in
`docs/ENTERPRISE_ROADMAP.md`. Real OIDC, Vault, TLS, provider accounts,
backup/restore drills, and penetration testing must be completed before
production use with sensitive data.

Apna khud ka AI assistant jo tumhare documents aur live web dono se
jawab de sakta hai — aur jab chaho, free se paid LLM (Groq → OpenAI/Claude)
pe bina code badle switch kar sakte ho.

## Features
- 📄 Apni PDFs, Word docs, TXT, CSV files se Q&A
- 🌐 Real-time web search (jab documents mein answer na mile)
- 🧭 Smart routing — khud decide karta hai kaunsa source use karna hai
- 🧠 Conversation memory — purani baatein yaad rakhta hai
- 🔌 Plug-and-play LLM — Groq (free), OpenAI, ya Claude — sirf `.env` change karo

## Folder Structure
```
personal-ai-assistant/
├── app.py                 # Streamlit chat interface
├── config.py               # saari settings yahan hain
├── llm_provider.py          # LLM switch karne ka logic
├── document_processor.py    # PDFs/docs load + split karta hai
├── vector_store.py           # embeddings + ChromaDB search
├── web_search.py              # Tavily web search
├── memory.py                   # SQLite chat history
├── router_agent.py              # main brain - decide + answer
├── data/                          # apni files yaha daalo
├── vectorstore/                    # auto-generated (documents ka data)
├── memory/                          # auto-generated (chat history)
├── requirements.txt
└── .env.example
```

## Setup (Step-by-Step)

### 1. Virtual environment banao
```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
```

### 2. Libraries install karo
```bash
pip install -r requirements.txt
```

### 3. API Keys set karo
```bash
cp .env.example .env
```
Fir `.env` file kholo aur apni keys daalo:
- **Groq** (FREE): https://console.groq.com/keys — bas signup karo, key mil jayegi
- **Tavily** (FREE tier, web search ke liye): https://tavily.com

Bas inhi do se poora system chal jayega, bilkul free mein.

Baad mein agar OpenAI/Claude pe shift hona ho, to sirf `.env` mein:
```
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-xxxxxxxx
```
— itna karke app restart karo, baaki kuch change nahi karna.

### 4. Apni files daalo
`data/` folder mein apni PDFs, notes, docs daal do.

### 5. App chalao
```bash
streamlit run app.py
```
Browser mein automatically khul jayega (localhost:8501).

### 6. Documents process karo
App khulne ke baad, sidebar se apni files upload karo aur
"Process Documents" button dabao. Ek baar process hone ke baad,
unse related koi bhi sawal puchh sakte ho.

## Kaise Kaam Karta Hai (Simple Words Mein)

1. Tum sawal poochte ho
2. System decide karta hai — iska jawab tumhare documents mein hai,
   web pe hai, ya dono chahiye
3. Sahi jagah se information nikalta hai
4. LLM (Groq/OpenAI/Claude) us information ko padh ke ek saaf,
   accurate jawab banata hai
5. Poori baatcheet memory mein save ho jaati hai

## Aage Kya Add Kar Sakte Ho (Next Steps)
- **Voice input/output** — Whisper (speech-to-text) add karke bol ke baat kar sako
- **Actions/Tools** — Email bhejna, calendar mein event banana (Agentic upgrade)
- **Multi-user support** — agar doston/business ke liye bhi banana ho
- **Better memory** — sirf recent messages nahi, "long-term memory" (vector-based) add karna

## Privacy-first production mode

The safe default is now local-first: cloud LLM providers are disabled unless
you explicitly set `ALLOW_CLOUD_PROVIDERS=true`. If an older `.env` selects
Groq/OpenAI/Claude while cloud is disabled, the application fails closed to
the local provider. External web search, cloud voice transcription, and cloud
text-to-speech are also disabled in local-only mode.

For a production FastAPI deployment, set:

```env
APP_ENV=production
API_AUTH_TOKEN=use-a-long-random-secret
API_CORS_ORIGINS=https://your-frontend.example.com
ALLOW_CLOUD_PROVIDERS=false
LOCAL_MODEL_PATH=models/Llama-3.2-3B-Instruct-Q4_K_M.gguf
COMPANY_DATA_ROOT=/mounted/company-share
```

Clients must send `Authorization: Bearer <API_AUTH_TOKEN>`. This is only the
first security layer. Before handling real company data, add identity-based
user/tenant isolation, document ACLs, encrypted storage, secret management,
audit logs, connector-specific permissions, and human approval for external
actions such as email, booking, messaging, and payment.

For a small multi-user private deployment, `API_TOKENS_JSON` can map separate
bearer tokens to separate `tenant_id`, `user_id`, and `roles` values. Replace
this bootstrap mechanism with an OIDC/JWT identity provider before exposing
the service to the public internet.

The filesystem connector is read-only and indexes a mounted local/NAS folder.
After setting `COMPANY_DATA_ROOT`, an administrator can call
`POST /api/connectors/filesystem/sync`. The folder must already be mounted on
the same private host; the connector does not upload the source files to a
third-party service.

Authorized documents can be downloaded through
`GET /api/documents/download?filename=...`; the API checks the authenticated
tenant/user visibility before serving the file.

## Container deployment

The `deploy/` directory contains a private backend/frontend/PostgreSQL Compose
stack, health probes and deployment notes. It is suitable for an on-prem pilot;
enterprise production still requires TLS, secret management, OIDC, backups and
an operational monitoring setup.

## Troubleshooting
- **"API key error"** → `.env` file check karo, key sahi se copy hui hai ya nahi
- **"Module not found"** → `pip install -r requirements.txt` dubara chalao
- **Slow response** → Groq sabse fast hai free options mein; OpenAI/Claude thode slow ho sakte hain
