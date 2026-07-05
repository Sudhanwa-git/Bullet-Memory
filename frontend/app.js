const USER_ID = "test-user-01";
const API_BASE = "http://localhost:8000";

// DOM Elements
const chatForm = document.getElementById('chat-form');
const messageInput = document.getElementById('message-input');
const sendButton = document.getElementById('send-button');
const chatHistory = document.getElementById('chat-history');
const memoryGrid = document.getElementById('memory-grid');
const refreshBtn = document.getElementById('refresh-memories');
const vaultFilter = document.getElementById('vault-filter-category');

const metricLatency = document.getElementById('metric-latency');
const metricRetrieved = document.getElementById('metric-retrieved');
const metricStored = document.getElementById('metric-stored');
const consoleLog = document.getElementById('pipeline-console');

// Pipeline Nodes
const nodes = {
    retrieve: document.getElementById('node-retrieve'),
    llm: document.getElementById('node-llm'),
    extract: document.getElementById('node-extract'),
    score: document.getElementById('node-score'),
    store: document.getElementById('node-store')
};
const edges = {
    1: document.getElementById('edge-1'),
    2: document.getElementById('edge-2'),
    3: document.getElementById('edge-3'),
    4: document.getElementById('edge-4')
};

// Ingest panel
const ingestBtn = document.getElementById('ingest-btn');
const ingestDirectBtn = document.getElementById('ingest-direct-btn');
const exportBtn = document.getElementById('export-btn');
const ingestResult = document.getElementById('ingest-result');

// ── Utils ─────────────────────────────────────────────────────────────────────
const sleep = ms => new Promise(r => setTimeout(r, ms));

function logConsole(msg, type = '') {
    const line = document.createElement('div');
    line.className = 'log-line';
    const ts = new Date().toISOString().split('T')[1].slice(0, 12);
    let content = `<span style="color:#2d3748">[${ts}]</span> `;
    if (type === 'highlight') content += `<span class="highlight">${msg}</span>`;
    else if (type === 'success') content += `<span class="success">${msg}</span>`;
    else if (type === 'accent') content += `<span class="accent">${msg}</span>`;
    else content += msg;
    line.innerHTML = content;
    consoleLog.appendChild(line);
    consoleLog.scrollTop = consoleLog.scrollHeight;
}

function resetPipeline() {
    Object.values(nodes).forEach(n => n.className = 'node');
    Object.values(edges).forEach(e => e.className = 'edge');
}

async function startForegroundPipeline() {
    resetPipeline();
    nodes.retrieve.classList.add('active');
    logConsole('Retrieval sequence initiated...');
    await sleep(200);
    nodes.retrieve.classList.remove('active');
    nodes.retrieve.classList.add('success');
    edges[1].classList.add('active');
    nodes.llm.classList.add('active');
    logConsole('Context injected. Streaming from LLM...', 'accent');
}

async function runBackgroundVisualizer() {
    nodes.extract.classList.add('active');
    logConsole('[BG] Memory extractor running...');
    await sleep(4500);
    nodes.extract.classList.remove('active');
    nodes.extract.classList.add('success');
    edges[3].classList.add('active');
    nodes.score.classList.add('active');
    logConsole('[BG] Importance scorer evaluating candidates (threshold: 0.6)...');
    await sleep(2000);
    nodes.score.classList.remove('active');
    nodes.score.classList.add('success');
    edges[4].classList.add('active');
    nodes.store.classList.add('active');
    logConsole('[BG] Embedding and persisting to Vector Vault...');
    await sleep(2000);
    nodes.store.classList.remove('active');
    nodes.store.classList.add('success');
    logConsole('[BG] Extraction pipeline complete.', 'success');
    setTimeout(() => {
        logConsole('> ENGINE IDLE');
        resetPipeline();
    }, 4000);
}

// ── Tab Switching ─────────────────────────────────────────────────────────────
function switchTab(tab) {
    document.getElementById('view-chat').classList.toggle('hidden', tab !== 'chat');
    document.getElementById('view-ingest').classList.toggle('hidden', tab !== 'ingest');
    document.getElementById('tab-chat').classList.toggle('active', tab === 'chat');
    document.getElementById('tab-ingest').classList.toggle('active', tab === 'ingest');
}

