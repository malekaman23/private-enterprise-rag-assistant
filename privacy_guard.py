"""
privacy_guard.py
-----------------
Yeh module check karta hai ki kisi text mein "sensitive personal data" hai
ya nahi (phone number, payment info, ID numbers, photos ka zikr, etc.)

Agar sensitive data mile, to router_agent.py is query ko FORCE karega
ki Ollama (local LLM) use ho, chahe .env mein Groq/OpenAI set ho -
taaki ye data kabhi bhi cloud pe na jaye.
"""

import re

# ---- Regex Patterns (numbers/IDs jo sensitive hote hain) ----
PATTERNS = {
    "phone_number": re.compile(r"(\+?91[\-\s]?)?[6-9]\d{9}\b"),           # Indian mobile
    "credit_card": re.compile(r"\b(?:\d[ -]*?){13,16}\b"),                 # card numbers
    "aadhaar": re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b"),                   # Aadhaar (12 digit grouped)
    "pan_card": re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b"),                     # PAN card format
    # UPI ID - sirf known UPI handles (@paytm, @ybl, etc.) match karo,
    # normal email addresses (@gmail.com, @company.com) match NAHI karne
    # chahiye - warna documents mein normal emails false-positive trigger
    # kar dete hain aur har jawab galti se "sensitive" ban jata hai.
    "upi_id": re.compile(
        r"\b[\w.\-]{2,}@(?:ybl|okaxis|okhdfcbank|oksbi|okicici|okbizaxis|"
        r"ibl|axl|upi|paytm|apl|jio|airtel|freecharge|idfcfirst|rbl|"
        r"kotak|axisbank|icici|hdfcbank)\b",
        re.IGNORECASE,
    ),
    "cvv_otp": re.compile(r"\b(cvv|otp)\D{0,5}\d{3,6}\b", re.IGNORECASE),
}

# ---- Keywords (English + Hindi/Hinglish) jo sensitive intent dikhate hain ----
SENSITIVE_KEYWORDS = [
    # English
    "password", "pin number", "bank account", "card number", "cvv", "otp",
    "credit card", "debit card", "payment details", "photo", "image of me",
    "passport", "aadhaar", "pan card", "contact number", "phone number",
    "personal number", "ssn", "social security",
    # Hindi / Hinglish
    "पासवर्ड", "फोन नंबर", "बैंक खाता", "भुगतान", "फोटो", "आधार", "पैन कार्ड",
    "contact no", "mobile number", "account number", "gupt", "confidential",
]


def contains_sensitive_data(text: str) -> bool:
    """
    True return karta hai agar text mein koi sensitive pattern ya keyword mile.
    Isse conservative rakha gaya hai (thoda zyada cautious) - better safe than
    accidentally sending real personal data to a cloud LLM.
    """
    if not text:
        return False

    lower_text = text.lower()

    # Keyword check (fast, simple)
    for kw in SENSITIVE_KEYWORDS:
        if kw.lower() in lower_text:
            return True

    # Pattern check (numbers/IDs)
    for name, pattern in PATTERNS.items():
        if pattern.search(text):
            return True

    return False


# Categories jo hamesha "sensitive" maani jaayengi, chahe unme kuch bhi ho
SENSITIVE_CATEGORIES = {"personal", "private", "sensitive", "confidential", "finance", "financial"}


def is_sensitive_category(category: str) -> bool:
    """Agar document ki category khud hi 'Personal'/'Private' jaisi hai."""
    if not category:
        return False
    return category.strip().lower() in SENSITIVE_CATEGORIES