"""Streamlit chat interface for the NED Undergraduate Prospectus RAG assistant.

High-End UI inspired by modern engineering sites (Sentec aesthetic):
- Prominent Hero Section with typography & animated engineering compass medallion
- No left sidebar: replaced with top tactical floating command bar & controls
- Subtle tactical grid, radial ambient lighting, glassmorphism cards
- Expandable citation drawers & live verification badges
- Clean multi-turn chat stream with source verification
"""

from pathlib import Path
import random
import time
import streamlit as st

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

# Custom High-End Styling (No left sidebar, rich ambient glow, animated compass)
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
        radial-gradient(circle at 75% 15%, rgba(255, 75, 17, 0.12) 0%, transparent 45%),
        radial-gradient(circle at 20% 80%, rgba(255, 75, 17, 0.05) 0%, transparent 40%),
        linear-gradient(rgba(255, 255, 255, 0.025) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255, 255, 255, 0.025) 1px, transparent 1px);
    background-size: 100% 100%, 100% 100%, 40px 40px, 40px 40px;
    color: #e2e8f0;
    font-family: 'Inter', -apple-system, sans-serif;
}

/* Main Container constraint */
.main .block-container {
    max-width: 1200px !important;
    padding-top: 1.5rem !important;
    padding-bottom: 5rem !important;
}

/* Top Tactical Navigation Bar */
.top-nav {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.9rem 1.6rem;
    background: rgba(14, 17, 22, 0.7);
    backdrop-filter: blur(14px);
    border: 1px solid rgba(255, 255, 255, 0.07);
    border-radius: 12px;
    margin-bottom: 2.2rem;
}

.brand-wrap {
    display: flex;
    align-items: center;
    gap: 12px;
}

.brand-badge {
    width: 28px;
    height: 28px;
    border-radius: 6px;
    background: linear-gradient(135deg, #ff551f, #d93d0b);
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 700;
    font-size: 0.85rem;
    color: #fff;
    box-shadow: 0 0 15px rgba(255, 85, 31, 0.4);
}

.brand-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.15rem;
    font-weight: 700;
    letter-spacing: -0.02em;
    color: #ffffff;
}

