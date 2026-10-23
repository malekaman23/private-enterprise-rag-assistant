"""
app.py
------
Streamlit-based chat interface.
Run with:  streamlit run app.py

Note: All UI text is kept in English by design. Only the assistant's
chat replies adapt to whatever language the user types in (handled in
router_agent.py's ANSWER_PROMPT).
"""

import streamlit as st
import os

import config
import memory
import document_processor
import vector_store
import voice_tools
from router_agent import answer_query

st.set_page_config(page_title="Personal AI Assistant", page_icon="🧠", layout="wide")

memory.init_db()

st.title("🧠 Personal AI Assistant")
st.caption(f"Provider: **{config.LLM_PROVIDER.upper()}** | Documents + Web Search enabled")

# ---------------- Sidebar: File Upload + Controls ----------------
with st.sidebar:
    st.header("📁 Documents")

    existing_categories = vector_store.get_all_categories()
    category_options = existing_categories + ["+ New category"]

    if category_options == ["+ New category"]:
        category = st.text_input("Category name", value="General")
    else:
        selected = st.selectbox("Category", options=category_options)
        if selected == "+ New category":
            category = st.text_input("New category name", value="General")
        else:
            category = selected

    uploaded_files = st.file_uploader(
        "Upload your PDFs / Docs / TXT / CSV files here",
        accept_multiple_files=True,
        type=["pdf", "docx", "txt", "csv"],
    )

    if uploaded_files and st.button("Process Documents"):
        os.makedirs(config.DATA_DIR, exist_ok=True)
        new_filenames = []
        for file in uploaded_files:
            safe_name = os.path.basename(file.name)
            extension = safe_name.lower().rsplit(".", 1)[-1] if "." in safe_name else ""
            if extension not in config.ALLOWED_UPLOAD_EXTENSIONS:
                st.error(f"Unsupported file type: {file.name}")
                continue
            if file.size > config.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
                st.error(f"File too large: {file.name}")
                continue
            filepath = os.path.join(config.DATA_DIR, safe_name)
            with open(filepath, "wb") as f:
                f.write(file.getbuffer())
            new_filenames.append(safe_name)

        with st.spinner("Processing documents..."):
            chunks = document_processor.process_documents(only_files=new_filenames)
            if chunks:
                vector_store.build_vectorstore(chunks, category=category)
                st.success(f"{len(chunks)} chunks added under category '{category}'!")
            else:
                st.warning("No document found to process.")

    st.divider()
    st.subheader("🔍 Search Filter")
    filter_categories = ["All"] + vector_store.get_all_categories()
    selected_filter = st.selectbox("Only search within category", options=filter_categories)
    st.session_state.category_filter = selected_filter

    st.divider()
    if st.button("🗑️ Clear Chat History"):
        memory.clear_history()
        st.session_state.messages = []
        st.success("History cleared!")

    st.divider()
    st.markdown("**To switch provider:** change `LLM_PROVIDER` in the `.env` file.")

    st.divider()
    st.subheader("🎙️ Voice Settings")
    voice_reply_enabled = st.checkbox("Speak the assistant's replies (TTS)", value=False)
    st.session_state.voice_reply_enabled = voice_reply_enabled

# ---------------- Main Chat Area ----------------
if "messages" not in st.session_state:
    # load previous history
    st.session_state.messages = [
        {"role": role, "content": msg} for role, msg in memory.get_recent_history(limit=20)
    ]

if "last_audio_id" not in st.session_state:
    st.session_state.last_audio_id = None

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ---- Voice input (mic) ----
audio_value = st.audio_input("🎙️ Or record your question")

voice_transcribed_text = None
if audio_value is not None:
    # Streamlit re-runs the script on every interaction, so we only
    # transcribe a NEW recording (avoid re-processing the same audio again)
    audio_bytes = audio_value.getvalue()
    audio_id = hash(audio_bytes)
    if audio_id != st.session_state.last_audio_id:
        st.session_state.last_audio_id = audio_id
        with st.spinner("Transcribing your voice..."):
            voice_transcribed_text = voice_tools.transcribe_audio(audio_bytes)

text_input = st.chat_input("Ask me anything...")

user_input = voice_transcribed_text or text_input

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                category_filter = st.session_state.get("category_filter", "All")
                answer, source = answer_query(user_input, category=category_filter)
                st.markdown(answer)
                st.caption(f"📌 Source used: {source}")
                st.session_state.messages.append({"role": "assistant", "content": answer})

                if st.session_state.get("voice_reply_enabled"):
                    with st.spinner("Generating voice reply..."):
                        audio_reply = voice_tools.text_to_speech(answer)
                        if audio_reply:
                            st.audio(audio_reply, format="audio/mp3", autoplay=True)
            except Exception as e:
                st.error(f"Error: {e}")
