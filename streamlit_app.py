"""
Bullet Memory — Streamlit UI
"""
from __future__ import annotations

import time
import os

import httpx
import streamlit as st


# ── Config ────────────────────────────────────────────────────────────────────

def _get_api_url() -> str:
    try:
        return st.secrets["API_BASE_URL"].rstrip("/")
    except Exception:
        return os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")

API_BASE_URL  = _get_api_url()
DEMO_USER_ID  = "demo-user"
REQUEST_TIMEOUT = 12.0


# ── Demo data ─────────────────────────────────────────────────────────────────

DEMO_MEMORIES = [
    {
        "id": "m1",
        "category": "PREFERENCE",
        "content": "Prefers Python over JavaScript for backend services and values clean async code.",
        "importance": 0.91,
        "confidence": 0.95,
        "source_type": "chat",
        "tags": ["python", "backend"],
        "access_count": 14,
        "created_at": "2024-11-02T10:22:00Z",
    },
    {
        "id": "m2",
        "category": "SKILL",
        "content": "Proficient with FastAPI, SQLAlchemy async, and Pydantic v2 for building production APIs.",
        "importance": 0.88,
        "confidence": 0.92,
        "source_type": "agent_event",
        "tags": ["fastapi", "pydantic"],
        "access_count": 9,
        "created_at": "2024-11-03T14:05:00Z",
    },
    {
        "id": "m3",
        "category": "GOAL",
        "content": "Building Bullet Memory as a portfolio project to demonstrate LLM engineering skills.",
        "importance": 0.97,
        "confidence": 0.99,
        "source_type": "manual",
        "tags": ["career", "portfolio"],
        "access_count": 22,
        "created_at": "2024-11-01T08:00:00Z",
    },
    {
        "id": "m4",
        "category": "FACT",
        "content": "Works best in the evening and prefers async/non-blocking architectures for I/O-bound workloads.",
        "importance": 0.74,
        "confidence": 0.85,
        "source_type": "chat",
        "tags": ["productivity"],
        "access_count": 5,
        "created_at": "2024-11-04T20:11:00Z",
    },
    {
        "id": "m5",
        "category": "TOOL_RESULT",
        "content": "ChromaDB initialised with 768-dim nomic-embed-text. Collection 'bullet_memory' has 47 vectors.",
        "importance": 0.65,
        "confidence": 0.99,
        "source_type": "agent_event",
        "tags": ["chromadb", "embeddings"],
        "access_count": 3,
        "created_at": "2024-11-05T09:30:00Z",
    },
    {
        "id": "m6",
        "category": "INSTRUCTION",
        "content": "Always reference the deduplicate_or_create pipeline when asked about LLM memory deduplication.",
        "importance": 0.82,
        "confidence": 0.90,
        "source_type": "manual",
        "tags": ["architecture"],
        "access_count": 7,
        "created_at": "2024-11-06T11:45:00Z",
    },
]

DEMO_REPLIES = {
    "what":  "**Bullet Memory** is a semantic memory engine for LLM agents. It extracts, deduplicates, and persists durable facts from conversations.\n\n- Automatic LLM extraction\n- ChromaDB vector search\n- Async FastAPI backend\n\n*[demo mode]*",
    "skill": "From your vault:\n- **FastAPI + Uvicorn** async APIs\n- **SQLAlchemy async** + aiosqlite\n- **ChromaDB** vector storage\n- **Pydantic v2** schema validation\n\n*[demo mode — 2 memories retrieved]*",
    "default": "Based on your memory profile: you're building **Bullet Memory** as a portfolio project with strong **FastAPI + async Python** skills.\n\n*[demo mode — connect a backend for live responses]*",
}


# ── API helpers ───────────────────────────────────────────────────────────────

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


# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Bullet Memory",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;700&display=swap');

/* ── Base ── */
html, body, [class*="css"], .stApp {
    font-family: 'JetBrains Mono', monospace !important;
    background: #000 !important;
    color: #c9d1d9 !important;
}

/* Kill Streamlit chrome */
header[data-testid="stHeader"], footer, #MainMenu,
.stDeployButton, [data-testid="stToolbar"] { display: none !important; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #0a0a0a !important;
    border-right: 1px solid #1a1a1a !important;
    padding: 0 !important;
}
[data-testid="stSidebarContent"] { padding: 24px 20px !important; }
[data-testid="stSidebar"] * { font-family: 'JetBrains Mono', monospace !important; }

