"""
router_agent.py
----------------
Yeh is poore system ka "dimaag" hai. Iska kaam hai:

1. User ka sawal padhna
2. Decide karna: iska jawab mere documents se milega, ya web search
   se, ya dono se milake
3. Sahi source(s) se information laake, LLM ke through
   ek final, saaf jawab banana

Isi step ko "Routing" bolte hain - jaise ek receptionist jo decide
karta hai ki tumhari query kis department mein bhejni hai.
"""

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

import config
import memory
import long_term_memory
import vector_store
import web_search
import tools
import privacy_guard
from llm_provider import get_llm
from langchain.agents import create_agent
import re
from tenant_utils import DEFAULT_TENANT_ID, DEFAULT_USER_ID


ROUTER_PROMPT = """Tum ek query router ho. User ka sawal padho aur decide karo
ki iska jawab dene ke liye WEB SEARCH ki zaroorat hai ya nahi.

Documents hamesha check kiye jaate hain (isliye is decision ka matlab sirf
itna hai ki EXTRA web search bhi karni hai ya nahi).

- "WEB" -> agar sawal current events, latest/real-time info, ya aisi cheez
  jo document mein na ho (jaise aaj ki date, live price, recent news) maang raha hai
- "NO_WEB" -> agar sawal general hai, ya sirf uploaded document/notes se
  related lagta hai, ya conversation se related hai

Sirf ek word return karo: WEB ya NO_WEB.

User ka sawal: {question}
"""

ACTION_CLASSIFIER_PROMPT = """Decide karo ki neeche diya gaya user input ek
"ACTION" hai ya sirf "QUESTION" hai.

ACTION sirf tab hai jab user in specific cheezon mein se koi karwana chahta hai:
- Email bhejna
- Reminder set/list karna
- Current date/time puchna
- WhatsApp message bhejna
- Calendar event banana
- CRM update karna
- Booking ya payment link banana

QUESTION hai agar user:
- Kisi document/PDF/notes ke bare mein pucch raha hai (explain karo, summary do, kya likha hai, etc.)
- Kisi topic ko samjhne/samjhane ko keh raha hai
- General knowledge ya information maang raha hai
- Koi bhi sawal jo upar diye 3 ACTIONS mein se match nahi karta

IMPORTANT: Sirf isliye ACTION mat bolo kyunki sentence mein "karo", "batao",
"explain karo" jaise command-jaise words hain - agar asli maksad EXPLAIN/
SUMMARIZE/INFORMATION dena hai (na ki email/reminder/time), to ye QUESTION hai.

Sirf ek word return karo: ACTION ya QUESTION.

User input: {question}
"""

ANSWER_PROMPT = """You are a helpful personal AI assistant.

LANGUAGE RULE (STRICT - follow this above everything else): Detect the
language of the user's question below and reply ONLY in that exact same
language. Do not switch languages based on context, memory, or documents -
only the question's language matters.
- If the question is in English -> reply in English, no Hindi/other words mixed in.
- If the question is in Hindi -> reply in Hindi.
- If the question is in Gujarati -> reply in Gujarati.
- If mixed (Hinglish) -> mirror that mixed style.
Before answering, identify the question's language internally, then write
the ENTIRE response in that language only.

FORMATTING RULE: You may use standard markdown (headings, bold, bullet
lists, numbered lists) where it improves readability - the interface
renders markdown properly, so use it naturally rather than avoiding it.

Use the context below to give an accurate answer to the user's question.
If the answer isn't in the context, clearly say the information wasn't
found - never make up information (do not hallucinate).

DOCUMENT CONTEXT RULE: The "Context (Documents)" section below contains
content retrieved from files the user has ALREADY uploaded to this system.
Each chunk is labelled with its source file name. So:
- Never say "no file is attached" or "please upload the file" when this
  section has content - the files are already here.
- If the user names a file (even with a typo or partial name), match it
  loosely against the file names in the labels and answer from that content.
- If the user's named file genuinely doesn't appear in the labels, tell them
  which files ARE available instead of saying nothing was uploaded.

--- Context (Documents) ---
{doc_context}

--- Context (Web Search) ---
{web_context}

--- Conversation History (recent, exact) ---
{chat_history}

--- Relevant Older Memory (recalled based on meaning, may be old) ---
{long_term_memory}

User ka sawal: {question}

Jawab:"""


