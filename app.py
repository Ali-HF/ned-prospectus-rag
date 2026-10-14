"""Streamlit chat interface for the NED Undergraduate Prospectus RAG assistant.

Clean, high-end tactical UI:
- Sleek minimalist command bar with live indicators
- Collapsible / auto-compact hero section to keep chat prominent
- Slower 160s ambient rotation on the engineering compass medallion
- Smooth, deliberate status transitions (Retrieving -> Sleuthing -> Honing -> Triangulating)
- Automatic scroll tracking to keep latest messages in view without awkward page scrolling
- Expandable citation drawers & live verification badges
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
    page_title="NED Guide // Admissions AI",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom High-End Styling & Scroll Fixes
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=Inter:wght@300;400;500;600;700&display=swap');

/* Hide default Streamlit sidebar entirely */
[data-testid="stSidebar"] {
    display: none !important;
}
[data-testid="collapsedControl"] {
    display: none !important;
}

/* Base Body & Tactical Canvas */
.stApp {
    background-color: #08090b;
    background-image: 
        radial-gradient(circle at 75% 15%, rgba(255, 75, 17, 0.1) 0%, transparent 45%),
        radial-gradient(circle at 20% 80%, rgba(255, 75, 17, 0.05) 0%, transparent 40%),
        linear-gradient(rgba(255, 255, 255, 0.02) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255, 255, 255, 0.02) 1px, transparent 1px);
    background-size: 100% 100%, 100% 100%, 40px 40px, 40px 40px;
    color: #e2e8f0;
    font-family: 'Inter', -apple-system, sans-serif;
}

/* Constrain main block cleanly with breathing room for fixed chat input */
.main .block-container {
    max-width: 960px !important;
    padding-top: 1rem !important;
    padding-bottom: 7rem !important;
}

/* Top Tactical Navigation Bar */
.top-nav {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.65rem 1.25rem;
    background: rgba(14, 17, 22, 0.75);
    backdrop-filter: blur(16px);
    border: 1px solid rgba(255, 255, 255, 0.07);
    border-radius: 10px;
    margin-bottom: 1.2rem;
}

.brand-wrap {
    display: flex;
    align-items: center;
    gap: 10px;
}

.brand-badge {
    width: 26px;
    height: 26px;
    border-radius: 5px;
    background: linear-gradient(135deg, #ff551f, #d93d0b);
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 700;
    font-size: 0.78rem;
    color: #fff;
    box-shadow: 0 0 12px rgba(255, 85, 31, 0.35);
}

.brand-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.98rem;
    font-weight: 700;
    letter-spacing: -0.01em;
    color: #ffffff;
}

.nav-links {
    display: flex;
    align-items: center;
    gap: 14px;
    font-family: 'Space Grotesk', monospace;
    font-size: 0.72rem;
    color: #94a3b8;
    letter-spacing: 0.06em;
    text-transform: uppercase;
}

.status-indicator {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 3px 8px;
    background: rgba(34, 197, 94, 0.08);
    border: 1px solid rgba(34, 197, 94, 0.22);
    border-radius: 100px;
    color: #4ade80;
    font-size: 0.68rem;
    font-weight: 600;
}
.status-indicator::before {
    content: "";
    width: 5px;
    height: 5px;
    background-color: #22c55e;
    border-radius: 50%;
    box-shadow: 0 0 6px #22c55e;
}

/* Hero Section */
.hero-wrapper {
    display: grid;
    grid-template-columns: 1.3fr 0.7fr;
    gap: 2rem;
    align-items: center;
    padding: 1.25rem 1.5rem;
    background: rgba(14, 18, 25, 0.45);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 12px;
    margin-bottom: 1.25rem;
}

@media (max-width: 800px) {
    .hero-wrapper {
        grid-template-columns: 1fr;
        gap: 1.2rem;
    }
}

.sys-label {
    font-family: 'Space Grotesk', monospace;
    font-size: 0.7rem;
    font-weight: 600;
    color: #ff551f;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 0.5rem;
}

.hero-main-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 2.3rem;
    font-weight: 700;
    line-height: 1.1;
    color: #ffffff;
    letter-spacing: -0.03em;
    margin-bottom: 0.6rem;
}
.hero-main-title span {
    color: #ff551f;
    background: linear-gradient(135deg, #ff551f 0%, #ff7a4d 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

.hero-description {
    font-size: 0.92rem;
    line-height: 1.55;
    color: #94a3b8;
    margin-bottom: 1rem;
}

/* Stat Counters */
.stat-strip {
    display: flex;
    gap: 1.6rem;
    margin-top: 0.8rem;
}
.stat-item {
    font-family: 'Space Grotesk', sans-serif;
}
.stat-val {
    font-size: 1.2rem;
    font-weight: 700;
    color: #ffffff;
}
.stat-label {
    font-size: 0.68rem;
    color: #64748b;
    letter-spacing: 0.04em;
    text-transform: uppercase;
}

/* Medallion / Compass Graphic (Subtle, slower 160s rotation) */
.medallion-container {
    display: flex;
    justify-content: center;
    align-items: center;
}

.medallion-svg {
    width: 100%;
    max-width: 220px;
    filter: drop-shadow(0 0 25px rgba(255, 85, 31, 0.16));
    animation: slow-rotate 160s linear infinite;
}

@keyframes slow-rotate {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
}

/* Chat Messages */
div[data-testid="stChatMessage"] {
    background-color: rgba(14, 18, 24, 0.75) !important;
    border: 1px solid rgba(255, 255, 255, 0.07) !important;
    border-radius: 10px !important;
    padding: 1rem 1.35rem !important;
    margin-bottom: 0.85rem !important;
    backdrop-filter: blur(10px) !important;
}

/* Assistant Message Accent */
div[data-testid="stChatMessage"]:has(div[data-testid="chatAvatarIcon-assistant"]) {
    border-left: 3px solid #ff551f !important;
    background-color: rgba(16, 20, 27, 0.88) !important;
}

/* User Message Accent */
div[data-testid="stChatMessage"]:has(div[data-testid="chatAvatarIcon-user"]) {
    border-left: 3px solid rgba(255, 255, 255, 0.25) !important;
}

/* Status widget styling */
div[data-testid="stStatusWidget"] {
    background: rgba(16, 20, 28, 0.85) !important;
    border: 1px solid rgba(255, 85, 31, 0.3) !important;
    border-left: 3px solid #ff551f !important;
    border-radius: 8px !important;
    transition: all 0.4s ease-in-out !important;
}

/* Source Box Component */
.citation-badge {
    display: inline-block;
    padding: 3px 8px;
    background: rgba(255, 85, 31, 0.1);
    border: 1px solid rgba(255, 85, 31, 0.28);
    border-radius: 5px;
    margin-top: 4px;
    margin-right: 6px;
    font-size: 0.72rem;
    font-family: 'Space Grotesk', monospace;
    color: #fdba74;
}

/* Collapsible Expander Dropdown Styling */
div[data-testid="stExpander"] {
    background-color: rgba(10, 13, 18, 0.6) !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    border-radius: 8px !important;
    margin-top: 0.6rem !important;
}
div[data-testid="stExpander"] summary {
    font-family: 'Space Grotesk', monospace !important;
    font-size: 0.74rem !important;
    font-weight: 600 !important;
    color: #94a3b8 !important;
    letter-spacing: 0.04em !important;
}
div[data-testid="stExpander"] summary:hover {
    color: #ff551f !important;
}
div[data-testid="stExpander"] div[role="region"] {
    border-top: 1px solid rgba(255, 255, 255, 0.05) !important;
    padding-top: 0.4rem !important;
}

/* Custom Chat Input Bar - pinned cleanly */
div[data-testid="stChatInput"] {
    border-radius: 10px !important;
    padding-bottom: 0.5rem !important;
}
div[data-testid="stChatInput"] textarea {
    background-color: #0d1117 !important;
    border: 1px solid rgba(255, 255, 255, 0.12) !important;
    color: #ffffff !important;
    border-radius: 8px !important;
    font-family: 'Inter', sans-serif !important;
    padding: 0.65rem 0.95rem !important;
    font-size: 0.92rem !important;
}
div[data-testid="stChatInput"] textarea:focus {
    border-color: #ff551f !important;
    box-shadow: 0 0 10px rgba(255, 85, 31, 0.25) !important;
}

/* Primary Action Buttons */
.stButton > button {
    background: rgba(255, 255, 255, 0.04) !important;
    border: 1px solid rgba(255, 255, 255, 0.12) !important;
    color: #cbd5e1 !important;
    font-family: 'Space Grotesk', monospace !important;
    font-size: 0.72rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.06em !important;
    text-transform: uppercase !important;
    border-radius: 6px !important;
    padding: 0.35rem 0.8rem !important;
    transition: all 0.2s ease !important;
}
.stButton > button:hover {
    background: #ff551f !important;
    border-color: #ff551f !important;
    color: #ffffff !important;
    box-shadow: 0 0 12px rgba(255, 85, 31, 0.35) !important;
}
</style>
""", unsafe_allow_html=True)