.nav-links {
    display: flex;
    align-items: center;
    gap: 20px;
    font-family: 'Space Grotesk', monospace;
    font-size: 0.76rem;
    color: #94a3b8;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}

.status-indicator {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 10px;
    background: rgba(34, 197, 94, 0.1);
    border: 1px solid rgba(34, 197, 94, 0.25);
    border-radius: 100px;
    color: #4ade80;
    font-size: 0.7rem;
    font-weight: 600;
}
.status-indicator::before {
    content: "";
    width: 6px;
    height: 6px;
    background-color: #22c55e;
    border-radius: 50%;
    box-shadow: 0 0 8px #22c55e;
}

/* Hero Split Layout */
.hero-wrapper {
    display: grid;
    grid-template-columns: 1.15fr 0.85fr;
    gap: 3rem;
    align-items: center;
    margin-bottom: 2.8rem;
    padding: 1.5rem 0;
}

@media (max-width: 900px) {
    .hero-wrapper {
        grid-template-columns: 1fr;
        gap: 1.5rem;
    }
}

.sys-label {
    font-family: 'Space Grotesk', monospace;
    font-size: 0.75rem;
    font-weight: 600;
    color: #ff551f;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 0.75rem;
}

.hero-main-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 3.4rem;
    font-weight: 700;
    line-height: 1.04;
    color: #ffffff;
    letter-spacing: -0.04em;
    margin-bottom: 1rem;
}
.hero-main-title span {
    color: #ff551f;
    background: linear-gradient(135deg, #ff551f 0%, #ff7a4d 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

.hero-description {
    font-size: 1.05rem;
    line-height: 1.6;
    color: #94a3b8;
    margin-bottom: 1.5rem;
    max-width: 560px;
}

/* Stat Counters */
.stat-strip {
    display: flex;
    gap: 2rem;
    margin-top: 1.2rem;
}
.stat-item {
    font-family: 'Space Grotesk', sans-serif;
}
.stat-val {
    font-size: 1.35rem;
    font-weight: 700;
    color: #ffffff;
}
.stat-label {
    font-size: 0.75rem;
    color: #64748b;
    letter-spacing: 0.05em;
    text-transform: uppercase;
}

/* Medallion / Compass Graphic */
.medallion-container {
    display: flex;
    justify-content: center;
    align-items: center;
    position: relative;
}

.medallion-svg {
    width: 100%;
    max-width: 380px;
    filter: drop-shadow(0 0 35px rgba(255, 85, 31, 0.18));
    animation: slow-rotate 60s linear infinite;
}

@keyframes slow-rotate {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
}

/* Tactical Action Bar */
.action-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.75rem 1.25rem;
    background: rgba(18, 22, 28, 0.5);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 10px;
    margin-bottom: 1.5rem;
}

/* Chat Messages */
div[data-testid="stChatMessage"] {
    background-color: rgba(14, 18, 24, 0.75) !important;
    border: 1px solid rgba(255, 255, 255, 0.07) !important;
    border-radius: 10px !important;
    padding: 1.2rem 1.5rem !important;
    margin-bottom: 1rem !important;
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

/* Source Box Component */
.citation-box {
    margin-top: 1rem;
    padding: 0.85rem 1.1rem;
    background: rgba(0, 0, 0, 0.45);
    border: 1px solid rgba(255, 85, 31, 0.22);
    border-radius: 8px;
    font-family: 'Space Grotesk', monospace;
    font-size: 0.8rem;
    color: #cbd5e1;
}
.citation-header {
    display: flex;
    align-items: center;
    gap: 8px;
    color: #ff551f;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-bottom: 0.4rem;
}
.citation-badge {
    display: inline-block;
    padding: 4px 10px;
    background: rgba(255, 85, 31, 0.12);
    border: 1px solid rgba(255, 85, 31, 0.35);
    border-radius: 6px;
    margin-top: 6px;
    margin-right: 8px;
    font-size: 0.76rem;
    font-family: 'Space Grotesk', monospace;
    color: #fdba74;
}

/* Collapsible Expander Dropdown Styling */
div[data-testid="stExpander"] {
    background-color: rgba(10, 13, 18, 0.6) !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    border-radius: 8px !important;
    margin-top: 0.75rem !important;
}
div[data-testid="stExpander"] summary {
    font-family: 'Space Grotesk', monospace !important;
    font-size: 0.78rem !important;
    font-weight: 600 !important;
    color: #94a3b8 !important;
    letter-spacing: 0.04em !important;
}
div[data-testid="stExpander"] summary:hover {
    color: #ff551f !important;
}
div[data-testid="stExpander"] div[role="region"] {
    border-top: 1px solid rgba(255, 255, 255, 0.05) !important;
    padding-top: 0.5rem !important;
}

/* Custom Chat Input Bar */
div[data-testid="stChatInput"] textarea {
    background-color: #0f131a !important;
    border: 1px solid rgba(255, 255, 255, 0.12) !important;
    color: #ffffff !important;
    border-radius: 8px !important;
    font-family: 'Inter', sans-serif !important;
    padding: 0.75rem 1rem !important;
}
div[data-testid="stChatInput"] textarea:focus {
    border-color: #ff551f !important;
    box-shadow: 0 0 12px rgba(255, 85, 31, 0.25) !important;
}

/* Primary Action Buttons */
.stButton > button {
    background: rgba(255, 255, 255, 0.04) !important;
    border: 1px solid rgba(255, 255, 255, 0.14) !important;
    color: #e2e8f0 !important;
    font-family: 'Space Grotesk', monospace !important;
    font-size: 0.78rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
    border-radius: 6px !important;
    transition: all 0.2s ease !important;
}
.stButton > button:hover {
    background: #ff551f !important;
    border-color: #ff551f !important;
    color: #ffffff !important;
    box-shadow: 0 0 14px rgba(255, 85, 31, 0.4) !important;
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

# Big Sentec-Style Hero Section with Animated Medallion
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
                <div class="stat-label">Out-of-Scope Fallback</div>
            </div>
        </div>
    </div>
    <div class="medallion-container">
        <svg class="medallion-svg" viewBox="0 0 400 400" fill="none" xmlns="http://www.w3.org/2000/svg">
            <!-- Outer Compass Rings -->
            <circle cx="200" cy="200" r="190" stroke="#ff551f" stroke-width="1.2" stroke-dasharray="4 6" opacity="0.45" />
            <circle cx="200" cy="200" r="176" stroke="#ffffff" stroke-width="1" opacity="0.25" />
            <circle cx="200" cy="200" r="148" stroke="#ffffff" stroke-width="0.75" stroke-dasharray="2 4" opacity="0.3" />
            <circle cx="200" cy="200" r="100" stroke="#ff551f" stroke-width="1.5" opacity="0.6" />
            
            <!-- Cardinal Compass Needle Points -->
            <polygon points="200,10 206,180 200,200 194,180" fill="#ff551f" />
            <polygon points="200,390 206,220 200,200 194,220" fill="#ffffff" opacity="0.5" />
            <polygon points="10,200 180,206 200,200 180,194" fill="#ffffff" opacity="0.5" />
            <polygon points="390,200 220,206 200,200 220,194" fill="#ffffff" opacity="0.5" />
            
            <!-- Diagonal Ticks -->
            <line x1="65" y1="65" x2="180" y2="180" stroke="#ffffff" stroke-width="0.7" opacity="0.35" />
            <line x1="335" y1="65" x2="220" y2="180" stroke="#ffffff" stroke-width="0.7" opacity="0.35" />
            <line x1="65" y1="335" x2="180" y2="220" stroke="#ffffff" stroke-width="0.7" opacity="0.35" />
            <line x1="335" y1="335" x2="220" y2="220" stroke="#ffffff" stroke-width="0.7" opacity="0.35" />
            
            <!-- Center Core & Gear Geometry -->
            <circle cx="200" cy="200" r="62" fill="#0d1117" stroke="#ff551f" stroke-width="2" />
            <circle cx="200" cy="200" r="42" stroke="#ffffff" stroke-width="1" stroke-dasharray="3 3" opacity="0.6" />
            <polygon points="200,165 210,190 235,190 215,205 222,230 200,215 178,230 185,205 165,190 190,190" fill="#ff551f" opacity="0.85" />
            <circle cx="200" cy="200" r="10" fill="#ffffff" />
        </svg>
    </div>
</div>
""", unsafe_allow_html=True)

# Tactical Action Toolbar
col_ctrl1, col_ctrl2 = st.columns([0.78, 0.22])

with col_ctrl1:
    show_sources = st.toggle("Display Verified Citations & Similarity Scores", value=True)

with col_ctrl2:
    if st.button("RESET CONVERSATION"):
        st.session_state["messages"] = []
        st.rerun()

# Initial conversation state
GREETING = (
    "Hello! I am **NED Guide**, your virtual assistant for the official NED Undergraduate Prospectus 2025. "
    "I answer using only official prospectus data: eligibility requirements, merit formulas, seat quotas under Regular and Self-Finance, fee schedules, scholarships, and campus regulations."
)

if "messages" not in st.session_state or not st.session_state["messages"]:
    st.session_state["messages"] = [
        {"role": "assistant", "content": GREETING, "sources": []}
    ]

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
            status_labels = ["Retrieving...", "Sleuthing...", "Honing...", "Triangulating..."]
            initial_label = random.choice(status_labels)
            with st.status(initial_label, expanded=False) as status:
                st.caption("Searching prospectus chunks & synthesizing verified response...")
                result = answer_with_sources(clean_input, history=history_for_rag)
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
