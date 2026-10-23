"""
llm_provider.py
----------------
Yeh "Factory Pattern" use karta hai - matlab isse ek function ko pucho
"mujhe LLM do", aur config.py mein jo provider set hai, wahi wapas milega.

Isse fayda yeh hai: agar kal Groq se OpenAI pe shift hona hai,
to sirf .env file change karo - is file ya kisi aur file mein
ek line bhi change nahi karni padegi.
"""

from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_ollama import ChatOllama

import config

# Local embedded model ko baar-baar disk se load karna bahut slow hoga
# (GGUF file load hone mein hi kaafi time lagta hai) - isliye ek baar
# load karke cache mein rakh lete hain, reuse karte rehte hain.
_LOCAL_LLM_CACHE = {}


def _get_local_llm(temperature: float):
    """Embedded local model (llama-cpp) ko load karta hai - sirf pehli baar,
    uske baad cached instance reuse hoti hai (fast)."""
    key = round(temperature, 2)
    if key not in _LOCAL_LLM_CACHE:
        from langchain_community.chat_models import ChatLlamaCpp

        if not config.is_local_model_ready():
            raise ValueError(
                f"Local model file nahi mili: '{config.LOCAL_MODEL_PATH}'. "
                f"Pehle GGUF model file download karke us path pe rakho."
            )

        _LOCAL_LLM_CACHE[key] = ChatLlamaCpp(
            model_path=config.LOCAL_MODEL_PATH,
            n_ctx=2048,  # 4096 se ghatakar 2048 - hum context ko already
                         # chhota rakhte hain (~1200 chars tak), isliye
                         # itni badi window allocate karne ki zaroorat nahi
                         # aur ye allocation/processing overhead bachata hai
            n_threads=config.LOCAL_MODEL_THREADS,
            temperature=temperature,
            max_tokens=200,  # aur kam - zyadatar chhote, natural jawab
                              # isse kam mein hi complete ho jaate hain
            n_batch=512,  # llama.cpp ka standard recommended batch size -
                           # prompt processing (prefill) fast karta hai
            stop=["\nUser's message:", "\nUser:", "\n\nUser"],  # jaise hi
                # model khud jawab de chuka ho aur agli "fake conversation"
                # banane lage, usko turant rok do - isse generation
                # unnecessarily lamba nahi chalta
            verbose=False,
        )
    return _LOCAL_LLM_CACHE[key]


def get_llm(temperature: float = 0.3, provider_override: str = None):
    """
    config.py mein set kiye gaye LLM_PROVIDER ke hisaab se
    sahi LLM object return karta hai.

    temperature: 0 = bahut factual/strict, 1 = zyada creative
    provider_override: agar diya gaya hai, to config ke bajaye
                        yehi provider use hoga (sirf isi call ke liye) -
                        isse privacy_guard sensitive queries ko force
                        local/Ollama pe bhej sakta hai, bina global setting badle.
    """

    provider = provider_override or config.LLM_PROVIDER

    if provider in {"groq", "openai", "anthropic"} and not config.ALLOW_CLOUD_PROVIDERS:
        raise ValueError(
            "Cloud LLM providers are disabled by policy. Set "
            "ALLOW_CLOUD_PROVIDERS=true only after approving the data policy."
        )

    if provider == "local":
        # 100% local, EMBEDDED (Ollama jaisa alag app bhi nahi chahiye) -
        # sabse fast local option, especially chhote models ke saath
        return _get_local_llm(temperature)

    elif provider == "ollama":
        # 100% local - koi data internet pe nahi jata
        return ChatOllama(
            base_url=config.OLLAMA_BASE_URL,
            model=config.MODEL_NAMES["ollama"],
            temperature=temperature,
        )

    elif provider == "groq":
        return ChatGroq(
            api_key=config.GROQ_API_KEY,
            model=config.MODEL_NAMES["groq"],
            temperature=temperature,
            timeout=20,
            max_retries=0,
        )

    elif provider == "openai":
        return ChatOpenAI(
            api_key=config.OPENAI_API_KEY,
            model=config.MODEL_NAMES["openai"],
            temperature=temperature,
        )

    elif provider == "anthropic":
        return ChatAnthropic(
            api_key=config.ANTHROPIC_API_KEY,
            model=config.MODEL_NAMES["anthropic"],
            temperature=temperature,
        )

    else:
        raise ValueError(
            f"Unknown LLM_PROVIDER: '{provider}'. "
            f"config.py mein 'local', 'ollama', 'groq', 'openai', ya 'anthropic' set karo."
        )
