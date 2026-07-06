"""
Bullet Memory — Streamlit UI
Memory OS interface with integrated Chatbot Demo (No collapsible sidebar)
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
]

DEMO_REPLIES = {
    "what":    {"text": "**Bullet Memory** is a semantic memory engine for LLM agents. I extract, deduplicate, and persist facts from conversations.", "retrieved": [DEMO_MEMORIES[3]]},
    "skill":   {"text": "From what I recall, you are proficient in **FastAPI + Uvicorn** async APIs, **SQLAlchemy async**, and **Pydantic v2**.", "retrieved": [DEMO_MEMORIES[1]]},
    "default": {"text": "Based on my memory, you are building **Bullet Memory** as a portfolio project and you strongly prefer Python.", "retrieved": [DEMO_MEMORIES[0], DEMO_MEMORIES[2]]},
}


# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Bullet Memory OS",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed", # We are abandoning the native sidebar
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;700&display=swap');

/* Base */
html, body, [class*="css"], .stApp {
    font-family: 'JetBrains Mono', monospace !important;
    background: #000000 !important;
    color: #e0e0e0 !important;
}

/* Hide native sidebar and streamit chrome completely */
[data-testid="stSidebar"], [data-testid="collapsedControl"], header[data-testid="stHeader"], footer, #MainMenu, .stDeployButton { display: none !important; }

/* Main container */
.main .block-container {
    padding: 3rem 4rem !important;
    max-width: 1400px !important;
}

/* OS Panel (Left Column) */
.os-panel {
    background: #050505;
    border-right: 1px solid #1a1a1a;
    height: 100%;
    padding-right: 2rem;
}
.os-logo-name { font-size: 20px; font-weight: 700; color: #00f0ff; display: flex; align-items: center; gap: 10px; margin-bottom: 4px; }
.os-dot { width: 10px; height: 10px; border-radius: 50%; background: #00f0ff; box-shadow: 0 0 12px #00f0ff; animation: blink 2s infinite; }
.os-tagline { font-size: 11px; color: #666; letter-spacing: 0.1em; margin-bottom: 2rem; text-transform: uppercase; }

.os-section-title { font-size: 10px; font-weight: 700; color: #444; letter-spacing: 0.15em; text-transform: uppercase; margin: 2rem 0 1rem; border-bottom: 1px solid #1a1a1a; padding-bottom: 6px; }

.os-feature { margin-bottom: 1rem; }
.os-feature-title { font-size: 12px; color: #00f0ff; font-weight: 700; margin-bottom: 4px; }
.os-feature-desc { font-size: 11px; color: #888; line-height: 1.5; }

.os-status { display: inline-block; font-size: 10px; padding: 4px 8px; border-radius: 4px; border: 1px solid #1a1a1a; background: #0a0a0a; color: #888; font-weight: 700; letter-spacing: 0.1em; }
.os-live { border-color: rgba(0,240,255,0.4); color: #00f0ff; background: rgba(0,240,255,0.05); }

/* Chat inputs and forms */
.stTextInput input, .stTextArea textarea, .stChatInput textarea {
    background: #0a0a0a !important; border: 1px solid #1a1a1a !important; color: #fff !important; font-size: 14px !important; border-radius: 6px !important;
}
.stTextInput input:focus, .stTextArea textarea:focus, .stChatInput textarea:focus {
    border-color: #00f0ff !important; box-shadow: 0 0 0 1px #00f0ff !important;
}

/* Memory Cards */
.mem-card {
    background: #080808; border: 1px solid #1a1a1a; border-left: 2px solid #00f0ff;
    padding: 12px 16px; margin: 8px 0; border-radius: 4px;
}
.mem-cat { font-size: 9px; font-weight: 700; letter-spacing: 0.1em; padding: 2px 6px; border: 1px solid #1a1a1a; display: inline-block; margin-bottom: 6px; color: #00f0ff; background: #000; }
.mem-body { font-size: 13px; color: #ccc; line-height: 1.5; margin-bottom: 8px; }
.mem-meta { font-size: 10px; color: #555; display: flex; gap: 12px; }

/* Expander (Memory Context in Chat) */
.streamlit-expanderHeader { background: transparent !important; color: #00f0ff !important; font-size: 12px !important; padding: 0 !important; border: none !important; }
div[data-testid="stExpander"] { background: transparent !important; border: none !important; margin-top: 8px; }
div[data-testid="stExpander"] > div:last-child { border: none !important; border-left: 1px dashed #1a1a1a !important; padding-left: 1rem !important; margin-left: 0.5rem !important; }

/* Chat Messages */
[data-testid="stChatMessage"] { background: transparent !important; border: none !important; padding: 1rem 0 !important; }
[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] { color: #d0d0d0 !important; font-size: 14px !important; line-height: 1.6 !important; }

@keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }
hr { border-color: #1a1a1a !important; }
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

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

def render_memory_card(mem: dict) -> None:
    cat = mem.get("category", "FACT")
    imp = mem.get("importance", 0)
    st.markdown(f"""
    <div class="mem-card">
        <div class="mem-cat">{cat}</div>
        <div class="mem-body">{mem.get("content", "")}</div>
        <div class="mem-meta">
            <span>imp: {imp:.2f}</span>
            <span>hits: {mem.get('access_count', 0)}</span>
            <span>src: {mem.get('source_type','—')}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ── Session State ─────────────────────────────────────────────────────────────