/* ── Main ── */
.main .block-container {
    background: #000 !important;
    padding: 32px 40px !important;
    max-width: 1200px;
}

/* ── Logo ── */
.bm-logo {
    margin-bottom: 32px;
}
.bm-logo-title {
    font-size: 15px;
    font-weight: 700;
    color: #00e5ff;
    letter-spacing: 0.06em;
    display: flex;
    align-items: center;
    gap: 8px;
}
.bm-logo-dot {
    width: 7px; height: 7px;
    background: #00e5ff;
    border-radius: 50%;
    box-shadow: 0 0 8px #00e5ff;
    animation: blink 2s ease-in-out infinite;
    flex-shrink: 0;
}
.bm-logo-sub {
    font-size: 10px;
    color: #444;
    margin-top: 4px;
    letter-spacing: 0.04em;
}

/* ── Nav ── */
.stRadio > div {
    gap: 2px !important;
}
.stRadio label {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 12px !important;
    color: #555 !important;
    padding: 6px 8px !important;
    border-radius: 4px !important;
    transition: color 0.15s !important;
}
.stRadio label:hover { color: #00e5ff !important; }
[data-baseweb="radio"][aria-checked="true"] + div label,
.stRadio [aria-checked="true"] ~ div { color: #00e5ff !important; }
.stRadio div[role="radiogroup"] > label[data-checked="true"] { color: #00e5ff !important; }

/* Radio dot */
.stRadio [data-baseweb="radio"] > div:first-child {
    border-color: #333 !important;
    background: transparent !important;
}
.stRadio [aria-checked="true"] [data-baseweb="radio"] > div:first-child,
[aria-checked="true"] > div > div:first-child {
    border-color: #00e5ff !important;
    background: #00e5ff !important;
}

/* ── Status pill ── */
.status-pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.08em;
    padding: 4px 10px;
    border-radius: 2px;
    margin-top: 4px;
}
.status-live { background: rgba(0,229,255,0.06); color: #00e5ff; border: 1px solid rgba(0,229,255,0.2); }
.status-demo { background: rgba(255,200,0,0.06); color: #ffc800; border: 1px solid rgba(255,200,0,0.2); }
.status-dot { width: 5px; height: 5px; border-radius: 50%; }
.dot-live { background: #00e5ff; box-shadow: 0 0 6px #00e5ff; }
.dot-demo { background: #ffc800; box-shadow: 0 0 6px #ffc800; }

/* ── Divider ── */
.bm-divider { border: none; border-top: 1px solid #1a1a1a; margin: 20px 0; }

/* ── Page title ── */
.bm-page-title {
    font-size: 22px;
    font-weight: 700;
    color: #00e5ff;
    letter-spacing: 0.04em;
    margin-bottom: 4px;
}
.bm-page-sub {
    font-size: 11px;
    color: #444;
    margin-bottom: 28px;
    letter-spacing: 0.03em;
}

/* ── Memory card ── */
.mem-card {
    background: #0a0a0a;
    border: 1px solid #1a1a1a;
    border-left: 2px solid #00e5ff;
    padding: 14px 16px;
    margin-bottom: 8px;
    transition: border-color 0.15s;
}
.mem-card:hover { border-color: rgba(0,229,255,0.4); }

.mem-cat {
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    padding: 2px 7px;
    border: 1px solid;
    display: inline-block;
    margin-bottom: 8px;
}
.cat-PREFERENCE  { color: #00e5ff; border-color: rgba(0,229,255,0.3); }
.cat-SKILL       { color: #4ade80; border-color: rgba(74,222,128,0.3); }
.cat-GOAL        { color: #fbbf24; border-color: rgba(251,191,36,0.3); }
.cat-FACT        { color: #a78bfa; border-color: rgba(167,139,250,0.3); }
.cat-TOOL_RESULT { color: #fb923c; border-color: rgba(251,146,60,0.3); }
.cat-INSTRUCTION { color: #f472b6; border-color: rgba(244,114,182,0.3); }
.cat-default     { color: #555; border-color: #333; }

.mem-content { font-size: 13px; color: #a8b2c0; line-height: 1.6; margin: 6px 0 10px; }
.mem-footer  { font-size: 10px; color: #333; display: flex; gap: 16px; flex-wrap: wrap; }
.mem-footer b { color: #555; }

.tag {
    display: inline-block;
    font-size: 9px;
    color: #444;
    border: 1px solid #1f1f1f;
    padding: 1px 6px;
    margin: 2px 2px 2px 0;
    letter-spacing: 0.05em;
}

/* ── Stat card ── */
.stat-card {
    background: #0a0a0a;
    border: 1px solid #1a1a1a;
    padding: 20px;
    text-align: center;
}
.stat-num { font-size: 32px; font-weight: 700; color: #00e5ff; line-height: 1; }
.stat-lbl { font-size: 9px; color: #444; letter-spacing: 0.15em; text-transform: uppercase; margin-top: 8px; }

/* ── Banners ── */
.banner {
    font-size: 11px;
    padding: 9px 14px;
    margin-bottom: 20px;
    display: flex;
    align-items: center;
    gap: 8px;
    letter-spacing: 0.04em;
}
.banner-demo { background: rgba(255,200,0,0.04); border: 1px solid rgba(255,200,0,0.18); color: #887700; }
.banner-live { background: rgba(0,229,255,0.04); border: 1px solid rgba(0,229,255,0.18); color: #009999; }

/* ── Info boxes (ingest pipeline) ── */
.info-box {
    background: #0a0a0a;
    border: 1px solid #1a1a1a;
    padding: 16px;
}
.info-box-title { font-size: 10px; font-weight: 700; color: #00e5ff; letter-spacing: 0.12em; margin-bottom: 8px; }
.info-box-body  { font-size: 12px; color: #555; line-height: 1.7; }

/* ── Streamlit widgets ── */
.stButton > button {
    background: transparent !important;
    border: 1px solid #1f1f1f !important;
    color: #555 !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 11px !important;
    letter-spacing: 0.06em !important;
    border-radius: 3px !important;
    padding: 6px 16px !important;
    transition: all 0.15s !important;
}
.stButton > button:hover {
    border-color: #00e5ff !important;
    color: #00e5ff !important;
}

.stFormSubmitButton > button {
    background: rgba(0,229,255,0.06) !important;
    border: 1px solid rgba(0,229,255,0.25) !important;
    color: #00e5ff !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 11px !important;
    font-weight: 700 !important;
    letter-spacing: 0.1em !important;
    border-radius: 3px !important;
    width: 100% !important;
}
.stFormSubmitButton > button:hover {
    background: rgba(0,229,255,0.12) !important;
}

/* Inputs */
.stTextInput input, .stTextArea textarea,
div[data-baseweb="input"] input,
div[data-baseweb="textarea"] textarea {
    background: #0a0a0a !important;
    border: 1px solid #1a1a1a !important;
    border-radius: 3px !important;
    color: #c9d1d9 !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 13px !important;
}
.stTextInput input:focus, .stTextArea textarea:focus {
    border-color: rgba(0,229,255,0.4) !important;
    box-shadow: none !important;
}

/* Labels */
.stTextInput label, .stTextArea label, .stSelectbox label,
.stSlider label {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 10px !important;
    font-weight: 700 !important;
    color: #444 !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
}

/* Selectbox */
div[data-baseweb="select"] > div {
    background: #0a0a0a !important;
    border: 1px solid #1a1a1a !important;
    border-radius: 3px !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 13px !important;
    color: #c9d1d9 !important;
}

/* Slider */
.stSlider [role="slider"] { background: #00e5ff !important; }

/* Chat */
[data-testid="stChatMessage"] {
    background: #0a0a0a !important;
    border: 1px solid #1a1a1a !important;
    border-radius: 4px !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 13px !important;
}
[data-testid="stChatInput"] textarea {
    background: #0a0a0a !important;
    border: 1px solid rgba(0,229,255,0.2) !important;
    border-radius: 3px !important;
    color: #c9d1d9 !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 13px !important;
}
[data-testid="stChatInput"] textarea:focus {
    border-color: rgba(0,229,255,0.5) !important;
}

/* Caption */
.stCaption, [data-testid="stCaptionContainer"] {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 10px !important;
    color: #444 !important;
}

/* Code */
code, pre {
    background: #0a0a0a !important;
    border: 1px solid #1a1a1a !important;
    border-radius: 3px !important;
    color: #00e5ff !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 12px !important;
}

/* Scrollbar */
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: #000; }
::-webkit-scrollbar-thumb { background: #1a1a1a; }
::-webkit-scrollbar-thumb:hover { background: #00e5ff; }

/* hr */
hr { border-color: #1a1a1a !important; }

/* Spinner */
.stSpinner > div { border-top-color: #00e5ff !important; }

/* Alerts */
.stSuccess { background: rgba(74,222,128,0.04) !important; border: 1px solid rgba(74,222,128,0.2) !important; border-radius: 3px !important; font-family: 'JetBrains Mono', monospace !important; font-size: 12px !important; }
.stWarning { background: rgba(251,191,36,0.04) !important; border: 1px solid rgba(251,191,36,0.2) !important; border-radius: 3px !important; font-family: 'JetBrains Mono', monospace !important; font-size: 12px !important; }
.stError   { background: rgba(255,80,80,0.04) !important; border: 1px solid rgba(255,80,80,0.2) !important; border-radius: 3px !important; font-family: 'JetBrains Mono', monospace !important; font-size: 12px !important; }
.stInfo    { background: rgba(0,229,255,0.04) !important; border: 1px solid rgba(0,229,255,0.2) !important; border-radius: 3px !important; font-family: 'JetBrains Mono', monospace !important; font-size: 12px !important; }

@keyframes blink {
    0%, 100% { opacity: 1; }
    50%       { opacity: 0.3; }
}
</style>
""", unsafe_allow_html=True)


# ── Session state ─────────────────────────────────────────────────────────────

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": (
                "Bullet Memory online. Vault connected.\n\n"
                "Ask me anything — I'll retrieve from your memory, or just chat and I'll extract new facts automatically."
            ),
        }
    ]

if "backend_ok" not in st.session_state:
    st.session_state.backend_ok = _check_backend()


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    # Logo
    st.markdown("""
    <div class="bm-logo">
        <div class="bm-logo-title">
            <div class="bm-logo-dot"></div>
            Bullet Memory
        </div>
        <div class="bm-logo-sub">semantic memory engine</div>
    </div>
    """, unsafe_allow_html=True)

    # Navigation
    page = st.radio(
        "nav",
        ["Chat", "Ingest", "Vault", "Stats"],
        label_visibility="collapsed",
    )

    st.markdown("<hr class='bm-divider'>", unsafe_allow_html=True)

    # Status
    if st.session_state.backend_ok:
        st.markdown(
            "<div class='status-pill status-live'><div class='status-dot dot-live'></div>connected</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            "<div class='status-pill status-demo'><div class='status-dot dot-demo'></div>demo mode</div>",
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    if st.button("ping backend"):
        with st.spinner(""):
            st.session_state.backend_ok = _check_backend()
        st.rerun()

    st.markdown("<hr class='bm-divider'>", unsafe_allow_html=True)

    st.markdown(
        "<div style='font-size:10px;color:#333;line-height:2;'>FastAPI · ChromaDB · Ollama<br>"
        "<a href='https://github.com/Sudhanwa-git/Bullet-Memory' "
        "style='color:#00e5ff;text-decoration:none;'>github →</a></div>",
        unsafe_allow_html=True,
    )


# ── Memory card ───────────────────────────────────────────────────────────────

def render_memory_card(mem: dict) -> None:
    cat = mem.get("category", "FACT")
    known = {"PREFERENCE", "SKILL", "GOAL", "FACT", "TOOL_RESULT", "INSTRUCTION"}
    cat_cls = f"cat-{cat}" if cat in known else "cat-default"
    tags_html = "".join(f"<span class='tag'>{t}</span>" for t in (mem.get("tags") or []))
    imp = mem.get("importance", 0)
    filled = int(imp * 10)
    bar = "█" * filled + "░" * (10 - filled)

    st.markdown(f"""
    <div class='mem-card'>
        <div class='mem-cat {cat_cls}'>{cat}</div>
        <div class='mem-content'>{mem.get("content", "")}</div>
        <div style='margin-bottom:10px'>{tags_html}</div>
        <div class='mem-footer'>
            <span><b>{imp:.2f}</b> importance &nbsp;<span style='color:#222;letter-spacing:-1px'>{bar}</span></span>
            <span><b>{mem.get('confidence', 0):.2f}</b> confidence</span>
            <span><b>{mem.get('access_count', 0)}</b> hits</span>
            <span style='color:#2a2a2a'>{mem.get('source_type', '—')}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# Chat
# ═══════════════════════════════════════════════════════════════════════════════

if page == "Chat":
    st.markdown("<div class='bm-page-title'>Bullet Memory</div>", unsafe_allow_html=True)
    st.markdown("<div class='bm-page-sub'>memory-augmented agent chat</div>", unsafe_allow_html=True)

    if not st.session_state.backend_ok:
        st.markdown(
            "<div class='banner banner-demo'>⚠ demo mode — pre-scripted responses. connect a backend for live LLM.</div>",
            unsafe_allow_html=True,
        )

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("ask anything..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner(""):
                if st.session_state.backend_ok:
                    t0 = time.time()
                    data = _api_post("/chat", {"user_id": DEMO_USER_ID, "message": prompt})
                    ms = (time.time() - t0) * 1000
                    if data:
                        answer = data.get("response", "No response.")
                        retrieved = data.get("memories_retrieved", 0)
                        st.markdown(answer)
                        if retrieved:
                            st.caption(f"{retrieved} memories · {ms:.0f}ms")
                        st.session_state.messages.append({"role": "assistant", "content": answer})
                    else:
                        err = "backend unreachable — switching to demo mode."
                        st.markdown(err)
                        st.session_state.messages.append({"role": "assistant", "content": err})
                        st.session_state.backend_ok = False
                else:
                    pl = prompt.lower()
                    if any(w in pl for w in ("what", "explain", "how", "bullet")):
                        answer = DEMO_REPLIES["what"]
                    elif any(w in pl for w in ("skill", "know", "proficient", "experience")):
                        answer = DEMO_REPLIES["skill"]
                    else:
                        answer = DEMO_REPLIES["default"]
                    time.sleep(0.5)
                    st.markdown(answer)
                    st.session_state.messages.append({"role": "assistant", "content": answer})

    if len(st.session_state.messages) > 1:
        if st.button("clear"):
            st.session_state.messages = [st.session_state.messages[0]]
            st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# Ingest
# ═══════════════════════════════════════════════════════════════════════════════

elif page == "Ingest":
    st.markdown("<div class='bm-page-title'>Ingest</div>", unsafe_allow_html=True)
    st.markdown("<div class='bm-page-sub'>extract and store memories from raw text</div>", unsafe_allow_html=True)

    if not st.session_state.backend_ok:
        st.markdown(
            "<div class='banner banner-demo'>⚠ demo mode — ingestion disabled.</div>",
            unsafe_allow_html=True,
        )

    with st.form("ingest_form"):
        raw_text = st.text_area("raw text", height=180,
            placeholder="paste any text — logs, notes, conversations, tool outputs...")

        col1, col2 = st.columns(2)
        with col1:
            source_type = st.selectbox("source type", ["api_ingest", "chat", "agent_event", "manual"])
            tags_input  = st.text_input("tags", placeholder="python, goals, career")
        with col2:
            agent_id   = st.text_input("agent id", placeholder="my-agent-v1")
            session_id = st.text_input("session id", placeholder="session-001")

        submitted = st.form_submit_button("extract & store", use_container_width=True)

        if submitted:
            if not raw_text.strip():
                st.warning("no input.")
            elif not st.session_state.backend_ok:
                st.info("demo — in a live deployment this would extract memories via LLM.")
            else:
                with st.spinner("extracting..."):
                    tags = [t.strip() for t in tags_input.split(",") if t.strip()] if tags_input else []
                    res  = _api_post("/ingest/raw", {
                        "user_id": DEMO_USER_ID,
                        "text": raw_text,
                        "source_type": source_type,
                        "agent_id": agent_id or None,
                        "session_id": session_id or None,
                        "tags": tags,
                    })
                    if res:
                        st.success(f"{res.get('memories_stored', 0)} memories stored.")
                    else:
                        st.error("ingest failed — check backend connection.")

    st.markdown("<hr>", unsafe_allow_html=True)

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.markdown("""<div class='info-box'>
            <div class='info-box-title'>01 — LLM Extraction</div>
            <div class='info-box-body'>Text is passed to an LLM that identifies durable facts, skills, preferences, and goals.</div>
        </div>""", unsafe_allow_html=True)
    with col_b:
        st.markdown("""<div class='info-box'>
            <div class='info-box-title'>02 — Importance Scoring</div>
            <div class='info-box-body'>Each candidate memory is scored 0–1. Low-importance items are dropped.</div>
        </div>""", unsafe_allow_html=True)
    with col_c:
        st.markdown("""<div class='info-box'>
            <div class='info-box-title'>03 — Deduplication</div>
            <div class='info-box-body'>New memories are embedded and compared via cosine similarity. Near-duplicates are merged.</div>
        </div>""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# Vault
# ═══════════════════════════════════════════════════════════════════════════════

elif page == "Vault":
    st.markdown("<div class='bm-page-title'>Memory Vault</div>", unsafe_allow_html=True)
    st.markdown("<div class='bm-page-sub'>browse all persisted memories</div>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        cat_filter = st.selectbox("category", ["All", "PREFERENCE", "SKILL", "GOAL", "FACT", "TOOL_RESULT", "INSTRUCTION"])
    with col2:
        src_filter = st.selectbox("source", ["All", "chat", "agent_event", "manual", "api_ingest"])
    with col3:
        min_imp = st.slider("min imp", 0.0, 1.0, 0.0, 0.05)

    if st.session_state.backend_ok:
        params: dict = {"user_id": DEMO_USER_ID}
        if cat_filter != "All": params["category"]       = cat_filter
        if src_filter != "All": params["source_type"]    = src_filter
        if min_imp > 0:         params["min_importance"] = min_imp
        data     = _api_get(f"/memories/{DEMO_USER_ID}", **params)
        memories = data.get("memories", []) if data else []
        if not data:
            st.warning("could not load memories.")
    else:
        memories = DEMO_MEMORIES
        if cat_filter != "All": memories = [m for m in memories if m["category"]    == cat_filter]
        if src_filter != "All": memories = [m for m in memories if m["source_type"] == src_filter]
        memories = [m for m in memories if m["importance"] >= min_imp]
        st.markdown(
            "<div class='banner banner-demo'>⚠ demo data — connect backend for real vault.</div>",
            unsafe_allow_html=True,
        )

    st.markdown("<hr>", unsafe_allow_html=True)

    if not memories:
        st.markdown("<div style='color:#333;font-size:12px;padding:16px 0'>no memories match the current filters.</div>", unsafe_allow_html=True)
    else:
        st.caption(f"{len(memories)} memor{'y' if len(memories)==1 else 'ies'}")
        for mem in sorted(memories, key=lambda m: m.get("importance", 0), reverse=True):
            render_memory_card(mem)


# ═══════════════════════════════════════════════════════════════════════════════
# Stats
# ═══════════════════════════════════════════════════════════════════════════════

elif page == "Stats":
    st.markdown("<div class='bm-page-title'>Stats</div>", unsafe_allow_html=True)
    st.markdown("<div class='bm-page-sub'>memory engine overview</div>", unsafe_allow_html=True)

    if not st.session_state.backend_ok:
        st.markdown(
            "<div class='banner banner-demo'>⚠ demo mode — example data.</div>",
            unsafe_allow_html=True,
        )
        memories = DEMO_MEMORIES
    else:
        data     = _api_get(f"/memories/{DEMO_USER_ID}")
        memories = data.get("memories", []) if data else []

    total    = len(memories)
    avg_imp  = sum(m.get("importance", 0) for m in memories) / total if total else 0
    hits     = sum(m.get("access_count", 0) for m in memories)
    cats: dict[str, int] = {}
    for m in memories:
        c = m.get("category", "UNKNOWN")
        cats[c] = cats.get(c, 0) + 1

    c1, c2, c3, c4 = st.columns(4)
    for col, (num, lbl) in zip(
        [c1, c2, c3, c4],
        [(str(total), "memories"), (f"{avg_imp:.2f}", "avg importance"), (str(hits), "total hits"), (str(len(cats)), "categories")],
    ):
        with col:
            st.markdown(f"<div class='stat-card'><div class='stat-num'>{num}</div><div class='stat-lbl'>{lbl}</div></div>", unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)

    if cats:
        st.markdown("<div style='font-size:10px;color:#444;letter-spacing:.1em;text-transform:uppercase;margin-bottom:12px;'>by category</div>", unsafe_allow_html=True)
        import pandas as pd
        df = pd.DataFrame(list(cats.items()), columns=["Category", "Count"]).sort_values("Count", ascending=False)
        st.bar_chart(df.set_index("Category"), color="#00e5ff")

    st.markdown("<div style='font-size:10px;color:#444;letter-spacing:.1em;text-transform:uppercase;margin-bottom:12px;'>top memories</div>", unsafe_allow_html=True)
    for mem in sorted(memories, key=lambda m: m.get("importance", 0), reverse=True)[:3]:
        render_memory_card(mem)

    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("<div style='font-size:10px;color:#444;letter-spacing:.1em;text-transform:uppercase;margin-bottom:12px;'>architecture</div>", unsafe_allow_html=True)
    st.code("""Streamlit UI (:8501)
    └── FastAPI Backend (:8000)
        ├── SQLite          (structured metadata)
        ├── ChromaDB (:8001)(vector embeddings)
        └── Ollama          (LLM + embeddings)""", language=None)