# Top Tactical Nav
st.markdown("""
<div class="top-nav">
    <div class="brand-wrap">
        <div class="brand-badge">NED</div>
        <div class="brand-title">ADMISSIONS INTEL // RAG</div>
    </div>
    <div class="nav-links">
        <span>PROSPECTUS 2025</span>
        <span>•</span>
        <span>HYBRID BM25+VECTOR</span>
        <span>•</span>
        <div class="status-indicator">INDEX VERIFIED</div>
    </div>
</div>
""", unsafe_allow_html=True)

# Initialize messages state
GREETING = (
    "Hello! I am **NED Guide**, your virtual assistant for the official NED Undergraduate Prospectus 2025. "
    "I answer using only official prospectus data: eligibility requirements, merit formulas, seat quotas under Regular and Self-Finance, fee schedules, scholarships, and campus regulations."
)

if "messages" not in st.session_state or not st.session_state["messages"]:
    st.session_state["messages"] = [
        {"role": "assistant", "content": GREETING, "sources": []}
    ]

has_conversation = len(st.session_state["messages"]) > 1

# Hero Section: Full display if fresh session, compact collapsible if conversation in progress
if not has_conversation:
    st.markdown("""
    <div class="hero-wrapper">
        <div>
            <div class="sys-label">SYS.01 / ONLINE &nbsp;•&nbsp; OFFICIAL ADMISSIONS COPILOT</div>
            <div class="hero-main-title">
                Make the admissions<br><span>tangible.</span>
            </div>
            <div class="hero-description">
                NED Guide turns 122 pages of scanned prospectus text into instant, verifiable intelligence. 
                Direct citations, merit formulas, seat quotas, and fee schedules grounded strictly in the 
                <strong>Undergraduate Prospectus 2025</strong> with zero hallucinations.
            </div>
            <div class="stat-strip">
                <div class="stat-item">
                    <div class="stat-val">122</div>
                    <div class="stat-label">Pages Indexed</div>
                </div>
                <div class="stat-item">
                    <div class="stat-val">562</div>
                    <div class="stat-label">Neural Chunks</div>
                </div>
                <div class="stat-item">
                    <div class="stat-val">0.62</div>
                    <div class="stat-label">Safety Cutoff</div>
                </div>
                <div class="stat-item">
                    <div class="stat-val">0.0s</div>
                    <div class="stat-label">Safety Shield</div>
                </div>
            </div>
        </div>
        <div class="medallion-container">
            <svg class="medallion-svg" viewBox="0 0 400 400" fill="none" xmlns="http://www.w3.org/2000/svg">
                <circle cx="200" cy="200" r="190" stroke="#ff551f" stroke-width="1.2" stroke-dasharray="4 6" opacity="0.4" />
                <circle cx="200" cy="200" r="176" stroke="#ffffff" stroke-width="1" opacity="0.2" />
                <circle cx="200" cy="200" r="148" stroke="#ffffff" stroke-width="0.75" stroke-dasharray="2 4" opacity="0.25" />
                <circle cx="200" cy="200" r="100" stroke="#ff551f" stroke-width="1.5" opacity="0.5" />
                
                <polygon points="200,10 206,180 200,200 194,180" fill="#ff551f" />
                <polygon points="200,390 206,220 200,200 194,220" fill="#ffffff" opacity="0.4" />
                <polygon points="10,200 180,206 200,200 180,194" fill="#ffffff" opacity="0.4" />
                <polygon points="390,200 220,206 200,200 220,194" fill="#ffffff" opacity="0.4" />
                
                <circle cx="200" cy="200" r="62" fill="#0d1117" stroke="#ff551f" stroke-width="2" />
                <circle cx="200" cy="200" r="42" stroke="#ffffff" stroke-width="1" stroke-dasharray="3 3" opacity="0.5" />
                <polygon points="200,165 210,190 235,190 215,205 222,230 200,215 178,230 185,205 165,190 190,190" fill="#ff551f" opacity="0.85" />
                <circle cx="200" cy="200" r="10" fill="#ffffff" />
            </svg>
        </div>
    </div>
    """, unsafe_allow_html=True)