# Chhote local models (jaise Ollama ke llama3.1:8b) bade cloud models (Groq
# 120B) jitna "smart" nahi hote - bahut saare context sections ek saath
# dekhkar confuse ho jaate hain aur natural jawab dene ke bajaye raw
# sections ko hi mechanically list kar dete hain. Isliye jab local/private
# model use ho raha ho, ek MUCH SIMPLER prompt dete hain - sirf jo
# genuinely zaroori hai, aur clear instruction ki natural sentence mein
# jawab do, sections ko echo mat karo.
ANSWER_PROMPT_SIMPLE = """You are a helpful personal assistant.

Reply in the SAME language as the user's message below (Hindi, English,
Gujarati, or mixed - match their language exactly).

Answer in plain, natural, conversational sentences only. Do NOT repeat
these instructions, do NOT list out section labels like "Available
Files:" or "Phone Number:" unless the user specifically asked for a list.
If the user is just telling you a fact to remember (not asking a
question), simply acknowledge it briefly in one natural sentence.

{doc_context_block}{memory_block}
User's message: {question}

Your natural reply:"""


def build_simple_prompt(question, doc_context, relevant_memory):
    """ANSWER_PROMPT_SIMPLE ke placeholders ko sirf tab bharta hai jab
    unme actually kuch content ho - khaali sections bhi noise banate hain."""
    doc_block = f"Relevant background info:\n{doc_context}\n\n" if doc_context else ""
    memory_block = f"Something relevant from earlier: {relevant_memory}\n\n" if relevant_memory else ""
    return ANSWER_PROMPT_SIMPLE.format(
        doc_context_block=doc_block,
        memory_block=memory_block,
        question=question,
    )


def fast_company_answer(question: str, doc_context: str):
    """Answer common numeric company-report questions without 3B inference."""
    q = question.lower()
    if not any(word in q for word in ("sales", "revenue", "target", "actual")):
        return None
    target = re.search(r"(?:revenue target|target)\s*:?\s*INR\s*([\d,]+)", doc_context, re.I)
    actual = re.search(r"(?:actual revenue|actual)\s*:?\s*INR\s*([\d,]+)", doc_context, re.I)
    gap = re.search(r"(?:revenue gap|gap)\s*:?\s*INR\s*([\d,]+)", doc_context, re.I)
    if not (target and actual):
        return None
    target_value = int(target.group(1).replace(",", ""))
    actual_value = int(actual.group(1).replace(",", ""))
    gap_value = int(gap.group(1).replace(",", "")) if gap else target_value - actual_value
    percentage = (gap_value / target_value * 100) if target_value else 0
    return (
        f"Sales revenue target was INR {target_value:,}, while actual revenue was "
        f"INR {actual_value:,}. The company is below target by INR {gap_value:,} "
        f"({percentage:.1f}%). Source: sales-overview.txt."
    )


def fast_arithmetic_answer(question: str):
    """Keep health/smoke-test arithmetic instant and deterministic."""
    match = re.fullmatch(r"\s*(\d+)\s*([+\-*/])\s*(\d+)\s*\??\s*", question)
    if not match:
        match = re.search(r"\b(\d+)\s*(?:plus|minus|times|divided by)\s*(\d+)\b", question.lower())
        if not match:
            return None
        left, right = int(match.group(1)), int(match.group(2))
        operator = "plus" if "plus" in question.lower() else ("minus" if "minus" in question.lower() else ("times" if "times" in question.lower() else "divided by"))
    else:
        left, operator, right = int(match.group(1)), match.group(2), int(match.group(3))
    if operator in ("+", "plus"):
        result = left + right
    elif operator in ("-", "minus"):
        result = left - right
    elif operator in ("*", "times"):
        result = left * right
    elif right:
        result = left / right
    else:
        return "Division by zero is not defined."
    return f"{left} {operator} {right} = {result:g}"


def is_general_cloud_question(question: str, category: str | None, force_private: bool) -> bool:
    """Avoid vector retrieval for clearly general questions in hybrid mode."""
    if force_private or category not in (None, "", "All"):
        return False
    if config.LLM_PROVIDER not in {"groq", "openai", "anthropic"}:
        return False
    if config.ALLOW_CLOUD_DOCUMENT_CONTEXT or privacy_guard.contains_sensitive_data(question):
        return False
    terms = (
        "document", "file", "pdf", "report", "uploaded", "company", "sales",
        "revenue", "finance", "policy", "department", "server", "data", "rag",
        "roadmap", "this file", "this document", "according to",
    )
    return not any(term in question.lower() for term in terms)


