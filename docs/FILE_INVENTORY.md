# File inventory

## Runtime RAG components

`api.py`, `router_agent.py`, `document_processor.py`, `vector_store.py`,
`connectors.py`, `auth.py`, `tenant_utils.py`, `config.py`, `llm_provider.py`,
`privacy_guard.py`, `deploy/`, `frontend/`, `enterprise/` and the test suite
are part of the current company RAG runtime or release checks.

## Optional capabilities

`voice_tools.py`, `web_search.py`, reminders and action/integration modules are
optional capabilities. They are kept because imports and approval workflows
still reference them; removing them without a dependency migration would break
the application.

## Operational utilities

The PowerShell repair scripts are host recovery utilities, not application
runtime. They are intentionally retained outside the container image so a
Docker/WSL recovery remains possible.

Do not delete `.env`, `deploy/secrets/`, `models/`, `data/`, `memory/` or
`vectorstore/` during cleanup; they contain credentials, model assets or
application state.