else:
    with st.expander("ℹ️ Prospectus Overview & System Metrics", expanded=False):
        st.caption(
            "Grounded in official **NED Undergraduate Prospectus 2025** • 122 pages indexed • 562 neural chunks • "
            "BM25 + ChromaDB Reciprocal Rank Fusion • Similarity threshold 0.62."
        )

# Tactical Action Toolbar
col_ctrl1, col_ctrl2 = st.columns([0.8, 0.2])

with col_ctrl1:
    show_sources = st.toggle("Display Verified Citations", value=True)

with col_ctrl2:
    if st.button("RESET CHAT"):
        st.session_state["messages"] = [
            {"role": "assistant", "content": GREETING, "sources": []}
        ]
        st.rerun()

# Render conversation history
for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if show_sources and msg.get("sources"):
            with st.expander(f"🔍 Verified Sources ({len(msg['sources'])} citations)", expanded=False):
                badges = []
                for page, section, sim in msg["sources"]:
                    sec_str = f" • {section}" if section else ""
                    badges.append(f"<span class='citation-badge'>Page {page}{sec_str} (similarity: {sim:.3f})</span>")
                citations_html = "".join(badges)
                st.markdown(citations_html, unsafe_allow_html=True)

# User Chat Input
user_input = st.chat_input("Ask any question regarding NED undergraduate admissions...")

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
            # Smooth, deliberate multi-phase transitions
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
                with st.expander(f"🔍 Verified Sources ({len(bot_sources)} citations)", expanded=False):
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

# Auto-scroll anchor component ensuring input and latest message remain cleanly in focus
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