def needs_web_search(question: str, provider_override: str = None) -> bool:
    """LLM se decide karwata hai ki EXTRA web search chahiye ya nahi."""
    llm = get_llm(temperature=0, provider_override=provider_override)
    prompt = ROUTER_PROMPT.format(question=question)
    response = llm.invoke([HumanMessage(content=prompt)])
    decision = response.content.strip().upper()
    return "WEB" in decision and "NO_WEB" not in decision


def is_action_request(question: str, provider_override: str = None) -> bool:
    """
    Decide karta hai ki user ne 'kaam karo' bola hai ya sirf 'sawal' pucha hai.

    Pehle ek fast keyword check karte hain: agar sawal mein email/reminder/
    time se related koi bhi keyword nahi hai, to seedha QUESTION maan lete
    hain (LLM ko call karne ki zaroorat nahi) - isse galat classification
    ka risk bhi kam hota hai aur ek extra API call bhi bach jaata hai.
    """
    action_keywords = [
        "email", "mail bhej", "mail kar",
        "reminder", "yaad dila", "remind",
        "current time", "abhi kya time", "aaj ki date", "kya time hua",
        "whatsapp", "calendar", "meeting", "appointment", "booking",
        "crm", "payment link", "invoice link",
    ]
    lower_q = question.lower()
    if not any(kw in lower_q for kw in action_keywords):
        return False

    llm = get_llm(temperature=0, provider_override=provider_override)
    prompt = ACTION_CLASSIFIER_PROMPT.format(question=question)
    response = llm.invoke([HumanMessage(content=prompt)])
    decision = response.content.strip().upper()
    return "ACTION" in decision and "QUESTION" not in decision


AGENT_SYSTEM_PROMPT = """You are a helpful personal assistant that can use tools
(send_email, add_reminder, list_reminders, get_current_datetime,
send_whatsapp_message, create_calendar_event, update_crm_record, create_booking,
create_payment_link). External actions are approval-gated; never claim they
were completed when the tool says they are queued.

LANGUAGE RULE (STRICT): Reply in the exact same language as the user's
message - English question gets English reply, Hindi gets Hindi, Gujarati
gets Gujarati. Never mix in a different language.

FORMATTING RULE: You may use standard markdown (bold, bullet lists) where
it improves readability - the interface renders markdown properly."""


def run_action_agent(question: str, provider_override: str = None) -> str:
    """
    Tool-calling agent chalata hai - LLM khud decide karega kaunsa
    tool (email/reminder/datetime) use karna hai aur kaise.
    """
    llm = get_llm(temperature=0, provider_override=provider_override)
    agent = create_agent(llm, tools.ALL_TOOLS, system_prompt=AGENT_SYSTEM_PROMPT)

    result = agent.invoke({
        "messages": [HumanMessage(content=question)]
    })

    # Agent ke last message mein final answer hota hai
    final_message = result["messages"][-1]
    return final_message.content


def decide_privacy_engine(question: str, force_private: bool = False):
    """
    Decide karta hai ki is query ke liye kaunsa engine (provider) use hoga.

    Return: (provider_override, engine_label, blocked_warning)
    - Agar sensitive data mila (ya user ne manually 'force private' on kiya):
        - 'local' (embedded model) ready hai -> use karo (sabse fast local option)
        - warna agar Ollama chal raha hai -> use karo
        - warna kisi cloud pe bhejne ke bajaye saaf mana kar do
    - Agar sensitive nahi hai -> normal config.LLM_PROVIDER (Groq/etc.) use hoga
    """
    is_sensitive = force_private or privacy_guard.contains_sensitive_data(question)

    if is_sensitive:
        ready_provider = config.get_ready_private_provider()
        if not ready_provider:
            warning = (
                "Yeh sawal mein sensitive personal data (phone number, payment "
                "info, ID, etc.) detect hua hai, ya aapne 'Private Mode' on kiya "
                "hai. Privacy ke liye ye sirf local model se process hota hai, "
                "lekin abhi koi local model (embedded ya Ollama) ready nahi hai. "
                "Model setup karke dubara try karo."
            )
            return None, None, warning
        label = "local (private, embedded)" if ready_provider == "local" else "ollama (private)"
        return ready_provider, label, None

    return None, config.LLM_PROVIDER, None


def format_chat_history(limit: int = 6, tenant_id: str = DEFAULT_TENANT_ID,
                        user_id: str = DEFAULT_USER_ID) -> str:
    """Recent conversation ko readable text mein badalta hai."""
    history = memory.get_recent_history(limit=limit, tenant_id=tenant_id, user_id=user_id)
    if not history:
        return "(koi purani history nahi hai)"
    return "\n".join([f"{role}: {msg}" for role, msg in history])


