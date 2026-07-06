import streamlit as st
import httpx
import json

# Constants
API_BASE_URL = "http://localhost:8000"
USER_ID = "demo-user"

# Setup page config
st.set_page_config(
    page_title="Bullet Memory /// OS",
    page_icon="🔌",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state for chat
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "[SYSTEM] Bullet Memory Engine v1.0 initialized. Memory is persistent across sessions."}
    ]

# Header
st.markdown("## BULLET MEMORY `<OS DASHBOARD v1.0>`")
st.markdown("---")

# Tabs
tab1, tab2, tab3 = st.tabs(["01. AGENT TERMINAL", "02. INGEST PANEL", "03. MEMORY VAULT"])

with tab1:
    st.markdown("#### /chat")
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input
    if prompt := st.chat_input("Transmit data to agent..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Processing..."):
                try:
                    response = httpx.post(
                        f"{API_BASE_URL}/chat",
                        json={"user_id": USER_ID, "message": prompt},
                        timeout=30.0
                    )
                    response.raise_for_status()
                    data = response.json()
                    answer = data.get("response", "Error: No response generated.")
                    
                    st.markdown(answer)
                    st.session_state.messages.append({"role": "assistant", "content": answer})
                    
                    # Optional: display retrieved metadata
                    if data.get("memories_retrieved", 0) > 0:
                        st.caption(f"[SYSTEM] Retrieved {data['memories_retrieved']} memories in {data.get('latency_ms', 0):.2f}ms")
                        
                except Exception as e:
                    st.error(f"Engine connection failed: {e}")

with tab2:
    st.markdown("#### /ingest")
    st.markdown("Extract durable facts and observations manually.")
    
    with st.form("ingest_form"):
        raw_text = st.text_area("RAW TEXT TO EXTRACT FROM", height=200, placeholder="Paste any text — agent outputs, documents, observations, reflections...")
        
        col1, col2 = st.columns(2)
        with col1:
            source_type = st.selectbox("SOURCE TYPE", ["api_ingest", "agent_event", "observation", "manual"])
            tags_input = st.text_input("TAGS (comma-separated)", placeholder="career, python, goals")
        with col2:
            agent_id = st.text_input("AGENT ID (optional)", placeholder="my-agent-v1")
            session_id = st.text_input("SESSION ID (optional)", placeholder="session-001")
            
        submitted = st.form_submit_button("EXTRACT & STORE")
        
        if submitted and raw_text:
            with st.spinner("Extracting..."):
                tags = [t.strip() for t in tags_input.split(",")] if tags_input else []
                payload = {
                    "user_id": USER_ID,
                    "text": raw_text,
                    "source_type": source_type,
                    "agent_id": agent_id if agent_id else None,
                    "session_id": session_id if session_id else None,
                    "tags": tags
                }
                
                try:
                    res = httpx.post(f"{API_BASE_URL}/ingest/raw", json=payload, timeout=60.0)
                    res.raise_for_status()
                    st.success(f"Success! {res.json().get('memories_stored', 0)} memories extracted and stored.")
                except Exception as e:
                    st.error(f"Ingest failed: {e}")

with tab3:
    st.markdown("#### /vault")
    
    col_a, col_b = st.columns([3, 1])
    with col_a:
        st.write("Browse persistent semantic memory.")
    with col_b:
        if st.button("SYNC / REFRESH"):
            st.rerun()
            
    st.markdown("---")
    
    try:
        res = httpx.get(f"{API_BASE_URL}/memory", params={"user_id": USER_ID}, timeout=10.0)
        res.raise_for_status()
        memories = res.json()
        
        if not memories:
            st.info("VAULT EMPTY")
        else:
            for mem in memories:
                with st.expander(f"{mem['category']} | Confidence: {mem['confidence']} | Importance: {mem['importance']}"):
                    st.write(mem["content"])
                    st.caption(f"ID: {mem['id']} | Source: {mem['source_type']} | Accessed: {mem['metadata'].get('access_count', 0)} times")
                    if mem.get("tags"):
                        st.caption(f"Tags: {', '.join(mem['tags'])}")
    except Exception as e:
        st.error(f"Failed to load vault: {e}")
