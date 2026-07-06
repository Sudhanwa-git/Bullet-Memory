"""
Bullet Memory — Streamlit UI
Live Demonstration Dashboard
"""
from __future__ import annotations

import time
import os
import json

import httpx
import streamlit as st


# ── Config ────────────────────────────────────────────────────────────────────

def _get_api_url() -> str:
    try:
        return st.secrets["API_BASE_URL"].rstrip("/")
    except Exception:
        return os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")

API_BASE_URL    = _get_api_url()
DEMO_USER_ID    = "demo-user"
REQUEST_TIMEOUT = 12.0


# ── Demo data ─────────────────────────────────────────────────────────────────

DEMO_MEMORIES = [
    {"id": "m1",  "category": "GOAL",        "content": "Building Bullet Memory as a portfolio project to demonstrate LLM engineering skills to recruiters.",        "importance": 0.97, "confidence": 0.99, "source_type": "manual",       "tags": ["career", "portfolio"],         "access_count": 22, "created_at": "2024-11-01T08:00:00Z"},
    {"id": "m2",  "category": "SKILL",       "content": "Proficient with FastAPI, SQLAlchemy async, and Pydantic v2 for building production APIs.",                  "importance": 0.88, "confidence": 0.92, "source_type": "agent_event",  "tags": ["fastapi", "pydantic", "async"], "access_count": 9,  "created_at": "2024-11-03T14:05:00Z"},
    {"id": "m3",  "category": "PREFERENCE",  "content": "Prefers Python over JavaScript for backend services and values clean, async-first code.",                    "importance": 0.91, "confidence": 0.95, "source_type": "chat",          "tags": ["python", "backend"],            "access_count": 14, "created_at": "2024-11-02T10:22:00Z"},
    {"id": "m4",  "category": "INSTRUCTION", "content": "When asked about LLM memory, always reference the deduplicate_or_create pipeline that prevents redundant storage via cosine similarity.", "importance": 0.82, "confidence": 0.90, "source_type": "manual", "tags": ["architecture"], "access_count": 7, "created_at": "2024-11-06T11:45:00Z"},
    {"id": "m5",  "category": "FACT",        "content": "Works best in the evening and prefers async/non-blocking architectures for all I/O-bound workloads.",        "importance": 0.74, "confidence": 0.85, "source_type": "chat",          "tags": ["productivity"],                 "access_count": 5,  "created_at": "2024-11-04T20:11:00Z"},
    {"id": "m6",  "category": "TOOL_RESULT", "content": "ChromaDB initialised with 768-dim nomic-embed-text embeddings. Collection 'bullet_memory' has 47 vectors.", "importance": 0.65, "confidence": 0.99, "source_type": "agent_event",  "tags": ["chromadb", "embeddings"],       "access_count": 3,  "created_at": "2024-11-05T09:30:00Z"},
]

