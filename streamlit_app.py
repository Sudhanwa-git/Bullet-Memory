"""
Bullet Memory — Streamlit UI
Memory OS (Right Panel) with Chatbot Demo (Left Panel)
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
    initial_sidebar_state="collapsed", 
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
    padding: 1rem 4rem !important;
    max-width: 1600px !important;
}

/* Layout Columns */
.chat-col { padding-right: 1rem; }
.os-col { padding-left: 1rem; border-left: 1px solid #1a1a1a; min-height: 80vh; }

/* OS Panel styling */
.os-logo-name { font-size: 22px; font-weight: 700; color: #00f0ff; display: flex; align-items: center; gap: 10px; margin-bottom: 4px; }
.os-dot { width: 10px; height: 10px; border-radius: 50%; background: #00f0ff; box-shadow: 0 0 12px #00f0ff; animation: blink 2s infinite; }
.os-tagline { font-size: 11px; color: #666; letter-spacing: 0.1em; margin-bottom: 1.5rem; text-transform: uppercase; }
.os-status { display: inline-block; font-size: 10px; padding: 4px 8px; border-radius: 4px; border: 1px solid #1a1a1a; background: #0a0a0a; color: #888; font-weight: 700; letter-spacing: 0.1em; margin-bottom: 1.5rem; }
.os-live { border-color: rgba(0,240,255,0.4); color: #00f0ff; background: rgba(0,240,255,0.05); }

/* Tabs */
.stTabs [data-baseweb="tab-list"] { background: transparent !important; border-bottom: 1px solid #1a1a1a; gap: 24px; padding-bottom: 8px; }
.stTabs [data-baseweb="tab"] { background: transparent !important; font-family: 'JetBrains Mono', monospace !important; font-size: 12px !important; color: #666 !important; padding: 0 !important; border: none !important; margin: 0 !important; text-transform: uppercase; letter-spacing: 0.05em; font-weight: 700; }
.stTabs [aria-selected="true"] { color: #00f0ff !important; border-bottom: 2px solid #00f0ff !important; padding-bottom: 6px !important; }

/* Memory Cards */
.mem-card { background: #080808; border: 1px solid #1a1a1a; border-left: 2px solid #00f0ff; padding: 12px 16px; margin: 8px 0; border-radius: 4px; }
.mem-cat { font-size: 9px; font-weight: 700; letter-spacing: 0.1em; padding: 2px 6px; border: 1px solid #1a1a1a; display: inline-block; margin-bottom: 6px; color: #00f0ff; background: #000; }
.mem-body { font-size: 13px; color: #ccc; line-height: 1.5; margin-bottom: 8px; }
.mem-meta { font-size: 10px; color: #555; display: flex; gap: 12px; }

/* Form inputs & Buttons */
.stTextInput input, .stTextArea textarea, .stChatInput textarea, div[data-baseweb="select"] > div {
    background: #0a0a0a !important; border: 1px solid #1a1a1a !important; color: #fff !important; font-size: 13px !important; border-radius: 4px !important;
}
.stTextInput input:focus, .stTextArea textarea:focus, .stChatInput textarea:focus { border-color: #00f0ff !important; box-shadow: 0 0 0 1px #00f0ff !important; }
.stTextInput label, .stTextArea label, .stSelectbox label { font-size: 10px !important; color: #666 !important; text-transform: uppercase; letter-spacing: 0.1em; }
.stButton > button, .stFormSubmitButton > button, .stDownloadButton > button {
    background: #0a0a0a !important; border: 1px solid #1a1a1a !important; color: #888 !important; border-radius: 4px !important; font-family: 'JetBrains Mono', monospace !important; font-size: 11px !important; text-transform: uppercase; letter-spacing: 0.1em; padding: 8px 16px !important;
}
.stButton > button:hover, .stFormSubmitButton > button:hover, .stDownloadButton > button:hover { border-color: #00f0ff !important; color: #00f0ff !important; background: rgba(0,240,255,0.05) !important; }

/* Expander (Inline Context) */
.streamlit-expanderHeader { background: transparent !important; color: #00f0ff !important; font-size: 11px !important; padding: 0 !important; border: none !important; }
div[data-testid="stExpander"] { background: transparent !important; border: none !important; margin-top: 8px; }
div[data-testid="stExpander"] > div:last-child { border: none !important; border-left: 1px dashed #1a1a1a !important; padding-left: 1rem !important; margin-left: 0.5rem !important; }

/* Chat */
[data-testid="stChatMessage"] { background: transparent !important; border: none !important; padding: 1rem 0 !important; }
[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] { color: #d0d0d0 !important; font-size: 13px !important; line-height: 1.6 !important; }
[data-testid="stChatMessage"] [data-testid="stIconContainer"] { display: none !important; } /* Hide default chat icons to look cleaner */

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

def _api_get_text(path: str, **params) -> str | None:
    try:
        r = httpx.get(f"{API_BASE_URL}{path}", params=params, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        return r.text
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
# Layout: Chatbot Demo (Left) & OS Features Panel (Right)
# ═══════════════════════════════════════════════════════════════════════════════

col_demo, col_os = st.columns([1, 1.4], gap="large")

# ─── 1. Chatbot Demo (Left Column) ───────────────────────────────────────────
with col_demo:
    st.markdown("<div class='chat-col'>", unsafe_allow_html=True)
    st.markdown("<div style='font-size:14px; font-weight:700; color:#fff; text-transform:uppercase; letter-spacing:0.1em; margin-bottom:4px;'>Live Chatbot Demo</div>", unsafe_allow_html=True)
    st.markdown("<div style='font-size:11px; color:#666; margin-bottom:1.5rem;'>The agent interacts with the OS via FastAPI.</div>", unsafe_allow_html=True)

    chat_container = st.container(height=460, border=False)
    
    with chat_container:
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                
                # Show memory context inline
                if msg.get("retrieved"):
                    with st.expander(f"🧠 {len(msg['retrieved'])} memories retrieved"):
                        for m in msg["retrieved"]:
                            render_memory_card(m)
                
                if msg.get("extracted"):
                    with st.expander(f"⚡ {len(msg['extracted'])} new memories stored"):
                        for m in msg["extracted"]:
                            render_memory_card(m)

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
                                with st.expander(f"🧠 {len(retrieved)} memories retrieved"):
                                    for m in retrieved:
                                        render_memory_card(m)
                                        
                            st.session_state.messages.append({"role": "assistant", "content": answer, "retrieved": retrieved, "extracted": []})
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
                        st.markdown(demo_resp["text"])
                        with st.expander(f"🧠 {len(demo_resp['retrieved'])} memories retrieved"):
                            for m in demo_resp["retrieved"]:
                                render_memory_card(m)
                                
                        st.session_state.messages.append({"role": "assistant", "content": demo_resp["text"], "retrieved": demo_resp["retrieved"], "extracted": []})
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


# ─── 2. OS Panel / Features (Right Column) ───────────────────────────────────
with col_os:
    st.markdown("<div class='os-col'>", unsafe_allow_html=True)
    
    # OS Header
    st.markdown("""
    <div class="os-logo-name"><div class="os-dot"></div>Bullet Memory OS</div>
    <div class="os-tagline">Semantic Memory Engine for LLM Agents</div>
    """, unsafe_allow_html=True)

    if st.session_state.backend_ok:
        st.markdown("<div class='os-status os-live'>● API: ONLINE</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='os-status'>○ API: DEMO MODE</div>", unsafe_allow_html=True)

    # OS Features via Tabs
    tab_overview, tab_vault, tab_ingest, tab_export = st.tabs(["Overview", "Memory Vault", "Manual Ingest", "Dataset Export"])

    # ── Tab 1: Overview
    with tab_overview:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("<div style='font-size:12px; color:#00f0ff; font-weight:700; margin-bottom:4px;'>Architecture</div>", unsafe_allow_html=True)
        st.code("""Frontend : Streamlit (:8501)