if "backend_ok" not in st.session_state:
    try:
        st.session_state.backend_ok = (httpx.get(f"{API_BASE_URL}/health", timeout=2.0).status_code == 200)
    except:
        st.session_state.backend_ok = False

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "I am connected to the Memory OS. Ask me anything, and I will retrieve context from the vault in real-time.",
            "retrieved": [],
            "extracted": []
        }
    ]


# ═══════════════════════════════════════════════════════════════════════════════
# Layout: OS Panel (Left) & Chatbot Demo (Right)
# ═══════════════════════════════════════════════════════════════════════════════

col_os, col_demo = st.columns([1, 2.5], gap="large")

# ─── OS Panel (Left Column) ──────────────────────────────────────────────────
with col_os:
    st.markdown("""
    <div class="os-logo-name"><div class="os-dot"></div>Bullet Memory OS</div>
    <div class="os-tagline">Semantic Memory Engine</div>
    """, unsafe_allow_html=True)

    if st.session_state.backend_ok:
        st.markdown("<div class='os-status os-live'>● BACKEND CONNECTED</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='os-status'>○ DEMO MODE</div>", unsafe_allow_html=True)

    st.markdown("<div class='os-section-title'>Core Features</div>", unsafe_allow_html=True)
    
    st.markdown("""
    <div class="os-feature">
        <div class="os-feature-title">Semantic Retrieval</div>
        <div class="os-feature-desc">Queries ChromaDB for relevant past context before the LLM generates a response.</div>
    </div>
    <div class="os-feature">
        <div class="os-feature-title">Auto-Extraction</div>
        <div class="os-feature-desc">Background LLM tasks automatically distill chat history into structured facts.</div>
    </div>
    <div class="os-feature">
        <div class="os-feature-title">Deduplication</div>
        <div class="os-feature-desc">Cosine similarity prevents redundant facts from polluting the vector space.</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div class='os-section-title'>Architecture</div>", unsafe_allow_html=True)
    st.code("""UI       : Streamlit
API      : FastAPI
Vector   : ChromaDB
LLM      : Ollama
DB       : SQLite Async""", language="text")

    st.markdown("<div class='os-section-title'>Vault Stats</div>", unsafe_allow_html=True)
    if st.session_state.backend_ok:
        data = _api_get(f"/memories/{DEMO_USER_ID}")
        mems = data.get("memories", []) if data else []
    else:
        mems = DEMO_MEMORIES
        
    st.markdown(f"""
    <div style="font-size:12px; color:#aaa; line-height:1.8;">
        Total Memories: <b>{len(mems)}</b><br>
        Vector Dimensions: <b>768</b><br>
        Access Hits: <b>{sum(m.get('access_count', 0) for m in mems)}</b>
    </div>
    """, unsafe_allow_html=True)


# ─── Chatbot Demo (Right Column) ─────────────────────────────────────────────
with col_demo:
    
    st.markdown("<div style='font-size:18px; font-weight:700; color:#fff; margin-bottom:4px;'>Live Demonstration</div>", unsafe_allow_html=True)
    st.markdown("<div style='font-size:12px; color:#666; margin-bottom:2rem;'>Interact with the agent. The OS will inject memory context inline.</div>", unsafe_allow_html=True)

    chat_container = st.container(height=600, border=False)
    
    with chat_container:
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                
                # Show memory context inline via expander
                if msg.get("retrieved"):
                    with st.expander(f"🧠 {len(msg['retrieved'])} memories retrieved for context"):
                        for m in msg["retrieved"]:
                            render_memory_card(m)
                
                if msg.get("extracted"):
                    with st.expander(f"⚡ {len(msg['extracted'])} new memories extracted and stored"):
                        for m in msg["extracted"]:
                            render_memory_card(m)

    # Chat Input
    if prompt := st.chat_input("Message the Memory OS..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with chat_container:
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                with st.spinner("Processing memory..."):
                    if st.session_state.backend_ok:
                        data = _api_post("/chat", {"user_id": DEMO_USER_ID, "message": prompt})
                        if data:
                            answer = data.get("response", "No response.")
                            retrieved = data.get("retrieved_context", [])
                            
                            st.markdown(answer)
                            if retrieved:
                                with st.expander(f"🧠 {len(retrieved)} memories retrieved for context"):
                                    for m in retrieved:
                                        render_memory_card(m)
                                        
                            st.session_state.messages.append({
                                "role": "assistant", 
                                "content": answer,
                                "retrieved": retrieved,
                                "extracted": []
                            })
                        else:
                            st.error("Backend error.")
                            st.session_state.backend_ok = False
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
                        retrieved = demo_resp["retrieved"]
                        
                        st.markdown(answer)
                        with st.expander(f"🧠 {len(retrieved)} memories retrieved for context"):
                            for m in retrieved:
                                render_memory_card(m)
                                
                        st.session_state.messages.append({
                            "role": "assistant", 
                            "content": answer,
                            "retrieved": retrieved,
                            "extracted": []
                        })
        st.rerun()