DEMO_REPLIES = {
    "what":    {"text": "**Bullet Memory** is a semantic memory engine for LLM agents — extracts, deduplicates, and persists durable facts from conversations.\n\n- Automatic LLM extraction\n- ChromaDB vector search\n- Async FastAPI backend", "retrieved": [DEMO_MEMORIES[3]]},
    "skill":   {"text": "From your vault:\n- **FastAPI + Uvicorn** async APIs\n- **SQLAlchemy async** + aiosqlite\n- **ChromaDB** vector storage\n- **Pydantic v2** schema validation", "retrieved": [DEMO_MEMORIES[1]]},
    "default": {"text": "Based on your memory profile: you're building **Bullet Memory** as a portfolio project with strong **FastAPI + async Python** skills.", "retrieved": [DEMO_MEMORIES[0], DEMO_MEMORIES[2]]},
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

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;700&display=swap');

/* ─── Base ─────────────────────────────────────────────────────────────────── */
html, body, [class*="css"], .stApp {
    font-family: 'JetBrains Mono', monospace !important;
    background: #000 !important;
    color: #c8d0da !important;
}
header[data-testid="stHeader"], footer, #MainMenu,
.stDeployButton, [data-testid="stToolbar"] { display: none !important; }

/* ─── Sidebar ───────────────────────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: #040404 !important;
    border-right: 1px solid #111 !important;
    min-width: 220px !important;
}
[data-testid="stSidebarContent"] {
    padding: 28px 20px 20px !important;
    display: flex;
    flex-direction: column;
    height: 100%;
}
[data-testid="stSidebar"] * { font-family: 'JetBrains Mono', monospace !important; }

/* Logo */
.sb-logo { margin-bottom: 28px; }
.sb-logo-name {
    font-size: 14px; font-weight: 700;
    color: #00e5ff; letter-spacing: .04em;
    display: flex; align-items: center; gap: 8px;
}
.sb-dot {
    width: 7px; height: 7px; border-radius: 50%;
    background: #00e5ff; box-shadow: 0 0 8px #00e5ff;
    animation: blink 2s ease-in-out infinite; flex-shrink: 0;
}
.sb-tagline { font-size: 10px; color: #333; margin-top: 4px; letter-spacing: .03em; }

/* Nav items */
.stRadio > div { gap: 0 !important; }
.stRadio label {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 12px !important; color: #444 !important;
    padding: 7px 10px !important; border-radius: 3px !important;
    display: block !important; transition: color .15s !important;
    letter-spacing: .03em !important;
}
.stRadio label:hover { color: #00e5ff !important; background: rgba(0,229,255,.04) !important; }
.stRadio [aria-checked="true"] > div > div:first-child {
    border-color: #00e5ff !important; background: #00e5ff !important;
}
.stRadio [data-baseweb="radio"] > div:first-child {
    border-color: #222 !important; background: transparent !important;
    width: 12px !important; height: 12px !important;
}

/* Status */
.sb-status {
    display: inline-flex; align-items: center; gap: 6px;
    font-size: 10px; font-weight: 600; letter-spacing: .08em;
    padding: 5px 10px; border-radius: 2px; margin-top: 6px;
}
.sb-live { color: #00e5ff; background: rgba(0,229,255,.05); border: 1px solid rgba(0,229,255,.18); }
.sb-demo { color: #ffc800; background: rgba(255,200,0,.05); border: 1px solid rgba(255,200,0,.18); }
.sb-dot-s { width: 5px; height: 5px; border-radius: 50%; flex-shrink: 0; }
.dot-live  { background: #00e5ff; box-shadow: 0 0 6px #00e5ff; }
.dot-demo  { background: #ffc800; box-shadow: 0 0 6px #ffc800; }

/* Quick stat in sidebar */
.sb-stat {
    display: flex; justify-content: space-between; align-items: center;
    padding: 5px 0; border-bottom: 1px solid #0e0e0e;
    font-size: 11px; color: #333;
}
.sb-stat b { color: #555; }
.sb-footer { font-size: 10px; color: #2a2a2a; line-height: 2; margin-top: auto; padding-top: 20px; }
.sb-footer a { color: #00e5ff; text-decoration: none; }

/* ─── Main ─────────────────────────────────────────────────────────────────── */
.main .block-container {
    background: #000 !important;
    padding: 28px 36px !important;
    max-width: 1300px;
}

/* Page header */
.ph { margin-bottom: 24px; }
.ph-title { font-size: 20px; font-weight: 700; color: #00e5ff; letter-spacing: .04em; }
.ph-sub   { font-size: 11px; color: #444; margin-top: 3px; }

/* Section label */
.sec { font-size: 10px; font-weight: 700; color: #333; letter-spacing: .15em; text-transform: uppercase; margin-bottom: 12px; border-bottom: 1px solid #111; padding-bottom: 6px; }

/* ─── Stat cards ────────────────────────────────────────────────────────────── */
.stat-row { display: flex; gap: 12px; margin-bottom: 28px; }
.stat-card {
    flex: 1; background: #060606; border: 1px solid #111;
    border-top: 2px solid #00e5ff; padding: 16px 14px; text-align: center;
}
.stat-n { font-size: 30px; font-weight: 700; color: #00e5ff; line-height: 1; }
.stat-l { font-size: 9px; color: #333; letter-spacing: .15em; text-transform: uppercase; margin-top: 6px; }

/* ─── Memory cards ──────────────────────────────────────────────────────────── */
.mem-card {
    background: #060606; border: 1px solid #111;
    border-left: 2px solid #00e5ff;
    padding: 13px 16px; margin-bottom: 8px;
    transition: border-color .15s, background .15s;
}
.mem-card:hover { border-color: rgba(0,229,255,.3); background: #080808; }

.mem-cat {
    font-size: 9px; font-weight: 700; letter-spacing: .16em;
    text-transform: uppercase; padding: 2px 7px; border: 1px solid;
    display: inline-block; margin-bottom: 8px;
}
.c-PREFERENCE  { color: #00e5ff; border-color: rgba(0,229,255,.3);  }
.c-SKILL       { color: #4ade80; border-color: rgba(74,222,128,.3); }
.c-GOAL        { color: #fbbf24; border-color: rgba(251,191,36,.3); }
.c-FACT        { color: #a78bfa; border-color: rgba(167,139,250,.3); }
.c-TOOL_RESULT { color: #fb923c; border-color: rgba(251,146,60,.3); }
.c-INSTRUCTION { color: #f472b6; border-color: rgba(244,114,182,.3); }
.c-default     { color: #444; border-color: #222; }

.mem-body { font-size: 13px; color: #a0aab4; line-height: 1.6; margin: 5px 0 10px; }
.mem-meta { font-size: 10px; color: #2e2e2e; display: flex; gap: 14px; flex-wrap: wrap; }
.mem-meta b { color: #484848; }
.mem-tag  { font-size: 9px; color: #333; border: 1px solid #1a1a1a; padding: 1px 6px; margin: 2px 2px 2px 0; display: inline-block; }

/* ─── Info box (pipeline steps) ─────────────────────────────────────────────── */
.info-box { background: #060606; border: 1px solid #111; padding: 16px; height: 100%; }
.info-title { font-size: 10px; font-weight: 700; color: #00e5ff; letter-spacing: .12em; margin-bottom: 8px; }
.info-body  { font-size: 12px; color: #3a3a3a; line-height: 1.8; }

/* ─── Banners ───────────────────────────────────────────────────────────────── */
.banner { font-size: 11px; padding: 8px 14px; margin-bottom: 20px; display: flex; align-items: center; gap: 8px; letter-spacing: .03em; border-radius: 2px; }
.b-demo { background: rgba(255,200,0,.04); border: 1px solid rgba(255,200,0,.15); color: #887700; }
.b-live { background: rgba(0,229,255,.04); border: 1px solid rgba(0,229,255,.15); color: #007777; }

/* ─── Widgets ───────────────────────────────────────────────────────────────── */
.stButton > button {
    background: transparent !important; border: 1px solid #1a1a1a !important;
    color: #444 !important; font-family: 'JetBrains Mono', monospace !important;
    font-size: 11px !important; letter-spacing: .05em !important;
    border-radius: 3px !important; padding: 5px 14px !important; transition: all .15s !important;
}
.stButton > button:hover { border-color: #00e5ff !important; color: #00e5ff !important; }

.stFormSubmitButton > button {
    background: rgba(0,229,255,.05) !important; border: 1px solid rgba(0,229,255,.2) !important;
    color: #00e5ff !important; font-family: 'JetBrains Mono', monospace !important;
    font-size: 11px !important; font-weight: 700 !important; letter-spacing: .08em !important;
    border-radius: 3px !important; width: 100% !important;
}
.stFormSubmitButton > button:hover { background: rgba(0,229,255,.1) !important; }

.stTextInput input, .stTextArea textarea,
div[data-baseweb="input"] input, div[data-baseweb="textarea"] textarea {
    background: #060606 !important; border: 1px solid #111 !important;
    border-radius: 3px !important; color: #c8d0da !important;
    font-family: 'JetBrains Mono', monospace !important; font-size: 13px !important;
}
.stTextInput input:focus, .stTextArea textarea:focus {
    border-color: rgba(0,229,255,.35) !important; box-shadow: none !important;
}
.stTextInput label, .stTextArea label, .stSelectbox label, .stSlider label {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 10px !important; font-weight: 700 !important;
    color: #333 !important; letter-spacing: .1em !important; text-transform: uppercase !important;
}
div[data-baseweb="select"] > div {
    background: #060606 !important; border: 1px solid #111 !important;
    border-radius: 3px !important; font-family: 'JetBrains Mono', monospace !important;
    font-size: 13px !important; color: #c8d0da !important;
}
.stSlider [role="slider"] { background: #00e5ff !important; }

/* Chat */
[data-testid="stChatMessage"] {
    background: #060606 !important; border: 1px solid #111 !important;
    border-radius: 4px !important; font-size: 13px !important;
    font-family: 'JetBrains Mono', monospace !important;
}
[data-testid="stChatInput"] textarea {
    background: #060606 !important; border: 1px solid rgba(0,229,255,.18) !important;
    border-radius: 3px !important; color: #c8d0da !important;
    font-family: 'JetBrains Mono', monospace !important; font-size: 13px !important;
}
[data-testid="stChatInput"] textarea:focus { border-color: rgba(0,229,255,.4) !important; }

/* Misc */
.stCaption, [data-testid="stCaptionContainer"] {
    font-family: 'JetBrains Mono', monospace !important; font-size: 10px !important; color: #555 !important;
}
code, pre {
    background: #060606 !important; border: 1px solid #111 !important;
    border-radius: 3px !important; color: #00e5ff !important;
    font-family: 'JetBrains Mono', monospace !important; font-size: 12px !important;
}
hr { border-color: #111 !important; }
.stSpinner > div { border-top-color: #00e5ff !important; }
.stSuccess { background: rgba(74,222,128,.04) !important; border: 1px solid rgba(74,222,128,.2) !important; border-radius: 3px !important; font-family: 'JetBrains Mono', monospace !important; font-size: 12px !important; }
.stWarning { background: rgba(251,191,36,.04) !important; border: 1px solid rgba(251,191,36,.2) !important; border-radius: 3px !important; font-family: 'JetBrains Mono', monospace !important; font-size: 12px !important; }
.stError   { background: rgba(255,80,80,.04) !important; border: 1px solid rgba(255,80,80,.2) !important; border-radius: 3px !important; font-family: 'JetBrains Mono', monospace !important; font-size: 12px !important; }
.stInfo    { background: rgba(0,229,255,.04) !important; border: 1px solid rgba(0,229,255,.2) !important; border-radius: 3px !important; font-family: 'JetBrains Mono', monospace !important; font-size: 12px !important; }
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: #000; }
::-webkit-scrollbar-thumb { background: #111; }
::-webkit-scrollbar-thumb:hover { background: #00e5ff; }

@keyframes blink {
    0%, 100% { opacity: 1; }
    50%       { opacity: .3; }
}
</style>
""", unsafe_allow_html=True)


# ── Session state ─────────────────────────────────────────────────────────────

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content":
            "Bullet Memory online. Vault connected.\n\n"
            "Ask me anything — I'll automatically retrieve relevant memories from the vault to enrich my response."},
    ]
if "last_retrieved" not in st.session_state:
    st.session_state.last_retrieved = []
if "backend_ok" not in st.session_state:
    st.session_state.backend_ok = _check_backend()


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    # ── Logo ──
    st.markdown("""
    <div class="sb-logo">
        <div class="sb-logo-name"><div class="sb-dot"></div>Bullet Memory</div>
        <div class="sb-tagline">semantic memory engine</div>
    </div>
    """, unsafe_allow_html=True)

    # ── Navigation ──
    page = st.radio(
        "nav",
        ["Dashboard", "Memory Vault", "Ingest"],
        label_visibility="collapsed",
    )

    st.markdown("<hr style='border-color:#111;margin:20px 0'>", unsafe_allow_html=True)

    # ── Status ──
    if st.session_state.backend_ok:
        st.markdown(
            "<div class='sb-status sb-live'><div class='sb-dot-s dot-live'></div>LIVE</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            "<div class='sb-status sb-demo'><div class='sb-dot-s dot-demo'></div>DEMO MODE</div>",
            unsafe_allow_html=True,
        )
    st.caption(f"`{API_BASE_URL}`")

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    if st.button("ping backend"):
        with st.spinner(""):
            st.session_state.backend_ok = _check_backend()
        st.rerun()

    st.markdown("<hr style='border-color:#111;margin:20px 0'>", unsafe_allow_html=True)

    # ── Quick stats ──
    total = len(DEMO_MEMORIES)
    avg_imp = round(sum(m["importance"] for m in DEMO_MEMORIES) / total, 2) if total else 0
    st.markdown(f"""
    <div class="sb-stat"><span>memories</span><b>{total}</b></div>
    <div class="sb-stat"><span>avg importance</span><b>{avg_imp}</b></div>
    <div class="sb-stat"><span>categories</span><b>6</b></div>
    <div class="sb-stat"><span>vector dims</span><b>768</b></div>
    """, unsafe_allow_html=True)

    # ── Footer ──
    st.markdown(
        "<div class='sb-footer'>FastAPI &nbsp;·&nbsp; ChromaDB &nbsp;·&nbsp; Ollama<br>"
        "<a href='https://github.com/Sudhanwa-git/Bullet-Memory'>github →</a></div>",
        unsafe_allow_html=True,
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

CAT_KNOWN = {"PREFERENCE", "SKILL", "GOAL", "FACT", "TOOL_RESULT", "INSTRUCTION"}

def render_memory_card(mem: dict) -> None:
    cat     = mem.get("category", "FACT")
    cat_cls = f"c-{cat}" if cat in CAT_KNOWN else "c-default"
    tags    = "".join(f"<span class='mem-tag'>{t}</span>" for t in (mem.get("tags") or []))
    imp     = mem.get("importance", 0)
    bar     = "█" * int(imp * 10) + "░" * (10 - int(imp * 10))

    st.markdown(f"""
    <div class="mem-card">
        <div class="mem-cat {cat_cls}">{cat}</div>
        <div class="mem-body">{mem.get("content", "")}</div>
        <div style="margin-bottom:10px">{tags}</div>
        <div class="mem-meta">
            <span><b>{imp:.2f}</b> importance &nbsp;<span style="color:#1e1e1e;letter-spacing:-1px">{bar}</span></span>
            <span><b>{mem.get('confidence', 0):.2f}</b> confidence</span>
            <span><b>{mem.get('access_count', 0)}</b> hits</span>
            <span style="color:#222">{mem.get('source_type','—')}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


def _load_memories(cat_f="All", src_f="All", min_i=0.0) -> list[dict]:
    if st.session_state.backend_ok:
        params: dict = {"user_id": DEMO_USER_ID}
        if cat_f != "All": params["category"]       = cat_f
        if src_f != "All": params["source_type"]    = src_f
        if min_i  > 0:     params["min_importance"] = min_i
        data = _api_get(f"/memories/{DEMO_USER_ID}", **params)
        return data.get("memories", []) if data else []
    else:
        mems = list(DEMO_MEMORIES)
        if cat_f != "All": mems = [m for m in mems if m["category"]    == cat_f]
        if src_f != "All": mems = [m for m in mems if m["source_type"] == src_f]
        return [m for m in mems if m["importance"] >= min_i]


def demo_banner() -> None:
    if not st.session_state.backend_ok:
        st.markdown(
            "<div class='banner b-demo'>⚠ demo mode — showing example data. run docker-compose up to connect a live backend.</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            "<div class='banner b-live'>● live — connected to backend.</div>",
            unsafe_allow_html=True,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Dashboard — Live Demonstration
# ═══════════════════════════════════════════════════════════════════════════════

if page == "Dashboard":
    st.markdown("""
    <div class="ph">
        <div class="ph-title">Live Demonstration</div>
        <div class="ph-sub">interact with the agent to see the memory OS retrieve facts in real-time</div>
    </div>
    """, unsafe_allow_html=True)

    demo_banner()

    # ── Stats row ──────────────────────────────────────────────────────────────
    mems = _load_memories()
    total       = len(mems)
    avg_imp     = sum(m.get("importance", 0) for m in mems) / total if total else 0
    total_hits  = sum(m.get("access_count", 0) for m in mems)
    cats: dict  = {}
    for m in mems:
        c = m.get("category", "?")
        cats[c] = cats.get(c, 0) + 1

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"<div class='stat-card'><div class='stat-n'>{total}</div><div class='stat-l'>memories stored</div></div>", unsafe_allow_html=True)
    with c2:
        st.markdown(f"<div class='stat-card'><div class='stat-n'>{avg_imp:.2f}</div><div class='stat-l'>avg importance</div></div>", unsafe_allow_html=True)
    with c3:
        st.markdown(f"<div class='stat-card'><div class='stat-n'>{total_hits}</div><div class='stat-l'>total retrievals</div></div>", unsafe_allow_html=True)
    with c4:
        st.markdown(f"<div class='stat-card'><div class='stat-n'>{len(cats)}</div><div class='stat-l'>categories</div></div>", unsafe_allow_html=True)

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # ── Split layout: Chat vs Live Memory Engine ──────────────────────────────
    left, right = st.columns([1, 1], gap="large")

    with left:
        st.markdown("<div class='sec'>Agent Chat</div>", unsafe_allow_html=True)
        
        chat_container = st.container(height=500, border=False)
        with chat_container:
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

        if prompt := st.chat_input("ask anything to trigger memory retrieval..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            with chat_container:
                with st.chat_message("user"):
                    st.markdown(prompt)

                with st.chat_message("assistant"):
                    with st.spinner("retrieving context..."):
                        if st.session_state.backend_ok:
                            t0   = time.time()
                            data = _api_post("/chat", {"user_id": DEMO_USER_ID, "message": prompt})
                            ms   = (time.time() - t0) * 1000
                            if data:
                                answer    = data.get("response", "No response.")
                                retrieved_list = data.get("retrieved_context", [])
                                st.session_state.last_retrieved = retrieved_list
                                
                                st.markdown(answer)
                                if retrieved_list:
                                    st.caption(f"{len(retrieved_list)} memories retrieved in {ms:.0f}ms")
                                st.session_state.messages.append({"role": "assistant", "content": answer})
                            else:
                                err = "backend unreachable — switching to demo mode."
                                st.markdown(err)
                                st.session_state.messages.append({"role": "assistant", "content": err})
                                st.session_state.backend_ok = False
                                st.session_state.last_retrieved = []
                        else:
                            pl = prompt.lower()
                            if any(w in pl for w in ("what", "explain", "how", "bullet")):
                                demo_resp = DEMO_REPLIES["what"]
                            elif any(w in pl for w in ("skill", "know", "proficient", "experience")):
                                demo_resp = DEMO_REPLIES["skill"]
                            else:
                                demo_resp = DEMO_REPLIES["default"]
                            
                            time.sleep(0.5)
                            answer = demo_resp["text"]
                            st.session_state.last_retrieved = demo_resp["retrieved"]
                            
                            st.markdown(answer)
                            if st.session_state.last_retrieved:
                                st.caption(f"{len(st.session_state.last_retrieved)} memories retrieved in 12ms")
                            st.session_state.messages.append({"role": "assistant", "content": answer})
            st.rerun()

        if len(st.session_state.messages) > 1:
            if st.button("clear chat"):
                st.session_state.messages = [st.session_state.messages[0]]
                st.session_state.last_retrieved = []
                st.rerun()

    with right:
        st.markdown("<div class='sec'>Live Memory Feed</div>", unsafe_allow_html=True)
        st.markdown("<div style='font-size:11px; color:#555; margin-bottom:16px;'>Memories retrieved by the OS to contextualise the last response:</div>", unsafe_allow_html=True)
        
        retrieved = st.session_state.last_retrieved
        
        if not retrieved:
            st.markdown("""
            <div style="background:#060606; border:1px dashed #1a1a1a; padding: 40px 20px; text-align:center; color:#333; font-size:11px;">
                waiting for interaction...
                <br>
                ask a question to see memory retrieval in action.
            </div>
            """, unsafe_allow_html=True)
        else:
            for mem in retrieved:
                render_memory_card(mem)


# ═══════════════════════════════════════════════════════════════════════════════
# Memory Vault
# ═══════════════════════════════════════════════════════════════════════════════

elif page == "Memory Vault":
    st.markdown("""
    <div class="ph">
        <div class="ph-title">Memory Vault</div>
        <div class="ph-sub">all persisted memories — filterable by category, source and importance</div>
    </div>
    """, unsafe_allow_html=True)

    demo_banner()

    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        cat_f = st.selectbox("category", ["All", "PREFERENCE", "SKILL", "GOAL", "FACT", "TOOL_RESULT", "INSTRUCTION"])
    with col2:
        src_f = st.selectbox("source", ["All", "chat", "agent_event", "manual", "api_ingest"])
    with col3:
        min_i = st.slider("min importance", 0.0, 1.0, 0.0, 0.05)

    st.markdown("<hr>", unsafe_allow_html=True)

    mems = _load_memories(cat_f, src_f, min_i)

    if not mems:
        st.markdown("<div style='color:#333;font-size:12px;padding:16px 0'>no memories match the filters.</div>", unsafe_allow_html=True)
    else:
        st.caption(f"{len(mems)} memor{'y' if len(mems)==1 else 'ies'}")
        for m in sorted(mems, key=lambda x: x.get("importance", 0), reverse=True):
            render_memory_card(m)


# ═══════════════════════════════════════════════════════════════════════════════
# Ingest
# ═══════════════════════════════════════════════════════════════════════════════

elif page == "Ingest":
    st.markdown("""
    <div class="ph">
        <div class="ph-title">Ingest</div>
        <div class="ph-sub">feed raw text to the memory extraction pipeline</div>
    </div>
    """, unsafe_allow_html=True)

    demo_banner()

    with st.form("ingest_form"):
        raw_text = st.text_area("raw text", height=180,
            placeholder="paste any text — logs, notes, conversations, tool outputs, documents...")

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
                st.warning("provide some text to ingest.")
            elif not st.session_state.backend_ok:
                st.info("demo — in a live deployment this would extract and deduplicate memories using an LLM.")
            else:
                with st.spinner("extracting memories..."):
                    tags = [t.strip() for t in tags_input.split(",") if t.strip()] if tags_input else []
                    res  = _api_post("/ingest/raw", {
                        "user_id": DEMO_USER_ID, "text": raw_text,
                        "source_type": source_type,
                        "agent_id": agent_id or None, "session_id": session_id or None,
                        "tags": tags,
                    })
                    if res:
                        st.success(f"{res.get('memories_stored', 0)} memories extracted and stored.")
                    else:
                        st.error("ingest failed — check backend connection.")

    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("<div class='sec'>extraction pipeline</div>", unsafe_allow_html=True)

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.markdown("""<div class='info-box'>
            <div class='info-title'>01 — LLM Extraction</div>
            <div class='info-body'>Text is passed to an LLM that identifies durable facts, skills, preferences, and goals. Greetings and filler are ignored.</div>
        </div>""", unsafe_allow_html=True)
    with col_b:
        st.markdown("""<div class='info-box'>
            <div class='info-title'>02 — Importance Scoring</div>
            <div class='info-body'>Each candidate memory is scored 0–1 by the LLM. Items below the configurable threshold are dropped.</div>
        </div>""", unsafe_allow_html=True)
    with col_c:
        st.markdown("""<div class='info-box'>
            <div class='info-title'>03 — Deduplication</div>
            <div class='info-body'>New memories are embedded and compared via cosine similarity against the vector store. Near-duplicates are merged, not duplicated.</div>
        </div>""", unsafe_allow_html=True)