// ── Chat (Streaming) ──────────────────────────────────────────────────────────
function appendUserMessage(text) {
    const div = document.createElement('div');
    div.className = 'message user';
    div.innerHTML = `<div class="message-content">${text}</div>`;
    chatHistory.appendChild(div);
    chatHistory.scrollTop = chatHistory.scrollHeight;
}

chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const text = messageInput.value.trim();
    if (!text) return;

    appendUserMessage(text);
    messageInput.value = '';
    messageInput.disabled = true;
    sendButton.disabled = true;

    const startTime = performance.now();
    startForegroundPipeline();

    try {
        const response = await fetch(`${API_BASE}/chat/stream`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: USER_ID, message: text })
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const reader = response.body.getReader();
        const decoder = new TextDecoder('utf-8');

        // Create agent message bubble
        const msgDiv = document.createElement('div');
        msgDiv.className = 'message system';
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        msgDiv.appendChild(contentDiv);
        chatHistory.appendChild(msgDiv);

        let textSpan = null;
        let isFirstToken = true;
        let ttft = 0;
        let buffer = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const parts = buffer.split('\n');
            buffer = parts.pop() || '';

            for (const line of parts) {
                if (!line.startsWith('data: ')) continue;
                try {
                    const payload = JSON.parse(line.substring(6));

                    if (payload.type === 'context') {
                        const ctx = payload.data || [];
                        metricRetrieved.textContent = ctx.length;

                        let html = `<div style="font-size:0.6rem;color:var(--text-dim);margin-bottom:0.4rem">[AGENT]</div>`;
                        if (ctx.length > 0) {
                            html += `<div style="margin-bottom:0.75rem;padding:0.6rem;background:var(--accent-dim);border:1px solid var(--accent);border-radius:3px">`;
                            html += `<div style="font-size:0.6rem;color:var(--accent);margin-bottom:0.4rem;letter-spacing:0.08em">[RETRIEVED CONTEXT — ${ctx.length} memories]</div>`;
                            ctx.forEach(c => {
                                html += `<div style="font-size:0.75rem;color:var(--text-main);margin-bottom:0.2rem">• <span style="color:var(--accent)">[${c.category}]</span> ${c.content}</div>`;
                            });
                            html += `</div>`;
                            logConsole(`Retrieved ${ctx.length} memories from vault.`, 'accent');
                        }
                        html += `<span class="agent-text"></span>`;
                        contentDiv.innerHTML = html;
                        textSpan = contentDiv.querySelector('.agent-text');

                        nodes.retrieve.classList.remove('active');
                        nodes.retrieve.classList.add('success');
                        edges[1].classList.add('active');
                        nodes.llm.classList.add('active');

                    } else if (payload.type === 'token') {
                        if (isFirstToken) {
                            ttft = (performance.now() - startTime) / 1000;
                            metricLatency.textContent = `${ttft.toFixed(2)}s`;
                            isFirstToken = false;
                        }
                        if (textSpan) {
                            textSpan.textContent += payload.data;
                            chatHistory.scrollTop = chatHistory.scrollHeight;
                        }
                    }
                } catch (_) { /* malformed line, skip */ }
            }
        }

        nodes.llm.classList.remove('active');
        nodes.llm.classList.add('success');
        edges[2].classList.add('active');
        const total = (performance.now() - startTime) / 1000;
        logConsole(`Stream done. TTFT: ${ttft.toFixed(2)}s | Total: ${total.toFixed(2)}s`, 'success');
        metricStored.textContent = '⟳';
        runBackgroundVisualizer();

    } catch (err) {
        logConsole(`ERROR: ${err.message}`, 'highlight');
        const div = document.createElement('div');
        div.className = 'message system';
        div.innerHTML = `<div class="message-content" style="color:#ff4444">ERR: ${err.message}</div>`;
        chatHistory.appendChild(div);
        resetPipeline();
    } finally {
        messageInput.disabled = false;
        sendButton.disabled = false;
        messageInput.focus();
    }
});

// ── Ingest Panel ──────────────────────────────────────────────────────────────
function showIngestResult(msg, type = 'success') {
    ingestResult.textContent = msg;
    ingestResult.className = `ingest-result ${type}`;
}

