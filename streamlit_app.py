"""
Bullet Memory — Streamlit Cloud Entry Point
============================================
Connects to a running FastAPI backend (configured via st.secrets or env var).
Falls back to demo mode automatically when no backend is reachable.

Deploy to Streamlit Cloud:
  1. Push this repo to GitHub
  2. Go to share.streamlit.io → New app → point at this file
  3. In App Settings → Secrets, add:
       API_BASE_URL = "https://your-backend.railway.app"
  4. Done. Without a backend, recruiter demo mode activates automatically.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone

import httpx
import streamlit as st

# ── Config ────────────────────────────────────────────────────────────────────

def _get_api_url() -> str:
    """Pull the backend URL from Streamlit secrets or env, fallback to localhost."""
    try:
        return st.secrets["API_BASE_URL"].rstrip("/")
    except Exception:
        import os
        return os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")

API_BASE_URL = _get_api_url()
DEMO_USER_ID = "demo-user"
REQUEST_TIMEOUT = 12.0


# ── Demo Data (shown when backend is unreachable) ─────────────────────────────

DEMO_MEMORIES = [
    {
        "id": "mem-001",
        "category": "PREFERENCE",
        "content": "User prefers Python over JavaScript for backend services and values clean async code.",
        "importance": 0.91,
        "confidence": 0.95,
        "source_type": "chat",
        "tags": ["python", "backend", "preferences"],
        "access_count": 14,
        "created_at": "2024-11-02T10:22:00Z",
    },
    {
        "id": "mem-002",
        "category": "SKILL",
        "content": "User is proficient with FastAPI, SQLAlchemy async, and Pydantic v2 for building production APIs.",
        "importance": 0.88,
        "confidence": 0.92,
        "source_type": "agent_event",
        "tags": ["fastapi", "sqlalchemy", "pydantic", "skills"],
        "access_count": 9,
        "created_at": "2024-11-03T14:05:00Z",
    },
    {
        "id": "mem-003",
        "category": "GOAL",
        "content": "User is building Bullet Memory as a portfolio project to demonstrate LLM engineering skills to recruiters.",
        "importance": 0.97,
        "confidence": 0.99,
        "source_type": "manual",
        "tags": ["career", "portfolio", "goals"],
        "access_count": 22,
        "created_at": "2024-11-01T08:00:00Z",
    },
    {
        "id": "mem-004",
        "category": "FACT",
        "content": "User works best in the evening and prefers async/non-blocking architectures for all I/O-bound workloads.",
        "importance": 0.74,
        "confidence": 0.85,
        "source_type": "chat",
        "tags": ["productivity", "architecture"],
        "access_count": 5,
        "created_at": "2024-11-04T20:11:00Z",
    },
    {
        "id": "mem-005",
        "category": "TOOL_RESULT",
        "content": "ChromaDB vector store initialised with 768-dim nomic-embed-text embeddings. Collection 'bullet_memory' contains 47 vectors.",
        "importance": 0.65,
        "confidence": 0.99,
        "source_type": "agent_event",
        "tags": ["chromadb", "embeddings", "system"],
        "access_count": 3,
        "created_at": "2024-11-05T09:30:00Z",
    },
    {
        "id": "mem-006",
        "category": "INSTRUCTION",
        "content": "When user asks about LLM memory, always reference the 'deduplicate_or_create' pipeline that prevents redundant memory storage via cosine similarity.",
        "importance": 0.82,
        "confidence": 0.90,
        "source_type": "manual",
        "tags": ["instructions", "memory", "architecture"],
        "access_count": 7,
        "created_at": "2024-11-06T11:45:00Z",
    },
]

DEMO_CHAT_RESPONSES = {
    "default": (
        "Based on your memory profile, I can see you're building **Bullet Memory** as a portfolio project. "
        "You have strong skills in **FastAPI + async Python**, and you prefer clean, production-oriented code. "
        "\n\n*[DEMO MODE — connect a live backend to enable real LLM responses]*"
    ),
    "what": (
        "**Bullet Memory** is a semantic memory engine for LLM agents. It extracts, deduplicates, "
        "and persists durable facts from conversations — giving your agents persistent, cross-session memory.\n\n"
        "Key features:\n"
        "- 🧠 Automatic extraction via LLM\n"
        "- 🔍 Semantic search with ChromaDB\n"
        "- ⚡ Async FastAPI backend\n"
        "- 📦 Fine-tuning dataset export\n\n"
        "*[DEMO MODE]*"
    ),
    "skill": (
        "From your memory vault, I can see you're proficient in:\n"
        "- **FastAPI** + **Uvicorn** for async APIs\n"
        "- **SQLAlchemy async** + **aiosqlite**\n"
        "- **ChromaDB** for vector storage\n"
        "- **Pydantic v2** for schema validation\n"
        "- **Structlog** for structured logging\n\n"
        "*[DEMO MODE — retrieved 2 memories]*"
    ),
}


# ── Backend helpers ───────────────────────────────────────────────────────────

def _check_backend() -> bool:
    try:
        r = httpx.get(f"{API_BASE_URL}/health", timeout=3.0)
        return r.status_code == 200
    except Exception:
        return False


def _api_get(path: str, **params) -> dict | list | None:
    try:
        r = httpx.get(f"{API_BASE_URL}{path}", params=params, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def _api_post(path: str, payload: dict) -> dict | None:
    try:
        r = httpx.post(f"{API_BASE_URL}{path}", json=payload, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


# ── Page setup ────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="BULLET MEMORY /// ENGINE",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Terminal CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;600;700;800&display=swap');

    /* ── Global reset ── */
    html, body, [class*="css"], .stApp {
        font-family: 'JetBrains Mono', monospace !important;
        background-color: #000000 !important;
        color: #e2e8f0 !important;
    }

    /* ── Kill Streamlit chrome ── */
    header[data-testid="stHeader"]         { display: none !important; }
    .stDeployButton                        { display: none !important; }
    footer                                 { display: none !important; }
    #MainMenu                              { display: none !important; }
    [data-testid="stToolbar"]              { display: none !important; }

    /* ── Sidebar ── */
    [data-testid="stSidebar"] {
        background: #050505 !important;
        border-right: 1px solid #00f0ff !important;
    }
    [data-testid="stSidebar"] * {
        font-family: 'JetBrains Mono', monospace !important;
    }
    [data-testid="stSidebarContent"] {
        padding-top: 1rem;
    }

    /* ── Main container ── */
    .main .block-container {
        background: #000000 !important;
        padding-top: 1.5rem !important;
        max-width: 1400px;
    }

    /* ── Sidebar logo ── */
    .sidebar-logo {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 0 0 16px 0;
        border-bottom: 1px solid rgba(0,240,255,0.3);
        margin-bottom: 20px;
    }
    .pulse-dot {
        width: 10px; height: 10px;
        background: #00f0ff;
        box-shadow: 0 0 12px rgba(0,240,255,0.8);
        animation: pulsate 2s ease-in-out infinite;
        flex-shrink: 0;
    }
    .logo-text {
        font-size: 13px;
        font-weight: 800;
        color: #00f0ff;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        line-height: 1.2;
    }
    .logo-sub {
        font-size: 10px;
        color: #64748b;
        letter-spacing: 0.08em;
        font-weight: 400;
    }

    /* ── Nav label ── */
    .nav-label {
        font-size: 10px;
        font-weight: 700;
        letter-spacing: 0.2em;
        color: #00f0ff;
        text-transform: uppercase;
        margin-bottom: 8px;
        padding-bottom: 4px;
        border-bottom: 1px solid rgba(0,240,255,0.15);
    }

    /* ── Status badges ── */
    .status-live {
        display: flex; align-items: center; gap: 8px;
        background: rgba(57,255,20,0.06);
        border: 1px solid rgba(57,255,20,0.4);
        padding: 8px 12px;
        font-size: 11px;
        font-weight: 600;
        color: #39ff14;
        letter-spacing: 0.08em;
        margin: 8px 0;
    }
    .status-demo {
        display: flex; align-items: center; gap: 8px;
        background: rgba(255,234,0,0.06);
        border: 1px solid rgba(255,234,0,0.4);
        padding: 8px 12px;
        font-size: 11px;
        font-weight: 600;
        color: #ffea00;
        letter-spacing: 0.08em;
        margin: 8px 0;
    }
    .status-dot {
        width: 7px; height: 7px;
        border-radius: 50%;
        flex-shrink: 0;
    }
    .dot-live { background: #39ff14; box-shadow: 0 0 8px rgba(57,255,20,0.8); }
    .dot-demo { background: #ffea00; box-shadow: 0 0 8px rgba(255,234,0,0.8); }

    /* ── Page header ── */
    .page-header {
        display: flex;
        align-items: flex-start;
        gap: 16px;
        border: 1px solid #00f0ff;
        padding: 16px 24px;
        margin-bottom: 24px;
        background: #050505;
        position: relative;
    }
    .page-header::before {
        content: '';
        position: absolute;
        top: -1px; left: 40px; right: 40px;
        height: 1px;
        background: linear-gradient(90deg, transparent, #00f0ff, transparent);
        box-shadow: 0 0 12px rgba(0,240,255,0.5);
    }
    .page-num {
        font-size: 10px;
        font-weight: 700;
        color: #00f0ff;
        letter-spacing: 0.2em;
        padding-top: 2px;
        opacity: 0.6;
    }
    .page-title {
        font-size: 18px;
        font-weight: 800;
        color: #00f0ff;
        letter-spacing: 0.15em;
        text-transform: uppercase;
        text-shadow: 0 0 20px rgba(0,240,255,0.4);
        line-height: 1.2;
    }
    .page-sub {
        font-size: 11px;
        color: #64748b;
        letter-spacing: 0.08em;
        margin-top: 2px;
        font-weight: 400;
    }

    /* ── Memory cards ── */
    .mem-card {
        background: #050505;
        border: 1px solid #1e293b;
        border-left: 3px solid #00f0ff;
        padding: 14px 18px;
        margin-bottom: 10px;
        transition: border-color 0.15s, box-shadow 0.15s;
        position: relative;
    }
    .mem-card:hover {
        border-color: #00f0ff;
        box-shadow: 0 0 16px rgba(0,240,255,0.08), inset 0 0 20px rgba(0,240,255,0.02);
    }

    /* Category pills */
    .mem-category {
        font-size: 10px;
        font-weight: 700;
        letter-spacing: 0.15em;
        text-transform: uppercase;
        padding: 2px 8px;
        display: inline-block;
        margin-bottom: 8px;
        border: 1px solid;
    }
    .cat-PREFERENCE  { color: #00f0ff; border-color: rgba(0,240,255,0.4); background: rgba(0,240,255,0.06); }
    .cat-SKILL       { color: #39ff14; border-color: rgba(57,255,20,0.4); background: rgba(57,255,20,0.05); }
    .cat-GOAL        { color: #ffea00; border-color: rgba(255,234,0,0.4); background: rgba(255,234,0,0.05); }
    .cat-FACT        { color: #a78bfa; border-color: rgba(167,139,250,0.4); background: rgba(167,139,250,0.05); }
    .cat-TOOL_RESULT { color: #fb923c; border-color: rgba(251,146,60,0.4); background: rgba(251,146,60,0.05); }
    .cat-INSTRUCTION { color: #f472b6; border-color: rgba(244,114,182,0.4); background: rgba(244,114,182,0.05); }
    .cat-default     { color: #64748b; border-color: rgba(100,116,139,0.4); background: rgba(100,116,139,0.05); }

    .mem-content {
        color: #cbd5e1;
        font-size: 13px;
        line-height: 1.65;
        margin: 6px 0 10px 0;
        font-weight: 400;
    }
    .mem-meta {
        color: #475569;
        font-size: 11px;
        display: flex;
        gap: 18px;
        flex-wrap: wrap;
        align-items: center;
    }
    .mem-meta b { color: #00f0ff; }

    /* Importance bar */
    .imp-bar {
        font-size: 10px;
        letter-spacing: -1px;
        color: #00f0ff;
    }

    /* Tags */
    .tag {
        display: inline-block;
        background: transparent;
        color: #00f0ff;
        border: 1px solid rgba(0,240,255,0.3);
        padding: 1px 7px;
        font-size: 10px;
        letter-spacing: 0.06em;
        margin: 2px 3px 2px 0;
        font-family: 'JetBrains Mono', monospace;
    }

    /* ── Stat cards ── */
    .stat-card {
        background: #050505;
        border: 1px solid rgba(0,240,255,0.25);
        padding: 20px 16px;
        text-align: center;
        position: relative;
        overflow: hidden;
    }
    .stat-card::after {
        content: '';
        position: absolute;
        bottom: 0; left: 0; right: 0;
        height: 1px;
        background: linear-gradient(90deg, transparent, #00f0ff, transparent);
        opacity: 0.4;
    }
    .stat-num {
        font-size: 36px;
        font-weight: 800;
        color: #00f0ff;
        text-shadow: 0 0 20px rgba(0,240,255,0.5);
        line-height: 1;
    }
    .stat-lbl {
        font-size: 10px;
        color: #475569;
        text-transform: uppercase;
        letter-spacing: 0.15em;
        margin-top: 8px;
        font-weight: 600;
    }

    /* ── Banners ── */
    .demo-banner {
        background: rgba(255,234,0,0.05);
        border: 1px solid rgba(255,234,0,0.35);
        padding: 10px 14px;
        color: #ffea00;
        font-size: 11px;
        letter-spacing: 0.06em;
        margin-bottom: 16px;
    }
    .live-banner {
        background: rgba(57,255,20,0.05);
        border: 1px solid rgba(57,255,20,0.35);
        padding: 10px 14px;
        color: #39ff14;
        font-size: 11px;
        letter-spacing: 0.06em;
        margin-bottom: 16px;
    }

    /* ── Streamlit widget overrides ── */
    .stButton > button {
        background: transparent !important;
        border: 1px solid #00f0ff !important;
        color: #00f0ff !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-weight: 700 !important;
        font-size: 12px !important;
        letter-spacing: 0.1em !important;
        border-radius: 0 !important;
        padding: 8px 20px !important;
        text-transform: uppercase !important;
        transition: all 0.15s !important;
    }
    .stButton > button:hover {
        background: #00f0ff !important;
        color: #000000 !important;
        box-shadow: 0 0 16px rgba(0,240,255,0.4) !important;
    }

    /* Form submit button */
    .stFormSubmitButton > button {
        background: rgba(0,240,255,0.08) !important;
        border: 1px solid #00f0ff !important;
        color: #00f0ff !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-weight: 700 !important;
        font-size: 12px !important;
        letter-spacing: 0.1em !important;
        border-radius: 0 !important;
        text-transform: uppercase !important;
        width: 100% !important;
    }
    .stFormSubmitButton > button:hover {
        background: #00f0ff !important;
        color: #000000 !important;
        box-shadow: 0 0 20px rgba(0,240,255,0.4) !important;
    }

    /* Text inputs, text areas, selects */
    .stTextInput input, .stTextArea textarea, .stSelectbox select,
    div[data-baseweb="input"] input, div[data-baseweb="textarea"] textarea {
        background: #050505 !important;
        border: 1px solid #1e293b !important;
        border-radius: 0 !important;
        color: #e2e8f0 !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 13px !important;
    }
    .stTextInput input:focus, .stTextArea textarea:focus {
        border-color: #00f0ff !important;
        box-shadow: 0 0 8px rgba(0,240,255,0.15) !important;
    }

    /* Selectbox */
    div[data-baseweb="select"] > div {
        background: #050505 !important;
        border: 1px solid #1e293b !important;
        border-radius: 0 !important;
        font-family: 'JetBrains Mono', monospace !important;
        color: #e2e8f0 !important;
    }
    div[data-baseweb="select"] > div:focus-within {
        border-color: #00f0ff !important;
    }

    /* Slider */
    .stSlider [data-baseweb="slider"] div[role="slider"] {
        background: #00f0ff !important;
        box-shadow: 0 0 8px rgba(0,240,255,0.5) !important;
    }
    .stSlider div[data-testid="stTickBarMin"],
    .stSlider div[data-testid="stTickBarMax"] {
        color: #475569 !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 11px !important;
    }

    /* Radio buttons */
    .stRadio label {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 12px !important;
        color: #94a3b8 !important;
        letter-spacing: 0.05em !important;
    }
    .stRadio [data-baseweb="radio"] span:first-child {
        border-color: #1e293b !important;
    }
    .stRadio [aria-checked="true"] span:first-child {
        border-color: #00f0ff !important;
        background: #00f0ff !important;
    }

    /* Chat messages */
    [data-testid="stChatMessage"] {
        background: #050505 !important;
        border: 1px solid #1e293b !important;
        border-radius: 0 !important;
        font-family: 'JetBrains Mono', monospace !important;
    }
    [data-testid="stChatMessage"][data-testid*="user"] {
        border-left: 3px solid #00f0ff !important;
    }

    /* Chat input */
    [data-testid="stChatInput"] textarea {
        background: #050505 !important;
        border: 1px solid rgba(0,240,255,0.3) !important;
        border-radius: 0 !important;
        color: #e2e8f0 !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 13px !important;
    }
    [data-testid="stChatInput"] textarea:focus {
        border-color: #00f0ff !important;
        box-shadow: 0 0 12px rgba(0,240,255,0.15) !important;
    }
    [data-testid="stChatInput"] button {
        color: #00f0ff !important;
    }

    /* Bar chart */
    .stVegaLiteChart canvas { background: #000000 !important; }

    /* Captions and labels */
    .stCaption, [data-testid="stCaptionContainer"] {
        font-family: 'JetBrains Mono', monospace !important;
        color: #475569 !important;
        font-size: 11px !important;
    }

    /* Code blocks */
    code, pre {
        background: #050505 !important;
        border: 1px solid #1e293b !important;
        border-radius: 0 !important;
        color: #00f0ff !important;
        font-family: 'JetBrains Mono', monospace !important;
    }

    /* Divider */
    hr { border-color: #1e293b !important; }

    /* Scrollbar */
    ::-webkit-scrollbar { width: 5px; height: 5px; }
    ::-webkit-scrollbar-track { background: #000000; }
    ::-webkit-scrollbar-thumb { background: #1e293b; }
    ::-webkit-scrollbar-thumb:hover { background: #00f0ff; }

    /* Spinner */
    .stSpinner > div { border-top-color: #00f0ff !important; }

    /* Success / warning / error */
    .stSuccess { background: rgba(57,255,20,0.06) !important; border: 1px solid rgba(57,255,20,0.3) !important; border-radius: 0 !important; }
    .stWarning { background: rgba(255,234,0,0.06) !important; border: 1px solid rgba(255,234,0,0.3) !important; border-radius: 0 !important; }
    .stError   { background: rgba(255,51,51,0.06) !important; border: 1px solid rgba(255,51,51,0.3) !important; border-radius: 0 !important; }
    .stInfo    { background: rgba(0,240,255,0.06) !important; border: 1px solid rgba(0,240,255,0.3) !important; border-radius: 0 !important; }

    @keyframes pulsate {
        0%, 100% { opacity: 1; box-shadow: 0 0 12px rgba(0,240,255,0.8); }
        50%       { opacity: 0.4; box-shadow: 0 0 4px rgba(0,240,255,0.3); }
    }
</style>
""", unsafe_allow_html=True)


