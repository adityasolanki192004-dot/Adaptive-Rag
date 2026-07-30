import streamlit as st
import requests
import time
from datetime import datetime

# ------------------------------------------------------------------
# Config
# ------------------------------------------------------------------
BACKEND_URL = "https://adaptive-rag-backend-fyyu.onrender.com"

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
    # BUG FIX: tracks (name, size) pairs already sent to the backend so the
    # widget's persisted file doesn't get re-uploaded on every rerun
    # (e.g. every time a chat message is sent). This was inflating the
    # "Documents Uploaded" counter (18 for a single file in the screenshot).
    st.session_state.uploaded_files_seen = set()
if "is_thinking" not in st.session_state:
    st.session_state.is_thinking = False
if "upload_toast" not in st.session_state:
    st.session_state.upload_toast = None

# Clear the input BEFORE the widget is instantiated this run (safe to do here)
if st.session_state.clear_input:
    st.session_state.question_input = ""
    st.session_state.clear_input = False

# ------------------------------------------------------------------
# Theme colors
# ------------------------------------------------------------------
if st.session_state.dark_mode:
    bg_main = "#0b0c10"
    bg_card = "#14151c"
    bg_sidebar = "#0e0f15"
    text_main = "#f2f2f5"
    text_dim = "#9a9daa"
    border_col = "rgba(255,255,255,0.08)"
else:
    bg_main = "#f5f6fa"
    bg_card = "#ffffff"
    bg_sidebar = "#ffffff"
    text_main = "#1a1c23"
    text_dim = "#5c5f6b"
    border_col = "rgba(0,0,0,0.08)"

accent_grad = "linear-gradient(90deg, #4f7cff, #9b5cff)"

# ------------------------------------------------------------------
# CSS
# ------------------------------------------------------------------
st.markdown(
    f"""
    <style>
    .stApp {{
        background-color: {bg_main};
        color: {text_main};
        animation: pageFadeIn 0.5s ease-out;
    }}
    @keyframes pageFadeIn {{
        from {{ opacity: 0; transform: translateY(10px); }}
        to   {{ opacity: 1; transform: translateY(0); }}
    }}

    section[data-testid="stSidebar"] {{
        background-color: {bg_sidebar};
        border-right: 1px solid {border_col};
    }}

    /* Gradient hero title */
    .hero-title {{
        font-size: 2.6rem;
        font-weight: 800;
        text-align: center;
        background: {accent_grad};
        background-size: 200% auto;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        animation: titlePop 0.6s ease-out, shine 6s linear infinite;
        margin-bottom: 0;
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
        margin-top: 0.2rem;
        margin-bottom: 1.2rem;
        animation: titlePop 0.7s ease-out;
    }}

    /* Animated bot avatar (stand-in for mascot illustration) */
    .mascot-wrap {{
        display: flex;
        justify-content: center;
        margin-bottom: 1.5rem;
    }}
    .mascot {{
        width: 90px;
        height: 90px;
        border-radius: 50%;
        background: {accent_grad};
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 2.6rem;
        box-shadow: 0 0 40px rgba(120,110,255,0.45);
        animation: floatBot 3s ease-in-out infinite;
    }}
    @keyframes floatBot {{
        0%, 100% {{ transform: translateY(0px) rotate(0deg); }}
        50%      {{ transform: translateY(-8px) rotate(3deg); }}
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
    }}
    .bubble-bot {{
        background: {bg_card};
        border: 1px solid {border_col};
        color: {text_main};
        padding: 0.9rem 1.1rem;
        border-radius: 14px 14px 14px 2px;
        max-width: 78%;
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

    /* Typing indicator */
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

    # BUG FIX: keep the ORIGINAL index from chat_log as the button key,
    # not the position within the filtered/reversed list — otherwise keys
    # collide or shift as the search text changes, causing stale reruns.
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
                f'<div class="hist-q">💬 {short_q}</div>'
                f'<div class="hist-t">{entry["time"]}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            if st.button("Ask again", key=f"reuse_{i}", use_container_width=True):
                st.session_state.question_input = entry["question"]
                st.rerun()

    if st.button("🗑️ Clear History", use_container_width=True):
        st.session_state.chat_log = []
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
            # BUG FIX: st.file_uploader keeps returning the same file object
            # on every rerun of the whole app (e.g. every time you send a
            # chat message), which was silently re-uploading it and bumping
            # "Documents Uploaded" each time. Only upload a signature we
            # haven't already sent.
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
st.markdown('<div class="hero-title">Adaptive RAG Chat ✨</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-sub">Ask anything from your documents</div>', unsafe_allow_html=True)
st.markdown('<div class="mascot-wrap"><div class="mascot">🤖</div></div>', unsafe_allow_html=True)

# Render conversation
for entry in st.session_state.chat_log:
    st.markdown(
        f'<div class="msg-row msg-user">'
        f'<div class="bubble-user">{entry["question"]}</div>'
        f'<div class="avatar avatar-user">🧑</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    sources_html = ""
    if entry.get("sources"):
        pills = "".join(f'<span class="source-pill">📄 {s}</span>' for s in entry["sources"])
        sources_html = (
            f'<div class="sources-row">'
            f'<div class="sources-label">Sources:</div>'
            f'{pills}'
            f'</div>'
        )

    # IMPORTANT: every line below is flush-left (no leading spaces).
    # Markdown treats 4+ leading spaces as an indented code block, so any
    # indentation here — combined with the AI answer's own line breaks —
    # can push the closing "</div></div>" past that 4-space threshold and
    # cause it to render as literal text instead of closing the HTML tags.
    # Keeping it flush-left, in a single st.markdown call, avoids that.
    bot_bubble_html = (
        f'<div class="msg-row msg-bot">'
        f'<div class="avatar avatar-bot">🤖</div>'
        f'<div class="bubble-bot">'
        f'<div class="bubble-time">{entry["time"]}</div>'
        f'{entry["answer"]}'
        f'{sources_html}'
        f'</div>'
        f'</div>'
    )
    st.markdown(bot_bubble_html, unsafe_allow_html=True)

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
# BUG FIX: wrapped in st.form so pressing Enter submits the question,
# not just clicking the Send button.
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
                if "result" in data:
                    result = data["result"]
                    if isinstance(result, dict):
                        answer_text = result.get("content", "No answer found.")
                        sources = result.get("sources", [])
                    else:
                        answer_text = str(result)
                elif "content" in data:
                    answer_text = data["content"]
                    sources = data.get("sources", [])

                st.session_state.chat_log.append({
                    "question": question,
                    "answer": answer_text,
                    # BUG FIX: "%H:%M %p" mixed 24-hour format with an AM/PM
                    # marker, producing nonsense like "17:20 PM". %I gives a
                    # proper 12-hour value that actually matches %p.
                    "time": datetime.now().strftime("%I:%M %p"),
                    "sources": sources,
                    "elapsed": elapsed,
                })
                st.session_state.clear_input = True
                st.session_state.is_thinking = False
                st.rerun()
            else:
                st.session_state.is_thinking = False
                st.error(f"Error: {response.status_code}")
                st.text(response.text)
        except Exception as e:
            st.session_state.is_thinking = False
            st.error(f"Request failed: {e}")
    else:
        st.warning("Please enter a question.")

st.markdown(
    '<div class="footnote">🔒 Your data is safe and secure. No data is stored without your permission.</div>',
    unsafe_allow_html=True,
)
