"""
voice_tools.py
--------------
Voice input aur output handle karta hai:
1. transcribe_audio()  -> user ki recorded awaaz ko text mein badalta hai
                           (Groq ka Whisper model use karke - bahut fast hai)
2. text_to_speech()     -> assistant ke jawab ko audio (mp3) mein badalta hai
                           (Google TTS use karke - free, multi-language)

Note: Speech-to-text ke liye HAMESHA Groq API key chahiye hoti hai
(chahe tumhara LLM_PROVIDER kuch bhi ho), kyunki Whisper sirf Groq
ke through use kar rahe hain - ye fast aur free hai.
"""

import io
from groq import Groq
from gtts import gTTS

import config


def transcribe_audio(audio_bytes: bytes) -> str:
    """
    Recorded audio (bytes, WAV format) ko text mein convert karta hai,
    Groq ke Whisper model se.
    """
    if not config.ALLOW_CLOUD_PROVIDERS:
        return "(Privacy policy ke kaaran cloud voice transcription disabled hai. Local speech-to-text provider configure karo.)"
    if not config.GROQ_API_KEY:
        return "(Voice input ke liye .env mein GROQ_API_KEY chahiye)"

    try:
        client = Groq(api_key=config.GROQ_API_KEY)
        transcription = client.audio.transcriptions.create(
            file=("audio.wav", audio_bytes),
            model="whisper-large-v3-turbo",
            response_format="text",
        )
        # Kabhi-kabhi response object hota hai, kabhi seedha string
        return transcription if isinstance(transcription, str) else transcription.text
    except Exception as e:
        return f"(Transcription error: {e})"


def detect_language_for_speech(text: str) -> str:
    """
    Text ke script (characters) dekh ke andaza lagata hai ki
    kaunsi language hai - taaki TTS sahi awaaz mein bole.
    """
    for ch in text:
        if "\u0900" <= ch <= "\u097F":   # Devanagari (Hindi)
            return "hi"
        if "\u0A80" <= ch <= "\u0AFF":   # Gujarati script
            return "gu"
    return "en"  # default English


def text_to_speech(text: str) -> bytes:
    """
    Text ko audio (mp3 bytes) mein convert karta hai, sahi language mein.
    Return: mp3 audio bytes (Streamlit mein seedha play ho sakta hai)
    """
    if not config.ALLOW_CLOUD_PROVIDERS:
        return None
    lang = detect_language_for_speech(text)
    try:
        tts = gTTS(text=text, lang=lang)
        buffer = io.BytesIO()
        tts.write_to_fp(buffer)
        buffer.seek(0)
        return buffer.read()
    except Exception as e:
        print(f"TTS error: {e}")
        return None