# ── Session state ─────────────────────────────────────────────────────────────

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": (
                "[SYSTEM] Bullet Memory Engine v1.0 initialized.\n\n"
                "Persistent memory vault online. Ask me anything about your stored knowledge, "
                "preferences, or goals — or just chat and I'll extract new memories automatically."
            ),
        }
    ]

if "backend_ok" not in st.session_state:
    st.session_state.backend_ok = _check_backend()


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("""
    <div class='sidebar-logo'>
        <div class='pulse-dot'></div>
        <div>
            <div class='logo-text'>BULLET MEMORY</div>
            <div class='logo-sub'>/// ENGINE v1.0</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div class='nav-label'>Navigation</div>", unsafe_allow_html=True)

    page = st.radio(
        "Go to",
        ["01 // AGENT TERMINAL", "02 // INGEST", "03 // MEMORY VAULT", "04 // STATS"],
        label_visibility="collapsed",
    )

    st.markdown("---")
    st.markdown("<div class='nav-label'>System Status</div>", unsafe_allow_html=True)

    if st.session_state.backend_ok:
        st.markdown(
            "<div class='status-live'><div class='status-dot dot-live'></div>BACKEND CONNECTED</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            "<div class='status-demo'><div class='status-dot dot-demo'></div>DEMO MODE</div>",
            unsafe_allow_html=True,
        )

    st.caption(f"API → `{API_BASE_URL}`")

    if st.button("[ PING BACKEND ]"):
        with st.spinner("Pinging..."):
            st.session_state.backend_ok = _check_backend()
        st.rerun()

    st.markdown("---")
    st.markdown("<div class='nav-label'>About</div>", unsafe_allow_html=True)
    st.markdown("""
<span style='color:#64748b;font-size:11px;line-height:1.8;'>
Semantic memory engine for LLM agents.<br><br>
⚡ FastAPI async backend<br>
🔍 ChromaDB vector store<br>
🤖 LLM-powered extraction<br>
📦 Fine-tune export (JSONL)
</span>
""", unsafe_allow_html=True)
    st.markdown(
        "<a href='https://github.com/Sudhanwa-git/Bullet-Memory' style='color:#00f0ff;font-size:11px;'>[ GITHUB → ]</a>",
        unsafe_allow_html=True,
    )


# ── Helper: render a memory card ─────────────────────────────────────────────

def render_memory_card(mem: dict) -> None:
    cat = mem.get("category", "FACT")
    known = ("PREFERENCE", "SKILL", "GOAL", "FACT", "TOOL_RESULT", "INSTRUCTION")
    cat_class = f"cat-{cat}" if cat in known else "cat-default"
    tags_html = "".join(f"<span class='tag'>{t}</span>" for t in (mem.get("tags") or []))
    importance = mem.get("importance", 0)
    filled = int(importance * 10)
    imp_bar = "█" * filled + "░" * (10 - filled)

    st.markdown(
        f"""
        <div class='mem-card'>
            <span class='mem-category {cat_class}'>{cat}</span>
            <div class='mem-content'>{mem.get("content", "")}</div>
            <div style='margin-bottom:10px;'>{tags_html}</div>
            <div class='mem-meta'>
                <span>IMP <b>{importance:.2f}</b> <span class='imp-bar'>{imp_bar}</span></span>
                <span>CONF <b>{mem.get('confidence', 0):.2f}</b></span>
                <span>HITS <b>{mem.get('access_count', 0)}</b></span>
                <span>SRC <b>{mem.get('source_type', '—')}</b></span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: Agent Terminal
# ═══════════════════════════════════════════════════════════════════════════════

if page == "01 // AGENT TERMINAL":
    st.markdown("""
    <div class='page-header'>
        <div class='page-num'>01</div>
        <div>
            <div class='page-title'>AGENT TERMINAL</div>
            <div class='page-sub'>Chat with memory-augmented agent</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if not st.session_state.backend_ok:
        st.markdown(
            "<div class='demo-banner'>[ DEMO MODE ] — Responses are pre-scripted. Connect a backend for real LLM responses.</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            "<div class='live-banner'>[ LIVE ] — Memory-augmented responses active.</div>",
            unsafe_allow_html=True,
        )

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Transmit data to agent..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Processing..."):
                if st.session_state.backend_ok:
                    t0 = time.time()
                    data = _api_post("/chat", {"user_id": DEMO_USER_ID, "message": prompt})
                    latency = (time.time() - t0) * 1000

                    if data:
                        answer = data.get("response", "No response.")
                        memories_used = data.get("memories_retrieved", 0)
                        st.markdown(answer)
                        if memories_used:
                            st.caption(f"[ {memories_used} memories retrieved · {latency:.0f}ms ]")
                        st.session_state.messages.append({"role": "assistant", "content": answer})
                    else:
                        err = "[ ERROR ] Backend unreachable. Switching to demo mode."
                        st.markdown(err)
                        st.session_state.messages.append({"role": "assistant", "content": err})
                        st.session_state.backend_ok = False
                else:
                    pl = prompt.lower()
                    if any(w in pl for w in ("what", "explain", "how", "bullet")):
                        answer = DEMO_CHAT_RESPONSES["what"]
                    elif any(w in pl for w in ("skill", "know", "proficient", "experience")):
                        answer = DEMO_CHAT_RESPONSES["skill"]
                    else:
                        answer = DEMO_CHAT_RESPONSES["default"]
                    time.sleep(0.6)
                    st.markdown(answer)
                    st.session_state.messages.append({"role": "assistant", "content": answer})

    if len(st.session_state.messages) > 1:
        if st.button("[ CLEAR CONVERSATION ]"):
            st.session_state.messages = [st.session_state.messages[0]]
            st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: Ingest
# ═══════════════════════════════════════════════════════════════════════════════

elif page == "02 // INGEST":
    st.markdown("""
    <div class='page-header'>
        <div class='page-num'>02</div>
        <div>
            <div class='page-title'>INGEST PANEL</div>
            <div class='page-sub'>Extract and store memories from raw text</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if not st.session_state.backend_ok:
        st.markdown(
            "<div class='demo-banner'>[ DEMO MODE ] — Ingestion disabled. Connect a backend to extract real memories.</div>",
            unsafe_allow_html=True,
        )

    with st.form("ingest_form"):
        raw_text = st.text_area(
            "RAW TEXT",
            height=200,
            placeholder="Paste any text — conversation logs, documents, notes, tool outputs...",
        )

        col1, col2 = st.columns(2)
        with col1:
            source_type = st.selectbox(
                "SOURCE TYPE",
                ["api_ingest", "chat", "agent_event", "manual"],
            )
            tags_input = st.text_input("TAGS (comma-separated)", placeholder="python, goals, career")
        with col2:
            agent_id = st.text_input("AGENT ID (optional)", placeholder="my-agent-v1")
            session_id = st.text_input("SESSION ID (optional)", placeholder="session-001")

        submitted = st.form_submit_button("[ EXECUTE INGESTION ]", use_container_width=True)

        if submitted:
            if not raw_text.strip():
                st.warning("No input detected. Provide text to ingest.")
            elif not st.session_state.backend_ok:
                st.info("[ DEMO ] In a live deployment, this would extract and store memories using an LLM.")
            else:
                with st.spinner("Extracting memories..."):
                    tags = [t.strip() for t in tags_input.split(",") if t.strip()] if tags_input else []
                    payload = {
                        "user_id": DEMO_USER_ID,
                        "text": raw_text,
                        "source_type": source_type,
                        "agent_id": agent_id or None,
                        "session_id": session_id or None,
                        "tags": tags,
                    }
                    res = _api_post("/ingest/raw", payload)
                    if res:
                        n = res.get("memories_stored", 0)
                        st.success(f"[ OK ] Extracted and stored {n} memories.")
                    else:
                        st.error("[ FAIL ] Ingest failed — check backend connection.")

    st.markdown("---")
    st.markdown("<div class='nav-label' style='margin-top:16px;'>How Extraction Works</div>", unsafe_allow_html=True)
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.markdown("""<div style='border:1px solid #1e293b;padding:14px;background:#050505;'>
<span style='color:#00f0ff;font-size:10px;font-weight:700;letter-spacing:.15em;'>01 // LLM EXTRACTION</span><br><br>
<span style='color:#94a3b8;font-size:12px;line-height:1.7;'>Text is passed to an LLM which identifies durable facts, skills, preferences, and goals.</span>
</div>""", unsafe_allow_html=True)
    with col_b:
        st.markdown("""<div style='border:1px solid #1e293b;padding:14px;background:#050505;'>
<span style='color:#00f0ff;font-size:10px;font-weight:700;letter-spacing:.15em;'>02 // IMPORTANCE SCORING</span><br><br>
<span style='color:#94a3b8;font-size:12px;line-height:1.7;'>Each candidate memory is scored 0–1. Low-importance items are filtered out.</span>
</div>""", unsafe_allow_html=True)
    with col_c:
        st.markdown("""<div style='border:1px solid #1e293b;padding:14px;background:#050505;'>
<span style='color:#00f0ff;font-size:10px;font-weight:700;letter-spacing:.15em;'>03 // DEDUPLICATION</span><br><br>
<span style='color:#94a3b8;font-size:12px;line-height:1.7;'>New memories are embedded and compared against the vector store. Near-duplicates are merged.</span>
</div>""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: Memory Vault
# ═══════════════════════════════════════════════════════════════════════════════

elif page == "03 // MEMORY VAULT":
    st.markdown("""
    <div class='page-header'>
        <div class='page-num'>03</div>
        <div>
            <div class='page-title'>MEMORY VAULT</div>
            <div class='page-sub'>Browse all persisted memories</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        cat_filter = st.selectbox("CATEGORY", ["All", "PREFERENCE", "SKILL", "GOAL", "FACT", "TOOL_RESULT", "INSTRUCTION"])
    with col2:
        src_filter = st.selectbox("SOURCE TYPE", ["All", "chat", "agent_event", "manual", "api_ingest"])
    with col3:
        min_imp = st.slider("MIN IMP", 0.0, 1.0, 0.0, 0.05)

    c1, c2 = st.columns([1, 5])
    with c1:
        if st.button("[ SYNC ]"):
            st.rerun()

    st.markdown("---")

    if st.session_state.backend_ok:
        params = {"user_id": DEMO_USER_ID}
        if cat_filter != "All":
            params["category"] = cat_filter
        if src_filter != "All":
            params["source_type"] = src_filter
        if min_imp > 0:
            params["min_importance"] = min_imp

        data = _api_get(f"/memories/{DEMO_USER_ID}", **params)
        if data:
            memories = data.get("memories", [])
        else:
            st.warning("[ WARN ] Could not load memories from backend.")
            memories = []
    else:
        memories = DEMO_MEMORIES
        if cat_filter != "All":
            memories = [m for m in memories if m["category"] == cat_filter]
        if src_filter != "All":
            memories = [m for m in memories if m["source_type"] == src_filter]
        memories = [m for m in memories if m["importance"] >= min_imp]
        st.markdown(
            "<div class='demo-banner'>[ DEMO ] Showing demo memories. Connect a backend to see real persisted data.</div>",
            unsafe_allow_html=True,
        )

    if not memories:
        st.markdown("<div style='color:#475569;font-size:12px;padding:20px 0;'>// No memories match current filters.</div>", unsafe_allow_html=True)
    else:
        st.caption(f"// {len(memories)} memor{'y' if len(memories)==1 else 'ies'} loaded")
        for mem in sorted(memories, key=lambda m: m.get("importance", 0), reverse=True):
            render_memory_card(mem)


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: Stats
# ═══════════════════════════════════════════════════════════════════════════════

elif page == "04 // STATS":
    st.markdown("""
    <div class='page-header'>
        <div class='page-num'>04</div>
        <div>
            <div class='page-title'>SYSTEM STATS</div>
            <div class='page-sub'>Memory engine overview</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if not st.session_state.backend_ok:
        st.markdown(
            "<div class='demo-banner'>[ DEMO MODE ] — Showing example stats.</div>",
            unsafe_allow_html=True,
        )
        memories = DEMO_MEMORIES
    else:
        data = _api_get(f"/memories/{DEMO_USER_ID}")
        memories = data.get("memories", []) if data else []

    total = len(memories)
    avg_imp = sum(m.get("importance", 0) for m in memories) / total if total else 0
    total_accesses = sum(m.get("access_count", 0) for m in memories)
    categories: dict[str, int] = {}
    for m in memories:
        c = m.get("category", "UNKNOWN")
        categories[c] = categories.get(c, 0) + 1

    cols = st.columns(4)
    stats = [
        (str(total), "TOTAL MEMORIES"),
        (f"{avg_imp:.2f}", "AVG IMPORTANCE"),
        (str(total_accesses), "TOTAL ACCESSES"),
        (str(len(categories)), "CATEGORIES"),
    ]
    for col, (num, lbl) in zip(cols, stats):
        with col:
            st.markdown(
                f"<div class='stat-card'><div class='stat-num'>{num}</div><div class='stat-lbl'>{lbl}</div></div>",
                unsafe_allow_html=True,
            )

    st.markdown("---")

    if categories:
        st.markdown("<div class='nav-label' style='margin-top:8px;'>Memory by Category</div>", unsafe_allow_html=True)
        import pandas as pd
        df = pd.DataFrame(list(categories.items()), columns=["Category", "Count"])
        df = df.sort_values("Count", ascending=False)
        st.bar_chart(df.set_index("Category"), color="#00f0ff")

    st.markdown("<div class='nav-label' style='margin-top:16px;'>Top Memories by Importance</div>", unsafe_allow_html=True)
    top = sorted(memories, key=lambda m: m.get("importance", 0), reverse=True)[:3]
    for mem in top:
        render_memory_card(mem)

    st.markdown("---")
    st.markdown("<div class='nav-label' style='margin-top:8px;'>Architecture</div>", unsafe_allow_html=True)
    st.code("""
  Streamlit UI  (:8501)
       │
       ▼
  FastAPI Backend  (:8000)  [uvicorn, async]
       │
  ┌────┴──────────┐
  │               │
  SQLite        ChromaDB  (:8001)
  (metadata)  (embeddings)
       │
       ▼
  Ollama / OpenAI  (LLM + embeddings)
""", language=None)
