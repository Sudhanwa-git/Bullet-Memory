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
    page_title="Bullet Memory — Semantic Memory Engine",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    .stApp { background: #0a0a0f; }

    /* Hide default Streamlit header */
    header[data-testid="stHeader"] { display: none; }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f0f1a 0%, #0a0a12 100%);
        border-right: 1px solid rgba(99,102,241,0.2);
    }

    /* Cards */
    .mem-card {
        background: linear-gradient(135deg, #13131f 0%, #0f0f1a 100%);
        border: 1px solid rgba(99,102,241,0.25);
        border-radius: 12px;
        padding: 16px 20px;
        margin-bottom: 12px;
        transition: border-color 0.2s ease;
    }
    .mem-card:hover { border-color: rgba(99,102,241,0.6); }

    .mem-category {
        font-family: 'JetBrains Mono', monospace;
        font-size: 11px;
        font-weight: 500;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        padding: 3px 8px;
        border-radius: 4px;
        display: inline-block;
        margin-bottom: 8px;
    }

    .cat-PREFERENCE  { background: rgba(99,102,241,0.15); color: #818cf8; border: 1px solid rgba(99,102,241,0.3); }
    .cat-SKILL       { background: rgba(34,197,94,0.1);   color: #4ade80; border: 1px solid rgba(34,197,94,0.25); }
    .cat-GOAL        { background: rgba(251,191,36,0.1);  color: #fbbf24; border: 1px solid rgba(251,191,36,0.25); }
    .cat-FACT        { background: rgba(56,189,248,0.1);  color: #38bdf8; border: 1px solid rgba(56,189,248,0.25); }
    .cat-TOOL_RESULT { background: rgba(168,85,247,0.1);  color: #c084fc; border: 1px solid rgba(168,85,247,0.25); }
    .cat-INSTRUCTION { background: rgba(251,113,133,0.1); color: #fb7185; border: 1px solid rgba(251,113,133,0.25); }
    .cat-default     { background: rgba(100,116,139,0.1); color: #94a3b8; border: 1px solid rgba(100,116,139,0.25); }

    .mem-content { color: #e2e8f0; font-size: 14px; line-height: 1.6; margin: 6px 0; }
    .mem-meta    { color: #64748b; font-size: 12px; font-family: 'JetBrains Mono', monospace; }

    .badge {
        display: inline-block;
        background: rgba(99,102,241,0.1);
        color: #6366f1;
        border: 1px solid rgba(99,102,241,0.2);
        border-radius: 20px;
        padding: 2px 10px;
        font-size: 11px;
        margin-right: 4px;
        font-family: 'JetBrains Mono', monospace;
    }

    .stat-card {
        background: linear-gradient(135deg, #13131f, #0f0f1a);
        border: 1px solid rgba(99,102,241,0.2);
        border-radius: 12px;
        padding: 20px;
        text-align: center;
    }
    .stat-num  { font-size: 32px; font-weight: 700; color: #818cf8; }
    .stat-lbl  { font-size: 12px; color: #64748b; text-transform: uppercase; letter-spacing: 0.1em; margin-top: 4px; }

    .demo-banner {
        background: linear-gradient(90deg, rgba(251,191,36,0.08), rgba(251,191,36,0.02));
        border: 1px solid rgba(251,191,36,0.3);
        border-radius: 8px;
        padding: 10px 16px;
        color: #fbbf24;
        font-size: 13px;
        margin-bottom: 16px;
    }
    .live-banner {
        background: linear-gradient(90deg, rgba(34,197,94,0.08), rgba(34,197,94,0.02));
        border: 1px solid rgba(34,197,94,0.3);
        border-radius: 8px;
        padding: 10px 16px;
        color: #4ade80;
        font-size: 13px;
        margin-bottom: 16px;
    }

    /* Override Streamlit button */
    .stButton > button {
        background: linear-gradient(135deg, #6366f1, #4f46e5);
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: 500;
        transition: opacity 0.2s;
    }
    .stButton > button:hover { opacity: 0.88; border: none; }

    /* Chat */
    [data-testid="stChatMessage"] {
        background: rgba(15,15,26,0.8);
        border-radius: 12px;
        border: 1px solid rgba(99,102,241,0.15);
        padding: 4px 8px;
    }

    /* Section titles */
    .section-title {
        font-family: 'JetBrains Mono', monospace;
        font-size: 11px;
        font-weight: 500;
        letter-spacing: 0.15em;
        text-transform: uppercase;
        color: #6366f1;
        margin-bottom: 16px;
        padding-bottom: 8px;
        border-bottom: 1px solid rgba(99,102,241,0.15);
    }
</style>
""", unsafe_allow_html=True)


# ── Session state ─────────────────────────────────────────────────────────────

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": (
                "🧠 **Bullet Memory Engine** online.\n\n"
                "I have access to your persistent memory vault. Ask me anything about your "
                "stored knowledge, preferences, or goals — or just chat and I'll extract new memories automatically."
            ),
        }
    ]

if "backend_ok" not in st.session_state:
    st.session_state.backend_ok = _check_backend()


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 🧠 Bullet Memory")
    st.markdown("<div class='section-title'>Navigation</div>", unsafe_allow_html=True)

    page = st.radio(
        "Go to",
        ["💬 Agent Terminal", "📥 Ingest", "🗄️ Memory Vault", "📊 Stats"],
        label_visibility="collapsed",
    )

    st.markdown("---")
    st.markdown("<div class='section-title'>Status</div>", unsafe_allow_html=True)

    if st.session_state.backend_ok:
        st.markdown(
            "<div class='live-banner'>🟢 &nbsp;Backend connected</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            "<div class='demo-banner'>🟡 &nbsp;Demo mode — no backend</div>",
            unsafe_allow_html=True,
        )

    st.caption(f"**API:** `{API_BASE_URL}`")

    if st.button("↻ Check Backend"):
        with st.spinner("Pinging..."):
            st.session_state.backend_ok = _check_backend()
        st.rerun()

    st.markdown("---")
    st.markdown("<div class='section-title'>About</div>", unsafe_allow_html=True)
    st.markdown(
        """
        **Bullet Memory** is a semantic memory engine for LLM agents.

        - ⚡ FastAPI async backend
        - 🔍 ChromaDB vector store
        - 🤖 LLM-powered extraction
        - 📦 Fine-tune export (JSONL)

        [GitHub →](https://github.com/Sudhanwa-git/Bullet-Memory)
        """,
        unsafe_allow_html=False,
    )


# ── Helper: render a memory card ─────────────────────────────────────────────

def render_memory_card(mem: dict) -> None:
    cat = mem.get("category", "FACT")
    cat_class = f"cat-{cat}" if cat in ("PREFERENCE", "SKILL", "GOAL", "FACT", "TOOL_RESULT", "INSTRUCTION") else "cat-default"
    tags_html = "".join(f"<span class='badge'>{t}</span>" for t in (mem.get("tags") or []))
    importance = mem.get("importance", 0)
    imp_bar = "█" * int(importance * 10) + "░" * (10 - int(importance * 10))

    st.markdown(
        f"""
        <div class='mem-card'>
            <span class='mem-category {cat_class}'>{cat}</span>
            <div class='mem-content'>{mem.get("content", "")}</div>
            <div style='margin-top:8px'>{tags_html}</div>
            <div class='mem-meta' style='margin-top:10px;display:flex;gap:20px;flex-wrap:wrap;'>
                <span>⚡ <b style='color:#818cf8'>{importance:.2f}</b> importance &nbsp;{imp_bar}</span>
                <span>🎯 {mem.get('confidence', 0):.2f} conf</span>
                <span>👁 {mem.get('access_count', 0)} accesses</span>
                <span>📂 {mem.get('source_type', '—')}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: Agent Terminal
# ═══════════════════════════════════════════════════════════════════════════════

if page == "💬 Agent Terminal":
    st.markdown("## 💬 Agent Terminal")
    st.markdown("<div class='section-title'>Chat with memory-augmented agent</div>", unsafe_allow_html=True)

    if not st.session_state.backend_ok:
        st.markdown(
            "<div class='demo-banner'>🟡 Demo mode — responses are pre-scripted. Connect a backend for real LLM responses.</div>",
            unsafe_allow_html=True,
        )

    # Render history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Input
    if prompt := st.chat_input("Ask anything…"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking…"):
                if st.session_state.backend_ok:
                    t0 = time.time()
                    data = _api_post("/chat", {"user_id": DEMO_USER_ID, "message": prompt})
                    latency = (time.time() - t0) * 1000

                    if data:
                        answer = data.get("response", "No response.")
                        memories_used = data.get("memories_retrieved", 0)
                        st.markdown(answer)
                        if memories_used:
                            st.caption(f"🧠 Retrieved {memories_used} memories · ⚡ {latency:.0f}ms")
                        st.session_state.messages.append({"role": "assistant", "content": answer})
                    else:
                        err = "⚠️ Backend unreachable. Switching to demo mode."
                        st.markdown(err)
                        st.session_state.messages.append({"role": "assistant", "content": err})
                        st.session_state.backend_ok = False
                else:
                    # Demo responses
                    pl = prompt.lower()
                    if any(w in pl for w in ("what", "explain", "how", "bullet")):
                        answer = DEMO_CHAT_RESPONSES["what"]
                    elif any(w in pl for w in ("skill", "know", "proficient", "experience")):
                        answer = DEMO_CHAT_RESPONSES["skill"]
                    else:
                        answer = DEMO_CHAT_RESPONSES["default"]
                    time.sleep(0.6)  # simulate latency
                    st.markdown(answer)
                    st.session_state.messages.append({"role": "assistant", "content": answer})

    # Clear chat
    if len(st.session_state.messages) > 1:
        if st.button("🗑 Clear conversation"):
            st.session_state.messages = [st.session_state.messages[0]]
            st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: Ingest
# ═══════════════════════════════════════════════════════════════════════════════

elif page == "📥 Ingest":
    st.markdown("## 📥 Ingest Panel")
    st.markdown("<div class='section-title'>Extract and store memories from raw text</div>", unsafe_allow_html=True)

    if not st.session_state.backend_ok:
        st.markdown(
            "<div class='demo-banner'>🟡 Demo mode — ingestion is disabled. Connect a backend to extract real memories.</div>",
            unsafe_allow_html=True,
        )

    with st.form("ingest_form"):
        raw_text = st.text_area(
            "Raw text to extract from",
            height=220,
            placeholder="Paste any text — conversation logs, documents, notes, tool outputs…",
        )

        col1, col2 = st.columns(2)
        with col1:
            source_type = st.selectbox(
                "Source type",
                ["api_ingest", "chat", "agent_event", "manual"],
            )
            tags_input = st.text_input("Tags (comma-separated)", placeholder="python, goals, career")

        with col2:
            agent_id = st.text_input("Agent ID (optional)", placeholder="my-agent-v1")
            session_id = st.text_input("Session ID (optional)", placeholder="session-001")

        submitted = st.form_submit_button("🚀 Extract & Store", use_container_width=True)

        if submitted:
            if not raw_text.strip():
                st.warning("Please enter some text to ingest.")
            elif not st.session_state.backend_ok:
                st.info("🟡 Demo mode: In a live deployment, this would extract and store memories from your text using an LLM.")
            else:
                with st.spinner("Extracting memories…"):
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
                        st.success(f"✅ Extracted and stored **{n}** memories.")
                    else:
                        st.error("Ingest failed — check backend connection.")

    st.markdown("---")
    st.markdown("### How extraction works")
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.markdown("**1. LLM Extraction**\nThe text is passed to an LLM which identifies durable facts, skills, preferences, and goals.")
    with col_b:
        st.markdown("**2. Importance Scoring**\nEach candidate memory is scored for importance (0–1). Low-importance items are filtered out.")
    with col_c:
        st.markdown("**3. Deduplication**\nNew memories are embedded and compared against the vector store. Near-duplicates are merged, not duplicated.")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: Memory Vault
# ═══════════════════════════════════════════════════════════════════════════════

elif page == "🗄️ Memory Vault":
    st.markdown("## 🗄️ Memory Vault")
    st.markdown("<div class='section-title'>Browse all stored memories</div>", unsafe_allow_html=True)

    # Filters
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        cat_filter = st.selectbox("Category", ["All", "PREFERENCE", "SKILL", "GOAL", "FACT", "TOOL_RESULT", "INSTRUCTION"])
    with col2:
        src_filter = st.selectbox("Source type", ["All", "chat", "agent_event", "manual", "api_ingest"])
    with col3:
        min_imp = st.slider("Min importance", 0.0, 1.0, 0.0, 0.05)

    refresh = st.button("↻ Refresh Vault")

    st.markdown("---")

    # Load memories
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
            st.warning("Could not load memories from backend.")
            memories = []
    else:
        # Demo data with client-side filtering
        memories = DEMO_MEMORIES
        if cat_filter != "All":
            memories = [m for m in memories if m["category"] == cat_filter]
        if src_filter != "All":
            memories = [m for m in memories if m["source_type"] == src_filter]
        memories = [m for m in memories if m["importance"] >= min_imp]

        st.markdown(
            "<div class='demo-banner'>🟡 Showing demo memories. Connect a backend to see real persisted data.</div>",
            unsafe_allow_html=True,
        )

    if not memories:
        st.info("No memories found matching the current filters.")
    else:
        st.caption(f"Showing **{len(memories)}** memor{'y' if len(memories)==1 else 'ies'}")
        for mem in sorted(memories, key=lambda m: m.get("importance", 0), reverse=True):
            render_memory_card(mem)


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: Stats
# ═══════════════════════════════════════════════════════════════════════════════

elif page == "📊 Stats":
    st.markdown("## 📊 System Stats")
    st.markdown("<div class='section-title'>Memory engine overview</div>", unsafe_allow_html=True)

    if not st.session_state.backend_ok:
        st.markdown(
            "<div class='demo-banner'>🟡 Demo mode — showing example stats.</div>",
            unsafe_allow_html=True,
        )
        # Demo stats
        memories = DEMO_MEMORIES
    else:
        data = _api_get(f"/memories/{DEMO_USER_ID}")
        memories = data.get("memories", []) if data else []

    total = len(memories)
    avg_imp = sum(m.get("importance", 0) for m in memories) / total if total else 0
    total_accesses = sum(m.get("access_count", 0) for m in memories)
    categories = {}
    for m in memories:
        c = m.get("category", "UNKNOWN")
        categories[c] = categories.get(c, 0) + 1

    # Stat row
    cols = st.columns(4)
    stats = [
        (str(total), "Total Memories"),
        (f"{avg_imp:.2f}", "Avg Importance"),
        (str(total_accesses), "Total Accesses"),
        (str(len(categories)), "Categories"),
    ]
    for col, (num, lbl) in zip(cols, stats):
        with col:
            st.markdown(
                f"<div class='stat-card'><div class='stat-num'>{num}</div><div class='stat-lbl'>{lbl}</div></div>",
                unsafe_allow_html=True,
            )

    st.markdown("---")

    if categories:
        st.markdown("### Memory by Category")
        # Simple bar chart using Streamlit
        import pandas as pd

        df = pd.DataFrame(list(categories.items()), columns=["Category", "Count"])
        df = df.sort_values("Count", ascending=False)
        st.bar_chart(df.set_index("Category"), color="#6366f1")

    st.markdown("### Top Memories by Importance")
    top = sorted(memories, key=lambda m: m.get("importance", 0), reverse=True)[:3]
    for mem in top:
        render_memory_card(mem)

    st.markdown("---")
    st.markdown("### Architecture")
    st.markdown(
        """
        ```
        Streamlit UI
             │
             ▼
        FastAPI Backend  (uvicorn, async)
             │
        ┌────┴──────────┐
        │               │
        SQLite          ChromaDB
        (metadata)   (embeddings)
             │
             ▼
        OpenAI / Ollama  (LLM + embeddings)
        ```
        """
    )
