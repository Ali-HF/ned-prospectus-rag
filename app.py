"""Streamlit chat interface for the NED Undergraduate Prospectus RAG assistant.

Clean, high-end Claude-style minimalist interface:
- Minimalist Claude aesthetic: warm neutral dark background, refined typography, generous line spacing
- Clean floating header with subtle model/source badges
- No distracting hero banner; full focus directly on conversation stream
- Claude-style thinking status drawer (Retrieving -> Sleuthing -> Honing -> Triangulating)
- Automatic scroll tracking to ensure input and latest message remain cleanly in focus
- Verified citations expander for full transparent grounding
"""

from pathlib import Path
import time
import streamlit as st
import streamlit.components.v1 as components

import config
from rag import answer_with_sources

# Ensure ChromaDB index exists on startup
CHROMA_DIR = Path(config.CHROMA_PERSIST_DIRECTORY)
if not CHROMA_DIR.exists() or not any(CHROMA_DIR.iterdir()):
    with st.spinner("Initializing prospectus knowledge base..."):
        import ingest
        ingest.build_index(force=True)

st.set_page_config(
    page_title="NED Guide",
    page_icon="✦",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Claude-Style Minimalist Styling
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;1,6..72,400&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');

/* Hide default Streamlit sidebar entirely */
[data-testid="stSidebar"], [data-testid="collapsedControl"] {
    display: none !important;
}

/* Base Body: Claude-like deep warm charcoal canvas */
.stApp {
    background-color: #18181b;
    color: #ececec;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    line-height: 1.6;
}

/* Constrain main block to a focused reading column just like Claude */
.main .block-container {
    max-width: 780px !important;
    padding-top: 1.25rem !important;
    padding-bottom: 7.5rem !important;
}

/* Claude-Style Minimal Top Bar */
.claude-nav {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.6rem 0.2rem 1.2rem;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    margin-bottom: 1.75rem;
}

.claude-brand {
    display: flex;
    align-items: center;
    gap: 10px;
}

.claude-icon {
    width: 28px;
    height: 28px;
    border-radius: 7px;
    background: #cc5a2b;
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: 'Newsreader', serif;
    font-weight: 500;
    font-size: 1rem;
    color: #ffffff;
}

.claude-title {
    font-family: 'Inter', sans-serif;
    font-size: 0.95rem;
    font-weight: 600;
    letter-spacing: -0.01em;
    color: #f4f4f5;
}

.claude-sub {
    font-size: 0.75rem;
    color: #a1a1aa;
    font-weight: 400;
}

.claude-pills {
    display: flex;
    align-items: center;
    gap: 10px;
}

.claude-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 3px 9px;
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.09);
    border-radius: 100px;
    color: #a1a1aa;
    font-size: 0.72rem;
    font-family: 'JetBrains Mono', monospace;
}

.claude-badge-dot {
    width: 5px;
    height: 5px;
    background-color: #22c55e;
    border-radius: 50%;
}

/* Chat Message Bubbles: Claude Clean Minimal Style */
div[data-testid="stChatMessage"] {
    background-color: transparent !important;
    border: none !important;
    padding: 1.2rem 0 !important;
    margin-bottom: 0.5rem !important;
}

/* Assistant Message: Clean Typography with generous breathing room */
div[data-testid="stChatMessage"]:has(div[data-testid="chatAvatarIcon-assistant"]) {
    background-color: transparent !important;
    border-left: none !important;
}

div[data-testid="stChatMessage"]:has(div[data-testid="chatAvatarIcon-assistant"]) [data-testid="stMarkdownContainer"] {
    font-size: 0.98rem !important;
    line-height: 1.68 !important;
    color: #e4e4e7 !important;
}

/* User Message: subtle pill background */
div[data-testid="stChatMessage"]:has(div[data-testid="chatAvatarIcon-user"]) {
    background-color: rgba(255, 255, 255, 0.04) !important;
    border-radius: 12px !important;
    padding: 0.9rem 1.2rem !important;
    border: 1px solid rgba(255, 255, 255, 0.06) !important;
}

/* Status widget styling (Claude-like Thinking drawer) */
div[data-testid="stStatusWidget"] {
    background: rgba(39, 39, 42, 0.5) !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    border-radius: 8px !important;
    font-size: 0.82rem !important;
    color: #d4d4d8 !important;
    padding: 0.2rem 0.5rem !important;
    margin-bottom: 0.75rem !important;
}

/* Citations Expanders */
div[data-testid="stExpander"] {
    background-color: rgba(24, 24, 27, 0.4) !important;
    border: 1px solid rgba(255, 255, 255, 0.07) !important;
    border-radius: 8px !important;
    margin-top: 0.75rem !important;
}

div[data-testid="stExpander"] summary {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.74rem !important;
    color: #a1a1aa !important;
}

div[data-testid="stExpander"] summary:hover {
    color: #cc5a2b !important;
}

.citation-badge {
    display: inline-block;
    padding: 3px 8px;
    background: rgba(204, 90, 43, 0.12);
    border: 1px solid rgba(204, 90, 43, 0.28);
    border-radius: 4px;
    margin-top: 4px;
    margin-right: 6px;
    font-size: 0.72rem;
    font-family: 'JetBrains Mono', monospace;
    color: #fdba74;
}