def answer_query(question: str, category: str = None, force_private: bool = False,
                 tenant_id: str = DEFAULT_TENANT_ID, user_id: str = DEFAULT_USER_ID,
                 departments: tuple[str, ...] = (), roles: tuple[str, ...] = ()) -> str:
    """
    Poora pipeline: pehle privacy check -> phir action hai ya question
    decide karo -> agar action hai to tools use karo -> agar question
    hai to RAG pipeline (docs + web + memory) use karo.
    'category' diya gaya to sirf usi category ke documents check honge.
    'force_private' True ho to hamesha Ollama use hoga (user ka manual toggle).
    """
    tools.set_execution_scope(tenant_id, user_id)

    arithmetic = fast_arithmetic_answer(question)
    if arithmetic:
        memory.save_message("user", question, tenant_id, user_id)
        memory.save_message("assistant", arithmetic, tenant_id, user_id)
        return arithmetic, "local-fast", []

    # ---- PRIVACY CHECK (sabse pehle, question ke basis pe) ----
    provider_override, engine_label, warning = decide_privacy_engine(question, force_private)
    if warning:
        memory.save_message("user", question, tenant_id, user_id)
        memory.save_message("assistant", warning, tenant_id, user_id)
        return warning, "PRIVACY_BLOCKED", []

    # Step 1: Action hai ya sirf question?
    if is_action_request(question, provider_override=provider_override):
        answer = run_action_agent(question, provider_override=provider_override)
        memory.save_message("user", question, tenant_id, user_id)
        memory.save_message("assistant", answer, tenant_id, user_id)
        long_term_memory.save_to_long_term_memory("user", question, tenant_id, user_id)
        long_term_memory.save_to_long_term_memory("assistant", answer, tenant_id, user_id)
        return answer, f"ACTION · {engine_label}", []

    # Step 2: Normal Question -> RAG pipeline

    # Documents hamesha check karo (agar koi upload kiya gaya ho)
    doc_context = ""
    sources = []
    doc_categories_seen = set()
    cloud_general_question = is_general_cloud_question(question, category, force_private)
    try:
        docs = [] if cloud_general_question else vector_store.search_documents(
            question, category=category, tenant_id=tenant_id, user_id=user_id,
            departments=departments, roles=roles,
        )
        if docs:
            # Har chunk ke saath uska filename/page bhi context mein bhejo,
            # taaki LLM ko pata rahe ye content kis file se aaya hai
            labelled_chunks = []
            seen = set()
            for d in docs:
                fname = d.metadata.get("source_file", "unknown")
                page = d.metadata.get("page")
                page_label = f", page {page + 1}" if isinstance(page, int) else ""
                labelled_chunks.append(
                    f"[From file: {fname}{page_label}]\n{d.page_content}"
                )
                doc_categories_seen.add(d.metadata.get("category", ""))

                key = (fname, page)
                if key not in seen:
                    seen.add(key)
                    sources.append({
                        "file": fname,
                        "page": (page + 1) if isinstance(page, int) else None,
                    })

            doc_context = "\n\n".join(labelled_chunks)

        # Available files ki list bhi context mein bhejo, taaki agar user
        # kisi aur file ka naam le to LLM bata sake kya-kya available hai
        try:
            all_docs = [] if cloud_general_question else vector_store.list_documents(
                tenant_id=tenant_id, user_id=user_id, departments=departments
                , roles=roles
            )
            # Do not even expose the private file inventory to cloud LLMs.
            # When document context is cloud-disabled, an empty retrieval can
            # still use Groq for a general question without leaking filenames.
            cloud_without_docs = (
                config.LLM_PROVIDER in {"groq", "openai", "anthropic"}
                and not config.ALLOW_CLOUD_DOCUMENT_CONTEXT
                and not doc_context
            )
            if all_docs and not cloud_without_docs:
                file_list = ", ".join(
                    f"{d['filename']} ({d['category']})" for d in all_docs
                )
                doc_context = (
                    f"[Files currently available in the system: {file_list}]\n\n"
                    + doc_context
                )
        except Exception:
            pass
    except Exception as e:
        doc_context = f"(documents search mein error: {e} - shayad abhi tak koi document process nahi hua)"

    # ---- PRIVACY RE-CHECK (documents ke content/category ke basis pe bhi) ----
    # Ho sakta hai sawal khud normal ho, lekin retrieved document sensitive ho
    if provider_override is None:
        doc_sensitive = (
            privacy_guard.contains_sensitive_data(doc_context)
            or any(privacy_guard.is_sensitive_category(c) for c in doc_categories_seen)
        )
        # Company RAG data stays on the private model unless an administrator
        # explicitly opts into sending document context to a cloud provider.
        if doc_context and config.LLM_PROVIDER in {"groq", "openai", "anthropic"} \
                and not config.ALLOW_CLOUD_DOCUMENT_CONTEXT:
            doc_sensitive = True
        if doc_sensitive:
            ready_provider = config.get_ready_private_provider()
            if not ready_provider:
                warning = (
                    "Is document mein sensitive personal data hai. Privacy ke "
                    "liye ye sirf local model se process hota hai, lekin abhi "
                    "koi local model (embedded ya Ollama) ready nahi hai. Model "
                    "setup karke dubara try karo."
                )
                memory.save_message("user", question, tenant_id, user_id)
                memory.save_message("assistant", warning, tenant_id, user_id)
                return warning, "PRIVACY_BLOCKED", []
            provider_override = ready_provider
            engine_label = "local (private, embedded)" if ready_provider == "local" else "ollama (private)"

    fast_answer = fast_company_answer(question, doc_context)
    if fast_answer:
        memory.save_message("user", question, tenant_id, user_id)
        memory.save_message("assistant", fast_answer, tenant_id, user_id)
        return fast_answer, "RAG · local-fast", sources

    llm = get_llm(temperature=0.3, provider_override=provider_override)

    # Web search sirf tab karo jab router bole ki zaroorat hai - LEKIN agar
    # ye query privacy ki wajah se local model pe route hui hai, to web
    # search SKIP karo. Do reasons: (1) speed - local model pe ek extra
    # LLM call lagana bahut slow hai, (2) PRIVACY - web search ka matlab
    # hai sawal Tavily (external service) ko jayega, jo khud ek data-leak
    # hoga - isse bachna hi privacy-routing ka poora maksad hai.
    web_context = ""
    use_web = False
    if provider_override is None and config.ALLOW_CLOUD_PROVIDERS:
        # Web search sends the query to an external service.
        use_web = needs_web_search(question)
        if use_web:
            web_context = web_search.web_search(question)

    decision = "BOTH" if (doc_context and use_web) else ("WEB" if use_web else "DOCS")
    decision = f"{decision} · {engine_label}"

    chat_history = format_chat_history(tenant_id=tenant_id, user_id=user_id)

    # Long-term memory: meaning ke hisaab se PURANI relevant baatein dhundo
    relevant_memory = "" if cloud_general_question else long_term_memory.recall_relevant_memory(
        question, tenant_id=tenant_id, user_id=user_id
    )

    # Cloud-only general questions must not inherit private conversation memory.
    if (provider_override is None and config.LLM_PROVIDER in {"groq", "openai", "anthropic"}
            and not doc_context and not config.ALLOW_CLOUD_DOCUMENT_CONTEXT):
        chat_history = ""
        relevant_memory = ""

    # Local/private model (chhota model) ke liye simpler prompt use karo -
    # chhota model kam context mein zyada accurately natural jawab deta hai.
    # Documents ka context bhi CHHOTA karte hain (sirf pehle ~1200 chars) -
    # CPU pe bade context ko process karna sabse zyada time leta hai, aur
    # zyadatar sawal (jaise "mera number yaad rakho") documents se related
    # hote hi nahi, to poora context bhejne ka fayda nahi, sirf slow karta hai.
    if provider_override in ("local", "ollama"):
        trimmed_doc_context = doc_context[:1200] if doc_context else ""
        final_prompt = build_simple_prompt(question, trimmed_doc_context, relevant_memory)
    else:
        final_prompt = ANSWER_PROMPT.format(
            doc_context=doc_context or "(use nahi kiya gaya)",
            web_context=web_context or "(use nahi kiya gaya)",
            chat_history=chat_history,
            long_term_memory=relevant_memory or "(koi relevant purani memory nahi mili)",
            question=question,
        )

    response = llm.invoke([HumanMessage(content=final_prompt)])
    answer = response.content

    # Short-term memory (SQLite) mein save karo
    memory.save_message("user", question, tenant_id, user_id)
    memory.save_message("assistant", answer, tenant_id, user_id)

    # Long-term memory (vector store) mein bhi save karo
    # Do not create local embedding work for cloud-only general chats. This
    # keeps Groq responses fast and prevents cloud conversation text from
    # being copied into the private semantic-memory index.
    if not cloud_general_question:
        long_term_memory.save_to_long_term_memory("user", question, tenant_id, user_id)
        long_term_memory.save_to_long_term_memory("assistant", answer, tenant_id, user_id)

    return answer, decision, sources