Backend  : FastAPI (:8000)
Vector   : ChromaDB (:8001)
Storage  : SQLite Async (Relational metadata)
Model    : Ollama (LLM + Embeddings)""", language="text")

        st.markdown("<div style='font-size:12px; color:#00f0ff; font-weight:700; margin-top:20px; margin-bottom:4px;'>The Pipeline</div>", unsafe_allow_html=True)
        st.markdown("""
        <div style="font-size:12px; color:#888; line-height:1.6;">
        <b>1. Semantic Retrieval:</b> Queries ChromaDB for relevant facts before the LLM replies.<br>
        <b>2. Auto-Extraction:</b> Background tasks distill raw chat into structured facts.<br>
        <b>3. Deduplication:</b> Cosine similarity checks prevent vector pollution.<br>
        </div>
        """, unsafe_allow_html=True)

    # ── Tab 2: Memory Vault
    with tab_vault:
        st.markdown("<br>", unsafe_allow_html=True)
        cat_f = st.selectbox("Filter Category", ["All", "PREFERENCE", "SKILL", "GOAL", "FACT", "TOOL_RESULT", "INSTRUCTION"])
        
        # Load memories
        if st.session_state.backend_ok:
            params = {"user_id": DEMO_USER_ID}
            if cat_f != "All": params["category"] = cat_f
            data = _api_get(f"/memories/{DEMO_USER_ID}", **params)
            mems = data.get("memories", []) if data else []
        else:
            mems = list(DEMO_MEMORIES)
            if cat_f != "All": mems = [m for m in mems if m["category"] == cat_f]

        if not mems:
            st.info("No memories found.")
        else:
            st.caption(f"Showing {len(mems)} memory records")
            with st.container(height=380, border=False):
                for m in sorted(mems, key=lambda x: x.get("importance", 0), reverse=True):
                    render_memory_card(m)

    # ── Tab 3: Manual Ingest
    with tab_ingest:
        st.markdown("<br>", unsafe_allow_html=True)
        st.caption("Paste raw text below. The backend pipeline will extract and deduplicate facts automatically.")
        with st.form("ingest_form"):
            raw_text = st.text_area("Raw Text (logs, notes, transcripts)", height=150)
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            col_s, col_sub = st.columns([2, 1])
            with col_s:
                source_type = st.selectbox("Source Type", ["manual", "api_ingest", "agent_event", "chat"])
            with col_sub:
                st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
                submitted = st.form_submit_button("Extract & Store", use_container_width=True)

            if submitted:
                if not raw_text.strip():
                    st.warning("Provide text.")
                elif not st.session_state.backend_ok:
                    st.info("Demo Mode: Backend unreachable.")
                else:
                    with st.spinner("Extracting..."):
                        res = _api_post("/ingest/raw", {"user_id": DEMO_USER_ID, "text": raw_text, "source_type": source_type, "tags": []})
                        if res:
                            st.success(f"{res.get('memories_stored', 0)} memories stored.")
                        else:
                            st.error("Ingest failed.")

    # ── Tab 4: Dataset Export (Fine-Tuning)
    with tab_export:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("<div style='font-size:12px; color:#888; margin-bottom:12px;'>Export the Memory Vault as a JSONL dataset for model fine-tuning.</div>", unsafe_allow_html=True)
        
        format_type = st.selectbox("Format", ["openai", "instruction", "jsonl"])
        min_imp = st.slider("Minimum Importance Threshold", 0.0, 1.0, 0.5, 0.05)
        
        if st.session_state.backend_ok:
            dl_data = _api_get_text(f"/export/{DEMO_USER_ID}", format=format_type, min_importance=min_imp)
        else:
            # Fake JSONL data for demo mode
            dl_data = ""
            for m in DEMO_MEMORIES:
                if m["importance"] >= min_imp:
                    if format_type == "openai":
                        dl_data += json.dumps({"messages": [{"role": "system", "content": "You are a memory agent."}, {"role": "user", "content": "What is a fact?"}, {"role": "assistant", "content": m["content"]}]}) + "\n"
                    else:
                        dl_data += json.dumps(m) + "\n"
        
        st.markdown("<br>", unsafe_allow_html=True)
        if dl_data:
            st.download_button(
                label=f"Download {format_type.upper()} Dataset",
                data=dl_data,
                file_name=f"bullet_memory_dataset_{format_type}.jsonl",
                mime="application/x-ndjson"
            )
        else:
            st.warning("No data meets the criteria or backend is unreachable.")

    st.markdown("</div>", unsafe_allow_html=True)
