import html
import os
import time
from datetime import datetime

import requests
import streamlit as st

# ------------------------------------------------------------------
# Config
# ------------------------------------------------------------------
# Override with the BACKEND_URL env var to point this at a local
# `uvicorn src.main:app` instance instead of the deployed one, e.g.:
#   BACKEND_URL=http://127.0.0.1:8000 streamlit run streamlit_app.py
BACKEND_URL = os.getenv("BACKEND_URL", "https://adaptive-rag-backend-fyyu.onrender.com")

st.set_page_config(
    page_title="Adaptive RAG Chat",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ------------------------------------------------------------------
# Session state
# ------------------------------------------------------------------
if "chat_log" not in st.session_state:
    st.session_state.chat_log = []          # [{question, answer, time, sources, elapsed}]
if "doc_count" not in st.session_state:
    st.session_state.doc_count = 0
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = True
if "history_search" not in st.session_state:
    st.session_state.history_search = ""
if "question_input" not in st.session_state:
    st.session_state.question_input = ""
if "clear_input" not in st.session_state:
    st.session_state.clear_input = False
if "uploaded_files_seen" not in st.session_state:
    # Tracks (name, size) pairs already sent to the backend so the widget's
    # persisted file doesn't get re-uploaded on every rerun (e.g. every time
    # a chat message is sent). Without this, "Documents Uploaded" inflates
    # on every rerun even though nothing new was uploaded.
    st.session_state.uploaded_files_seen = set()
if "is_thinking" not in st.session_state:
    st.session_state.is_thinking = False
if "stream_next" not in st.session_state:
    # When True, the most recent chat_log entry hasn't been "typed out" on
    # screen yet — the render loop below will animate it once, then flip
    # this back to False so it renders instantly on every later rerun.
    st.session_state.stream_next = False

# Clear the input BEFORE the widget is instantiated this run (safe to do here)
if st.session_state.clear_input:
    st.session_state.question_input = ""
    st.session_state.clear_input = False

# ------------------------------------------------------------------
# Theme colors
# ------------------------------------------------------------------
if st.session_state.dark_mode:
    bg_main = (
        "radial-gradient(circle at 15% 15%, rgba(59,130,246,0.16), transparent 42%),"
        "radial-gradient(circle at 85% 25%, rgba(139,92,246,0.14), transparent 45%),"
        "radial-gradient(circle at 50% 100%, rgba(34,211,238,0.10), transparent 55%),"
        "#050914"
    )
    bg_card = "rgba(20,26,48,0.72)"
    bg_sidebar = "#0a0e22"
    text_main = "#f2f2f5"
    text_dim = "#9a9daa"
    border_col = "rgba(120,160,255,0.18)"
else:
    bg_main = "#f5f6fa"
    bg_card = "#ffffff"
    bg_sidebar = "#ffffff"
    text_main = "#1a1c23"
    text_dim = "#5c5f6b"
    border_col = "rgba(0,0,0,0.08)"

accent_grad = "linear-gradient(90deg, #4f7cff, #9b5cff)"
# Cyan -> blue -> violet gradient used for the "RAG Chat" hero wordmark and
# the neon glow accents, matching the reference banner's color scheme.
hero_grad = "linear-gradient(90deg, #22d3ee, #3b82f6, #8b5cf6)"

# ------------------------------------------------------------------
# CSS
# ------------------------------------------------------------------
st.markdown(
    f"""
    <style>
    .stApp {{
        background: {bg_main};
        background-attachment: fixed;
        color: {text_main};
        animation: pageFadeIn 0.5s ease-out;
        position: relative;
    }}
    @keyframes pageFadeIn {{
        from {{ opacity: 0; transform: translateY(10px); }}
        to   {{ opacity: 1; transform: translateY(0); }}
    }}

    /* Slow-drifting glow blobs behind everything, echoing the neon-network
       banner art. Painted first so real content always sits on top. */
    .stApp::before {{
        content: "";
        position: fixed;
        inset: 0;
        z-index: 0;
        pointer-events: none;
        background:
            radial-gradient(circle at 18% 25%, rgba(59,130,246,0.20), transparent 40%),
            radial-gradient(circle at 82% 20%, rgba(139,92,246,0.16), transparent 42%),
            radial-gradient(circle at 50% 105%, rgba(34,211,238,0.14), transparent 50%);
        animation: glowDrift 14s ease-in-out infinite alternate;
    }}
    @keyframes glowDrift {{
        from {{ transform: translate(0px, 0px) scale(1); }}
        to   {{ transform: translate(18px, -14px) scale(1.06); }}
    }}
    section[data-testid="stAppViewContainer"], section[data-testid="stSidebar"] {{
        position: relative;
        z-index: 1;
    }}

    section[data-testid="stSidebar"] {{
        background-color: {bg_sidebar};
        border-right: 1px solid {border_col};
    }}

    /* Two-line hero wordmark: plain "Adaptive" + cyan-blue-violet "RAG Chat" */
    .hero-title-wrap {{
        text-align: center;
        position: relative;
        z-index: 1;
        margin-bottom: 0;
    }}
    .hero-title-line1 {{
        font-size: 1.9rem;
        font-weight: 800;
        color: {text_main};
        letter-spacing: 0.5px;
        animation: titlePop 0.5s ease-out;
    }}
    .hero-title-line2 {{
        font-size: 3.1rem;
        font-weight: 900;
        line-height: 1.1;
        background: {hero_grad};
        background-size: 200% auto;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        animation: titlePop 0.6s ease-out, shine 6s linear infinite;
    }}
    @keyframes titlePop {{
        from {{ opacity: 0; transform: scale(0.94); }}
        to   {{ opacity: 1; transform: scale(1); }}
    }}
    @keyframes shine {{
        to {{ background-position: 200% center; }}
    }}
    .hero-sub {{
        text-align: center;
        color: {text_dim};
        margin-top: 0.3rem;
        margin-bottom: 1.4rem;
        animation: titlePop 0.7s ease-out;
        position: relative;
        z-index: 1;
    }}
    .hero-sub b {{
        background: {hero_grad};
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }}

    /* Documents -> AI engine -> Vector store flow diagram (banner-style) */
    .brand-flow {{
        display: flex;
        align-items: center;
        justify-content: center;
        margin: 0.2rem 0 1.8rem 0;
        position: relative;
        z-index: 1;
    }}
    .flow-node {{
        width: 62px;
        height: 62px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.7rem;
        background: {bg_card};
        border: 1px solid {border_col};
        box-shadow: 0 0 22px rgba(80,150,255,0.28);
        animation: floatBot 4s ease-in-out infinite;
    }}
    .flow-brain {{
        width: 92px;
        height: 92px;
        font-size: 2.5rem;
        background: {hero_grad};
        border: none;
        animation: floatBot 3.2s ease-in-out infinite, pulseGlow 2.4s ease-in-out infinite;
    }}
    @keyframes floatBot {{
        0%, 100% {{ transform: translateY(0px); }}
        50%      {{ transform: translateY(-8px); }}
    }}
    @keyframes pulseGlow {{
        0%, 100% {{ box-shadow: 0 0 28px rgba(80,150,255,0.4); }}
        50%      {{ box-shadow: 0 0 55px rgba(139,92,246,0.75); }}
    }}
    .flow-line {{
        width: 64px;
        height: 2px;
        margin: 0 6px;
        background-image: repeating-linear-gradient(90deg, #67a9ff 0 6px, transparent 6px 13px);
        animation: flowMove 0.9s linear infinite;
    }}
    @keyframes flowMove {{
        to {{ background-position: -19px 0; }}
    }}

    /* Feature badge row (Adaptive Retrieval / Semantic Search / ...) */
    .feature-row {{
        display: flex;
        justify-content: center;
        gap: 2.4rem;
        flex-wrap: wrap;
        margin-bottom: 1.6rem;
        position: relative;
        z-index: 1;
    }}
    .feature-item {{
        display: flex;
        flex-direction: column;
        align-items: center;
        text-align: center;
        width: 96px;
        animation: itemIn 0.5s ease-out both;
        transition: transform 0.2s ease;
    }}
    .feature-item:nth-child(2) {{ animation-delay: 0.08s; }}
    .feature-item:nth-child(3) {{ animation-delay: 0.16s; }}
    .feature-item:nth-child(4) {{ animation-delay: 0.24s; }}
    .feature-item:hover {{ transform: translateY(-4px); }}
    .feature-icon {{
        width: 50px;
        height: 50px;
        border-radius: 50%;
        border: 1.5px solid rgba(120,160,255,0.5);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.3rem;
        margin-bottom: 6px;
        background: rgba(120,160,255,0.08);
        box-shadow: 0 0 16px rgba(80,150,255,0.25);
    }}
    .feature-label {{
        font-size: 0.72rem;
        color: {text_dim};
        font-weight: 600;
        line-height: 1.25;
    }}

    /* Tech stack strip at the bottom of the page */
    .tech-stack-row {{
        display: flex;
        justify-content: center;
        flex-wrap: wrap;
        gap: 0.5rem;
        margin-top: 1rem;
        position: relative;
        z-index: 1;
    }}
    .tech-pill {{
        background: {bg_card};
        border: 1px solid {border_col};
        border-radius: 20px;
        padding: 4px 12px;
        font-size: 0.75rem;
        color: {text_dim};
        font-weight: 600;
    }}

    /* Chat bubbles */
    .msg-row {{
        display: flex;
        margin-bottom: 0.9rem;
        animation: msgIn 0.35s ease-out both;
    }}
    @keyframes msgIn {{
        from {{ opacity: 0; transform: translateY(8px); }}
        to   {{ opacity: 1; transform: translateY(0); }}
    }}
    .msg-user {{ justify-content: flex-end; }}
    .msg-bot  {{ justify-content: flex-start; }}

    .bubble-user {{
        background: {accent_grad};
        color: white;
        padding: 0.7rem 1rem;
        border-radius: 14px 14px 2px 14px;
        max-width: 70%;
        font-weight: 500;
        white-space: pre-wrap;
        word-wrap: break-word;
    }}
    .bubble-bot {{
        background: {bg_card};
        border: 1px solid {border_col};
        color: {text_main};
        padding: 0.9rem 1.1rem;
        border-radius: 14px 14px 14px 2px;
        max-width: 78%;
        white-space: pre-wrap;
        word-wrap: break-word;
    }}
    .bubble-time {{
        font-size: 0.72rem;
        color: {text_dim};
        margin-bottom: 4px;
    }}
    .avatar {{
        width: 34px; height: 34px;
        border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        font-size: 1.1rem;
        flex-shrink: 0;
    }}
    .avatar-bot {{ background: {accent_grad}; margin-right: 10px; }}
    .avatar-user {{ background: {bg_card}; border: 1px solid {border_col}; margin-left: 10px; }}

    .sources-row {{
        margin-top: 0.6rem;
        padding-top: 0.6rem;
        border-top: 1px solid {border_col};
    }}
    .sources-label {{ color: #9b8bff; font-size: 0.78rem; font-weight: 600; margin-bottom: 6px; }}
    .source-pill {{
        display: inline-block;
        background: rgba(120,110,255,0.12);
        color: {text_main};
        border: 1px solid {border_col};
        border-radius: 8px;
        padding: 3px 9px;
        font-size: 0.75rem;
        margin-right: 6px;
        margin-bottom: 6px;
    }}

    /* Typing indicator (waiting for the backend) */
    .typing-row {{
        display: flex;
        margin-bottom: 0.9rem;
        animation: msgIn 0.25s ease-out both;
    }}
    .typing-bubble {{
        background: {bg_card};
        border: 1px solid {border_col};
        border-radius: 14px 14px 14px 2px;
        padding: 0.8rem 1.1rem;
        display: flex;
        align-items: center;
        gap: 5px;
    }}
    .typing-dot {{
        width: 7px; height: 7px;
        border-radius: 50%;
        background: #9b8bff;
        animation: dotPulse 1.1s ease-in-out infinite;
    }}
    .typing-dot:nth-child(2) {{ animation-delay: 0.15s; }}
    .typing-dot:nth-child(3) {{ animation-delay: 0.3s; }}
    @keyframes dotPulse {{
        0%, 60%, 100% {{ opacity: 0.3; transform: translateY(0); }}
        30% {{ opacity: 1; transform: translateY(-4px); }}
    }}

    /* Claude-style blinking text cursor while an answer is streaming in */
    .type-cursor {{
        display: inline-block;
        width: 2px;
        margin-left: 2px;
        background: #9b8bff;
        animation: cursorBlink 0.85s step-start infinite;
    }}
    @keyframes cursorBlink {{
        50% {{ opacity: 0; }}
    }}

    /* Sidebar history cards */
    .hist-card {{
        background: {bg_card};
        border: 1px solid {border_col};
        border-radius: 10px;
        padding: 0.5rem 0.7rem;
        margin-bottom: 0.5rem;
        transition: transform 0.15s ease, border-color 0.15s ease;
        animation: itemIn 0.35s ease-out both;
    }}
    .hist-card:hover {{ transform: translateX(3px); border-color: rgba(120,110,255,0.5); }}
    @keyframes itemIn {{
        from {{ opacity: 0; transform: translateX(-8px); }}
        to   {{ opacity: 1; transform: translateX(0); }}
    }}
    .hist-q {{ font-size: 0.85rem; color: {text_main}; }}
    .hist-t {{ font-size: 0.7rem; color: {text_dim}; }}

    /* Stat cards */
    .stat-card {{
        background: {bg_card};
        border: 1px solid {border_col};
        border-radius: 12px;
        padding: 0.7rem 0.9rem;
        margin-bottom: 0.6rem;
        animation: itemIn 0.4s ease-out both;
        transition: transform 0.15s ease, border-color 0.15s ease;
    }}
    .stat-card:hover {{ transform: translateY(-2px); border-color: rgba(120,110,255,0.4); }}
    .stat-label {{ font-size: 0.75rem; color: {text_dim}; }}
    .stat-value {{ font-size: 1.4rem; font-weight: 700; color: {text_main}; }}
    .stat-delta {{ font-size: 0.72rem; color: #4fd18b; }}

    /* Buttons */
    div.stButton > button {{
        border-radius: 10px;
        border: 1px solid {border_col};
        background-color: {bg_card};
        color: {text_main};
        font-weight: 600;
        transition: transform 0.15s ease, box-shadow 0.2s ease, border-color 0.2s ease;
    }}
    div.stButton > button:hover {{
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(80,110,255,0.25);
        border-color: rgba(120,110,255,0.55);
    }}
    div.stFormSubmitButton > button {{
        border-radius: 10px;
        background: {accent_grad};
        color: white;
        font-weight: 700;
        border: none;
        transition: transform 0.15s ease, box-shadow 0.2s ease, filter 0.2s ease;
    }}
    div.stFormSubmitButton > button:hover {{
        transform: translateY(-2px);
        box-shadow: 0 6px 18px rgba(120,110,255,0.35);
        filter: brightness(1.08);
    }}

    /* Input bar */
    div[data-testid="stTextInput"] input {{
        border-radius: 12px !important;
        transition: box-shadow 0.2s ease, border-color 0.2s ease;
    }}
    div[data-testid="stTextInput"] input:focus {{
        box-shadow: 0 0 0 3px rgba(120,110,255,0.25);
        border-color: rgba(120,110,255,0.7) !important;
    }}

    .footnote {{
        text-align: center;
        color: {text_dim};
        font-size: 0.78rem;
        margin-top: 0.8rem;
        animation: itemIn 0.6s ease-out both;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)


def file_signature(f):
    """Stable identity for an uploaded file across reruns."""
    return (f.name, f.size)


def esc(text) -> str:
    """
    HTML-escape any user- or model-provided text before it goes into an
    unsafe_allow_html block. Without this, a question or answer containing
    '<', '>' or '&' can break the bubble markup or, worse, get executed as
    HTML/JS in the page.
    """
    return html.escape(str(text))


def format_answer_html(text: str) -> str:
    """Escape the answer and turn newlines into <br> so multi-line answers
    (lists, steps, etc.) still read correctly inside the bubble."""
    return esc(text).replace("\n", "<br>")


def build_sources_html(entry: dict) -> str:
    """
    Render source pills if the backend provided any, with a graceful
    fallback: the current backend doesn't return document filenames, only
    which tool the agent called. If that's all we have, show a small
    "used document search" hint instead of silently showing nothing.
    """
    sources = entry.get("sources") or []
    if sources:
        pills = "".join(f'<span class="source-pill">📄 {esc(s)}</span>' for s in sources)
        return (
            '<div class="sources-row">'
            '<div class="sources-label">Sources:</div>'
            f'{pills}'
            '</div>'
        )

    tool_calls = entry.get("tool_calls") or []
    if tool_calls:
        pills = "".join(
            f'<span class="source-pill">🔎 searched: {esc(tc.get("input", ""))}</span>'
            for tc in tool_calls if tc.get("input")
        )
        if pills:
            return (
                '<div class="sources-row">'
                '<div class="sources-label">Document search used:</div>'
                f'{pills}'
                '</div>'
            )
    return ""


def build_user_bubble_html(entry: dict) -> str:
    return (
        '<div class="msg-row msg-user">'
        f'<div class="bubble-user">{esc(entry["question"])}</div>'
        '<div class="avatar avatar-user">🧑</div>'
        '</div>'
    )


def build_bot_bubble_html(entry: dict, answer_override: str = None, show_cursor: bool = False) -> str:
    """
    IMPORTANT: every line here is built with no leading indentation inside
    the f-strings. Markdown treats 4+ leading spaces as a code block, so
    stray indentation combined with the AI answer's own line breaks can
    push the closing </div></div> past that threshold and make it render
    as literal text instead of closing the HTML tags.
    """
    answer_source = entry["answer"] if answer_override is None else answer_override
    answer_html = format_answer_html(answer_source)
    cursor_html = '<span class="type-cursor">&nbsp;</span>' if show_cursor else ""
    sources_html = "" if show_cursor else build_sources_html(entry)

    return (
        '<div class="msg-row msg-bot">'
        '<div class="avatar avatar-bot">🤖</div>'
        '<div class="bubble-bot">'
        f'<div class="bubble-time">{esc(entry["time"])}</div>'
        f'{answer_html}{cursor_html}'
        f'{sources_html}'
        '</div>'
        '</div>'
    )


def stream_bot_bubble(entry: dict, placeholder) -> None:
    """
    Claude-style progressive reveal: types the answer into the placeholder
    a few words at a time instead of dumping the whole thing in at once.
    Speed scales with answer length so a long answer doesn't take forever.
    """
    words = entry["answer"].split(" ")
    total = len(words)
    if total == 0:
        placeholder.markdown(build_bot_bubble_html(entry), unsafe_allow_html=True)
        return

    # Cap the number of visual "frames" so very long answers don't crawl.
    step = max(1, total // 60)
    delay = 0.02

    shown_words = []
    for i in range(0, total, step):
        shown_words = words[: i + step]
        partial = " ".join(shown_words)
        placeholder.markdown(
            build_bot_bubble_html(entry, answer_override=partial, show_cursor=True),
            unsafe_allow_html=True,
        )
        time.sleep(delay)

    # Final frame: full text, no cursor, sources visible.
    placeholder.markdown(build_bot_bubble_html(entry), unsafe_allow_html=True)


# ------------------------------------------------------------------
# SIDEBAR
# ------------------------------------------------------------------
with st.sidebar:
    st.markdown("### 🤖 Adaptive RAG")
    st.markdown("---")

    st.markdown("**🕘 Chat History**")
    st.session_state.history_search = st.text_input(
        "Search history...", value=st.session_state.history_search,
        label_visibility="collapsed", placeholder="Search history..."
    )

    # Keep the ORIGINAL index from chat_log as the button key, not the
    # position within the filtered/reversed list — otherwise keys collide
    # or shift as the search text changes, causing stale reruns.
    indexed_log = list(enumerate(st.session_state.chat_log))
    filtered = [
        (i, e) for i, e in reversed(indexed_log)
        if st.session_state.history_search.lower() in e["question"].lower()
    ]

    if not filtered:
        st.caption("No matching history yet.")
    else:
        for i, entry in filtered:
            short_q = entry["question"] if len(entry["question"]) <= 40 else entry["question"][:37] + "..."
            st.markdown(
                f'<div class="hist-card">'
                f'<div class="hist-q">💬 {esc(short_q)}</div>'
                f'<div class="hist-t">{esc(entry["time"])}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            if st.button("Ask again", key=f"reuse_{i}", use_container_width=True):
                st.session_state.question_input = entry["question"]
                st.rerun()

    if st.button("🗑️ Clear History", use_container_width=True):
        st.session_state.chat_log = []
        st.session_state.stream_next = False
        st.rerun()

    st.markdown("---")
    st.markdown("**📊 Dashboard**")

    total_q = len(st.session_state.chat_log)
    avg_time = (
        sum(e.get("elapsed", 0) for e in st.session_state.chat_log) / total_q
        if total_q else 0
    )

    st.markdown(
        f'<div class="stat-card">'
        f'<div class="stat-label">Total Questions</div>'
        f'<div class="stat-value">{total_q}</div>'
        f'</div>'
        f'<div class="stat-card">'
        f'<div class="stat-label">Documents Uploaded</div>'
        f'<div class="stat-value">{st.session_state.doc_count}</div>'
        f'</div>'
        f'<div class="stat-card">'
        f'<div class="stat-label">Avg Response Time</div>'
        f'<div class="stat-value">{avg_time:.2f}s</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown("---")
    with st.expander("📎 Upload Document"):
        uploaded_file = st.file_uploader(
            "Upload a PDF or TXT file", type=["pdf", "txt"], label_visibility="collapsed"
        )
        if uploaded_file:
            sig = file_signature(uploaded_file)
            # st.file_uploader keeps returning the same file object on every
            # rerun of the whole app (e.g. every time you send a chat
            # message), which would otherwise silently re-upload it and
            # bump "Documents Uploaded" each time. Only upload a signature
            # we haven't already sent.
            if sig in st.session_state.uploaded_files_seen:
                st.success("Uploaded!")
            else:
                with st.spinner("Uploading..."):
                    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                    headers = {"X-Description": uploaded_file.name}
                    try:
                        resp = requests.post(
                            f"{BACKEND_URL}/rag/documents/upload",
                            files=files, headers=headers, timeout=60,
                        )
                        if resp.status_code == 200:
                            st.session_state.uploaded_files_seen.add(sig)
                            st.session_state.doc_count += 1
                            st.success("Uploaded!")
                            st.toast(f"📄 {uploaded_file.name} added", icon="✅")
                        else:
                            st.error(resp.text)
                    except Exception as e:
                        st.error(f"Upload failed: {e}")

    st.markdown("---")
    dm_col1, dm_col2 = st.columns([3, 1])
    with dm_col1:
        st.markdown("🌙 Dark Mode" if st.session_state.dark_mode else "☀️ Light Mode")
    with dm_col2:
        if st.button("Toggle", key="theme_toggle"):
            st.session_state.dark_mode = not st.session_state.dark_mode
            st.rerun()

    st.markdown("---")
    st.caption("Made with ❤️ using Streamlit")

# ------------------------------------------------------------------
# MAIN AREA
# ------------------------------------------------------------------
st.markdown(
    '<div class="hero-title-wrap">'
    '<div class="hero-title-line1">Adaptive</div>'
    '<div class="hero-title-line2">RAG Chat ✨</div>'
    '</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="hero-sub">AI-Powered <b>Retrieval-Augmented Generation</b> System</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="brand-flow">'
    '<div class="flow-node" title="Your documents">📄</div>'
    '<div class="flow-line"></div>'
    '<div class="flow-node flow-brain" title="AI engine">🧠</div>'
    '<div class="flow-line"></div>'
    '<div class="flow-node" title="Vector store">🗄️</div>'
    '</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="feature-row">'
    '<div class="feature-item"><div class="feature-icon">🔍</div>'
    '<div class="feature-label">Adaptive<br>Retrieval</div></div>'
    '<div class="feature-item"><div class="feature-icon">🗂️</div>'
    '<div class="feature-label">Semantic<br>Search</div></div>'
    '<div class="feature-item"><div class="feature-icon">💬</div>'
    '<div class="feature-label">Context-Aware<br>Responses</div></div>'
    '<div class="feature-item"><div class="feature-icon">🧠</div>'
    '<div class="feature-label">AI-Powered<br>Generation</div></div>'
    '</div>',
    unsafe_allow_html=True,
)

# Render conversation
last_index = len(st.session_state.chat_log) - 1
for idx, entry in enumerate(st.session_state.chat_log):
    st.markdown(build_user_bubble_html(entry), unsafe_allow_html=True)

    if idx == last_index and st.session_state.stream_next:
        # Newest answer: type it out once, Claude-style, then freeze it.
        bot_placeholder = st.empty()
        stream_bot_bubble(entry, bot_placeholder)
        st.session_state.stream_next = False
    else:
        # Already-seen history: render instantly, no replaying the animation.
        st.markdown(build_bot_bubble_html(entry), unsafe_allow_html=True)

# Animated typing indicator while a request is in flight
thinking_placeholder = st.empty()
if st.session_state.is_thinking:
    thinking_placeholder.markdown(
        '<div class="typing-row">'
        '<div class="avatar avatar-bot">🤖</div>'
        '<div class="typing-bubble">'
        '<div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>'
        '</div></div>',
        unsafe_allow_html=True,
    )

st.write("")

# ------------------------------------------------------------------
# Input bar
# Wrapped in st.form so pressing Enter submits the question, not just
# clicking the Send button.
# ------------------------------------------------------------------
with st.form(key="ask_form", clear_on_submit=False):
    col_input, col_send = st.columns([6, 1])
    with col_input:
        question = st.text_input(
            "Ask anything...", key="question_input",
            label_visibility="collapsed", placeholder="Ask anything..."
        )
    with col_send:
        send_clicked = st.form_submit_button("➤ Send", use_container_width=True)

if send_clicked:
    if question.strip():
        st.session_state.is_thinking = True
        thinking_placeholder.markdown(
            '<div class="typing-row">'
            '<div class="avatar avatar-bot">🤖</div>'
            '<div class="typing-bubble">'
            '<div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>'
            '</div></div>',
            unsafe_allow_html=True,
        )
        try:
            start = time.time()
            response = requests.post(
                f"{BACKEND_URL}/rag/query",
                json={"query": question, "session_id": "demo-session"},
                timeout=60,
            )
            elapsed = time.time() - start

            if response.status_code == 200:
                data = response.json()

                answer_text = "No answer found."
                sources = []
                tool_calls = []
                if "result" in data:
                    result = data["result"]
                    if isinstance(result, dict):
                        answer_text = result.get("content", "No answer found.")
                        sources = result.get("sources", [])
                        tool_calls = (result.get("additional_kwargs") or {}).get("tool_calls", [])
                    else:
                        answer_text = str(result)
                elif "content" in data:
                    answer_text = data["content"]
                    sources = data.get("sources", [])

                st.session_state.chat_log.append({
                    "question": question,
                    "answer": answer_text,
                    # "%H:%M %p" mixes 24-hour format with an AM/PM marker,
                    # producing nonsense like "17:20 PM". %I gives a proper
                    # 12-hour value that actually matches %p.
                    "time": datetime.now().strftime("%I:%M %p"),
                    "sources": sources,
                    "tool_calls": tool_calls,
                    "elapsed": elapsed,
                })
                st.session_state.clear_input = True
                st.session_state.is_thinking = False
                st.session_state.stream_next = True
                st.rerun()
            else:
                st.session_state.is_thinking = False
                thinking_placeholder.empty()  # don't leave the dots stuck on screen
                st.error(f"Error: {response.status_code}")
                st.text(response.text)
        except Exception as e:
            st.session_state.is_thinking = False
            thinking_placeholder.empty()  # don't leave the dots stuck on screen
            st.error(f"Request failed: {e}")
    else:
        st.warning("Please enter a question.")

st.markdown(
    '<div class="footnote">🔒 Your data is safe and secure. No data is stored without your permission.</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="tech-stack-row">'
    '<span class="tech-pill">🐍 Python</span>'
    '<span class="tech-pill">⚡ FastAPI</span>'
    '<span class="tech-pill">🎈 Streamlit</span>'
    '<span class="tech-pill">🔗 LangChain</span>'
    '<span class="tech-pill">📊 FAISS</span>'
    '<span class="tech-pill">🧠 LLM</span>'
    '</div>',
    unsafe_allow_html=True,
)