ingestBtn.addEventListener('click', async () => {
    const text = document.getElementById('ingest-text').value.trim();
    if (!text) return;
    ingestBtn.disabled = true;
    ingestBtn.textContent = 'EXTRACTING...';
    showIngestResult('Processing...', '');

    const payload = {
        user_id: USER_ID,
        text,
        source_type: document.getElementById('ingest-source-type').value,
        agent_id: document.getElementById('ingest-agent-id').value || null,
        session_id: document.getElementById('ingest-session-id').value || null,
        tags: document.getElementById('ingest-tags').value.split(',').map(t => t.trim()).filter(Boolean),
    };

    try {
        logConsole(`[INGEST] Extracting from ${text.length} chars...`, 'accent');
        const resp = await fetch(`${API_BASE}/ingest/raw/sync`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        const data = await resp.json();
        const stored = data.memories_stored || 0;
        showIngestResult(`✓ Extraction complete. ${stored} memories stored.`, 'success');
        logConsole(`[INGEST] Done. ${stored} memories extracted and stored.`, 'success');
        fetchMemories();
    } catch (err) {
        showIngestResult(`✗ Error: ${err.message}`, 'error');
    } finally {
        ingestBtn.disabled = false;
        ingestBtn.textContent = 'EXTRACT & STORE';
    }
});

ingestDirectBtn.addEventListener('click', async () => {
    const text = document.getElementById('ingest-text').value.trim();
    if (!text) return;
    ingestDirectBtn.disabled = true;

    const payload = {
        user_id: USER_ID,
        content: text,
        source_type: document.getElementById('ingest-source-type').value,
        importance: 0.8,
        agent_id: document.getElementById('ingest-agent-id').value || null,
        session_id: document.getElementById('ingest-session-id').value || null,
        tags: document.getElementById('ingest-tags').value.split(',').map(t => t.trim()).filter(Boolean),
    };

    try {
        const resp = await fetch(`${API_BASE}/ingest/direct`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        const data = await resp.json();
        showIngestResult(`✓ Directly stored: ${data.memory_id}`, 'success');
        fetchMemories();
    } catch (err) {
        showIngestResult(`✗ Error: ${err.message}`, 'error');
    } finally {
        ingestDirectBtn.disabled = false;
    }
});

exportBtn.addEventListener('click', async (e) => {
    e.preventDefault();
    try {
        const resp = await fetch(`${API_BASE}/memories/export/${USER_ID}?format=openai&min_importance=0.6`);
        const text = await resp.text();
        const blob = new Blob([text], { type: 'application/x-ndjson' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `bullet_memory_${USER_ID}_openai.jsonl`;
        a.click();
        URL.revokeObjectURL(url);
        logConsole('Fine-tuning dataset exported as JSONL.', 'success');
    } catch (err) {
        logConsole(`Export failed: ${err.message}`, 'highlight');
    }
});

// ── Memory Vault ──────────────────────────────────────────────────────────────
async function fetchMemories() {
    const cat = vaultFilter.value;
    let url = `${API_BASE}/memories/${USER_ID}`;
    if (cat) url += `?category=${cat}`;
    try {
        const resp = await fetch(url);
        if (!resp.ok) return;
        const data = await resp.json();
        renderMemories(data.memories || []);
    } catch (_) {}
}

function renderMemories(memories) {
    metricStored.textContent = memories.length;
    memoryGrid.innerHTML = '';
    if (memories.length === 0) {
        memoryGrid.innerHTML = '<div class="empty-state">VAULT EMPTY</div>';
        return;
    }
    memories.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
    memories.forEach(mem => {
        const node = document.createElement('div');
        const srcClass = mem.source_type === 'agent_event' ? 'source-agent'
            : mem.source_type === 'manual' ? 'source-manual' : '';
        node.className = `memory-node ${srcClass}`;
        const tagsHtml = (mem.tags || []).length > 0
            ? `<div class="node-tags">${mem.tags.map(t => `<span class="node-tag">${t}</span>`).join('')}</div>`
            : '';
        node.innerHTML = `
            <div class="node-meta">
                <span class="node-cat">${mem.category.toUpperCase()}</span>
                <span class="node-source">${mem.source_type}</span>
                <span class="node-imp">IMP: ${(mem.importance * 100).toFixed(0)}%</span>
                <span class="node-access">↑${mem.access_count || 0}</span>
            </div>
            <div class="node-content">${mem.content}</div>
            ${tagsHtml}
        `;
        memoryGrid.appendChild(node);
    });
}

vaultFilter.addEventListener('change', fetchMemories);
refreshBtn.addEventListener('click', fetchMemories);
setInterval(fetchMemories, 3000);
fetchMemories();
