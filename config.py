"""
config.py
---------
Yeh file poore project ki settings control karti hai.
LLM provider badalne ke liye sirf .env file mein LLM_PROVIDER value change karo:
    LLM_PROVIDER=local     -> 100% FREE, 100% LOCAL, EMBEDDED (fastest local option) - koi alag app nahi chahiye
    LLM_PROVIDER=ollama    -> 100% FREE, 100% LOCAL - Ollama app chahiye background mein
    LLM_PROVIDER=groq      -> free, fast, lekin data Groq ke server pe jata hai
    LLM_PROVIDER=openai    -> paid, best quality
    LLM_PROVIDER=anthropic -> paid, best quality (Claude)

Baki pura code bina kisi change ke automatically naya provider use karega.
"""

import os
from dotenv import load_dotenv

load_dotenv()  # .env file se saari keys load karega


def _setting(name: str, default: str = "") -> str:
    """Read a setting or its *_FILE secret-file counterpart."""
    value = os.getenv(name, "")
    if value:
        return value
    file_path = os.getenv(f"{name}_FILE", "")
    if file_path:
        try:
            with open(file_path, "r", encoding="utf-8") as secret_file:
                return secret_file.read().strip()
        except OSError:
            return default
    return default

# ---- LLM Provider Settings ----
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "local").lower()  # privacy-first default

# Cloud providers are opt-in.  A production deployment should keep this false
# unless its data policy explicitly allows sending prompts/context off-host.
ALLOW_CLOUD_PROVIDERS = os.getenv("ALLOW_CLOUD_PROVIDERS", "false").lower() in {
    "1", "true", "yes", "on"
}
# Never send retrieved company documents to a cloud model by default.
ALLOW_CLOUD_DOCUMENT_CONTEXT = os.getenv("ALLOW_CLOUD_DOCUMENT_CONTEXT", "false").lower() in {
    "1", "true", "yes", "on"
}

# If an old .env still says groq/openai/anthropic while cloud is disabled,
# fail closed by selecting the local provider instead of leaking data.
if LLM_PROVIDER in {"groq", "openai", "anthropic"} and not ALLOW_CLOUD_PROVIDERS:
    LLM_PROVIDER = "local"

# API Keys (jo use nahi ho rahi wo blank rakh sakte ho)
GROQ_API_KEY = _setting("GROQ_API_KEY")
OPENAI_API_KEY = _setting("OPENAI_API_KEY")
ANTHROPIC_API_KEY = _setting("ANTHROPIC_API_KEY")
TAVILY_API_KEY = _setting("TAVILY_API_KEY")  # web search ke liye

# Ollama - LOCAL LLM, koi API key nahi chahiye (bas Ollama app installed hona chahiye)
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1")

# Local Embedded Model - Ollama jaisa koi alag app nahi chahiye, model file
# seedha is Python process ke andar load hoti hai (fastest local option,
# especially chhote models ke saath jo weak/no-GPU laptops pe bhi fast chalein)
LOCAL_MODEL_PATH = os.getenv(
    "LOCAL_MODEL_PATH", "models/Llama-3.2-3B-Instruct-Q4_K_M.gguf"
)
LOCAL_MODEL_CONTEXT = int(os.getenv("LOCAL_MODEL_CONTEXT", "4096"))
LOCAL_MODEL_THREADS = int(os.getenv("LOCAL_MODEL_THREADS", str(os.cpu_count() or 4)))

# Email (send_email tool ke liye - Gmail App Password use karo, normal password nahi)
EMAIL_ADDRESS = _setting("EMAIL_ADDRESS")
EMAIL_APP_PASSWORD = _setting("EMAIL_APP_PASSWORD")

# ---- Model Names (provider ke hisab se) ----
MODEL_NAMES = {
    "groq": "openai/gpt-oss-120b",
    "openai": "gpt-4o-mini",
    "anthropic": "claude-sonnet-4-6",
    "ollama": OLLAMA_MODEL,
    "local": os.path.basename(LOCAL_MODEL_PATH),
}

# ---- Embedding Model (documents ko vector banane ke liye) ----
# Yeh hamesha free/local rahega, chahe LLM koi bhi ho
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# ---- Paths ----
DATA_DIR = "data"                # yaha apni PDFs/docs daalo
VECTORSTORE_DIR = "vectorstore"  # processed data yaha store hoga
MEMORY_DB = "memory/chat_history.db"  # conversation history yaha save hogi

# ---- RAG Settings ----
CHUNK_SIZE = 800        # document ko kitne bade tukdo mein todna hai
CHUNK_OVERLAP = 100     # tukdo ke beech overlap (context na tute isliye)
TOP_K_RESULTS = 4       # kitne relevant chunks LLM ko dene hain

# ---- Web Search Settings ----
WEB_SEARCH_RESULTS = 5  # kitne web results laane hain

# Network/file safety limits.  Keep these conservative and tune per deployment.
MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "50"))
MAX_CONNECTOR_FILE_SIZE_MB = int(os.getenv("MAX_CONNECTOR_FILE_SIZE_MB", "100"))
ALLOWED_UPLOAD_EXTENSIONS = {"pdf", "docx", "txt", "csv"}
API_CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("API_CORS_ORIGINS", "http://localhost:5173").split(",")
    if origin.strip()
]
APP_ENV = os.getenv("APP_ENV", "development").lower()
PRODUCT_MODE = os.getenv("PRODUCT_MODE", "company").strip().lower()
if PRODUCT_MODE not in {"company", "personal", "hybrid"}:
    PRODUCT_MODE = "company"
DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() in {"1", "true", "yes", "on"}
DEMO_USERS = {
    "employee": {"token": "demo-employee-token", "user_id": "demo-employee", "roles": ["employee"], "departments": []},
    "sales": {"token": "demo-sales-token", "user_id": "demo-sales-employee", "roles": ["employee", "sales"], "departments": ["sales"]},
    "admin": {"token": "demo-admin-token", "user_id": "demo-admin", "roles": ["admin"], "departments": []},
}
API_AUTH_TOKEN = _setting("API_AUTH_TOKEN")
API_TOKENS_JSON = _setting("API_TOKENS_JSON")
API_TENANT_ID = os.getenv(
    "API_TENANT_ID", "company-demo" if PRODUCT_MODE == "company" else "personal"
)
API_USER_ID = os.getenv("API_USER_ID", "personal-user")
OIDC_ISSUER = os.getenv("OIDC_ISSUER", "").strip()
OIDC_AUDIENCE = os.getenv("OIDC_AUDIENCE", "").strip()
OIDC_JWKS_URL = os.getenv("OIDC_JWKS_URL", "").strip()
OIDC_TENANT_CLAIM = os.getenv("OIDC_TENANT_CLAIM", "tenant_id").strip()
OIDC_ROLES_CLAIM = os.getenv("OIDC_ROLES_CLAIM", "roles").strip()
OIDC_DEPARTMENTS_CLAIM = os.getenv("OIDC_DEPARTMENTS_CLAIM", "departments").strip()
COMPANY_DATA_ROOT = os.getenv("COMPANY_DATA_ROOT", "").strip()
DATABASE_URL = _setting("DATABASE_URL")
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "120"))
REDIS_URL = _setting("REDIS_URL").strip()
WHATSAPP_CONNECTOR_URL = os.getenv("WHATSAPP_CONNECTOR_URL", "").strip()
CALENDAR_CONNECTOR_URL = os.getenv("CALENDAR_CONNECTOR_URL", "").strip()
CRM_CONNECTOR_URL = os.getenv("CRM_CONNECTOR_URL", "").strip()
BOOKING_CONNECTOR_URL = os.getenv("BOOKING_CONNECTOR_URL", "").strip()
PAYMENT_CONNECTOR_URL = os.getenv("PAYMENT_CONNECTOR_URL", "").strip()
WHATSAPP_CONNECTOR_ENABLED = os.getenv("WHATSAPP_CONNECTOR_ENABLED", "false")
CALENDAR_CONNECTOR_ENABLED = os.getenv("CALENDAR_CONNECTOR_ENABLED", "false")
CRM_CONNECTOR_ENABLED = os.getenv("CRM_CONNECTOR_ENABLED", "false")
BOOKING_CONNECTOR_ENABLED = os.getenv("BOOKING_CONNECTOR_ENABLED", "false")
PAYMENT_CONNECTOR_ENABLED = os.getenv("PAYMENT_CONNECTOR_ENABLED", "false")
WHATSAPP_CONNECTOR_URL_TOKEN = _setting("WHATSAPP_CONNECTOR_URL_TOKEN")
CALENDAR_CONNECTOR_URL_TOKEN = _setting("CALENDAR_CONNECTOR_URL_TOKEN")
CRM_CONNECTOR_URL_TOKEN = _setting("CRM_CONNECTOR_URL_TOKEN")
BOOKING_CONNECTOR_URL_TOKEN = _setting("BOOKING_CONNECTOR_URL_TOKEN")
PAYMENT_CONNECTOR_URL_TOKEN = _setting("PAYMENT_CONNECTOR_URL_TOKEN")

# Privacy ke liye kaunsa local/private provider priority mein pehle try
# hoga - "local" (embedded, fast) ko "ollama" se pehle try karte hain
PRIVATE_PROVIDER_PRIORITY = ["local", "ollama"]


def is_local_model_ready() -> bool:
    """Check karta hai ki embedded model file disk pe maujood hai ya nahi."""
    return os.path.exists(LOCAL_MODEL_PATH)


def is_ollama_running() -> bool:
    """Check karta hai ki Ollama local server chal raha hai ya nahi."""
    try:
        import urllib.request
        urllib.request.urlopen(f"{OLLAMA_BASE_URL}/api/tags", timeout=1)
        return True
    except Exception:
        return False


def get_ready_private_provider():
    """
    PRIVATE_PROVIDER_PRIORITY list mein se sabse pehla provider return karta
    hai jo abhi ready hai (local model file mila, ya Ollama chal raha hai).
    Agar koi bhi ready nahi hai, None return karta hai.
    """
    for provider in PRIVATE_PROVIDER_PRIORITY:
        if provider == "local" and is_local_model_ready():
            return "local"
        if provider == "ollama" and is_ollama_running():
            return "ollama"
    return None


def get_available_providers():
    """
    Konse providers use karne layak hain (key hai ya local model/server
    available hai) - UI mein sirf yehi options dikhayenge.
    """
    available = []
    if is_local_model_ready():
        available.append("local")
    if is_ollama_running():
        available.append("ollama")
    if ALLOW_CLOUD_PROVIDERS and GROQ_API_KEY:
        available.append("groq")
    if ALLOW_CLOUD_PROVIDERS and OPENAI_API_KEY:
        available.append("openai")
    if ALLOW_CLOUD_PROVIDERS and ANTHROPIC_API_KEY:
        available.append("anthropic")
    return available


def set_provider(provider: str):
    """
    Runtime mein LLM_PROVIDER badalta hai (bina .env ya restart ke).
    Sirf tabhi badlega jab us provider ki API key ya local server available ho.
    """
    global LLM_PROVIDER
    if provider not in get_available_providers():
        raise ValueError(f"'{provider}' abhi available nahi hai (key/model/server missing).")
    LLM_PROVIDER = provider
    return LLM_PROVIDER