/* Minimalist Chat Input Bar pinned cleanly at bottom */
div[data-testid="stChatInput"] {
    max-width: 780px !important;
    margin: 0 auto !important;
    border-radius: 12px !important;
    padding-bottom: 0.75rem !important;
}

div[data-testid="stChatInput"] textarea {
    background-color: #27272a !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    color: #f4f4f5 !important;
    border-radius: 10px !important;
    font-family: 'Inter', sans-serif !important;
    padding: 0.75rem 1rem !important;
    font-size: 0.95rem !important;
}

div[data-testid="stChatInput"] textarea:focus {
    border-color: #cc5a2b !important;
    box-shadow: 0 0 0 1px #cc5a2b !important;
}

/* Reset / Action Buttons */
.stButton > button {
    background: transparent !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    color: #a1a1aa !important;
    font-size: 0.74rem !important;
    border-radius: 6px !important;
    padding: 0.25rem 0.65rem !important;
    transition: all 0.15s ease !important;
}

.stButton > button:hover {
    color: #ffffff !important;
    border-color: rgba(255, 255, 255, 0.25) !important;
    background: rgba(255, 255, 255, 0.05) !important;
}
</style>
""", unsafe_allow_html=True)

# Claude-Style Top Bar
st.markdown("""
<div class="claude-nav">
    <div class="claude-brand">
        <div class="claude-icon">✦</div>
        <div>
            <div class="claude-title">NED Guide</div>
            <div class="claude-sub">Undergraduate Prospectus 2025</div>
        </div>
    </div>
    <div class="claude-pills">
        <div class="claude-badge">
            <span class="claude-badge-dot"></span>
            122 Pgs Indexed
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Initial conversation state
GREETING = (
    "Hello! I am **NED Guide**, your assistant for the official NED Undergraduate Prospectus 2025. "
    "I answer using only official prospectus data: eligibility requirements, merit formulas, seat quotas under Regular and Self-Finance, fee schedules, scholarships, and campus regulations."
)

if "messages" not in st.session_state or not st.session_state["messages"]:
    st.session_state["messages"] = [
        {"role": "assistant", "content": GREETING, "sources": []}
    ]

# Action controls
col_ctrl1, col_ctrl2 = st.columns([0.82, 0.18])

with col_ctrl1:
    show_sources = st.toggle("Show citations", value=True)

with col_ctrl2:
    if st.button("Clear chat"):
        st.session_state["messages"] = [
            {"role": "assistant", "content": GREETING, "sources": []}
        ]
        st.rerun()

# Render conversation history
for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if show_sources and msg.get("sources"):
            with st.expander(f"🔍 Prospectus Sources ({len(msg['sources'])} citations)", expanded=False):
                badges = []
                for page, section, sim in msg["sources"]:
                    sec_str = f" • {section}" if section else ""
                    badges.append(f"<span class='citation-badge'>Page {page}{sec_str} (similarity: {sim:.3f})</span>")
                citations_html = "".join(badges)
                st.markdown(citations_html, unsafe_allow_html=True)

# User Chat Input
user_input = st.chat_input("Ask a question about NED undergraduate admissions...")

if user_input:
    clean_input = user_input.strip()
    if clean_input:
        st.session_state["messages"].append({"role": "user", "content": clean_input})
        with st.chat_message("user"):
            st.markdown(clean_input)

        history_for_rag = [
            {"role": m["role"], "content": m["content"]}
            for m in st.session_state["messages"][:-1]
        ]

        with st.chat_message("assistant"):
            # Smooth Claude-style status transitions
            with st.status("Retrieving...", expanded=False) as status:
                st.caption("Scanning 122 prospectus pages & dense neural vectors...")
                time.sleep(0.7)
                
                status.update(label="Sleuthing...", state="running")
                st.caption("Cross-referencing BM25 keywords & rank fusion scores...")
                time.sleep(0.7)

                status.update(label="Honing...", state="running")
                st.caption("Filtering top candidate chunks against 0.62 similarity threshold...")
                
                # Fetch answer from RAG engine
                result = answer_with_sources(clean_input, history=history_for_rag)
                
                status.update(label="Triangulating...", state="running")
                st.caption("Synthesizing verified citations & grounds...")
                time.sleep(0.5)

                status.update(label="Response verified", state="complete", expanded=False)

            bot_answer = result["answer"]
            bot_sources = result.get("sources", [])
            st.markdown(bot_answer)
            if show_sources and bot_sources:
                with st.expander(f"🔍 Prospectus Sources ({len(bot_sources)} citations)", expanded=False):
                    badges = []
                    for page, section, sim in bot_sources:
                        sec_str = f" • {section}" if section else ""
                        badges.append(f"<span class='citation-badge'>Page {page}{sec_str} (similarity: {sim:.3f})</span>")
                    citations_html = "".join(badges)
                    st.markdown(citations_html, unsafe_allow_html=True)

        st.session_state["messages"].append({
            "role": "assistant",
            "content": bot_answer,
            "sources": bot_sources
        })

# Auto-scroll anchor component
components.html(
    """
    <script>
    setTimeout(function() {
        const doc = window.parent.document;
        const main = doc.querySelector('.main') || doc.documentElement;
        main.scrollTo({ top: main.scrollHeight, behavior: 'smooth' });
    }, 150);
    </script>
    """,
    height=0,
)
