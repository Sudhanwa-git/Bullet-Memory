# Bullet Memory

**A lightweight, production-oriented semantic memory engine for LLM agents.**

Bullet Memory sits between your application and an LLM, automatically retrieving relevant knowledge before inference and learning new knowledge after inference.

---

## What It Does

Traditional LLMs are stateless — every request starts from zero context.

Bullet Memory introduces a **persistent semantic memory layer** that continuously learns structured knowledge from conversations.

```
User: "I've been building AI infrastructure with Python and FastAPI."
↓
Stored Memory:
  Category:   Skills
  Content:    Experienced with Python and FastAPI
  Importance: 0.9
  Confidence: 0.95
```

The system remembers **knowledge**, not chat history.

---

## Architecture

```
Client Application
       │
       ▼
 FastAPI Endpoints
       │
       ▼
Memory Orchestrator
       │
  ┌────┴────────────────┐
  ▼                     ▼
Memory Service      LLM Provider
  │
  ├── Extractor     ← converts text → structured facts
  ├── Scorer        ← filters by importance threshold
  ├── Embedder      ← generates vector representations
  ├── Retriever     ← semantic similarity search
  └── Updater       ← deduplicates / merges conflicts
       │
       ▼
 SQLite + ChromaDB
```

---

## Quick Start

### 1. Install

```bash
pip install -e ".[dev]"
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env — at minimum, set your OPENAI_API_KEY
```

### 3. Run

```bash
uvicorn app.main:app --reload
```

The API is now available at `http://localhost:8000`.  
Interactive docs: `http://localhost:8000/docs`

---

## API Reference

### Chat (memory-augmented)

```http
POST /chat
Content-Type: application/json

{
  "user_id": "alice",
  "message": "What programming languages do I know?",
  "system_prompt": null
}
```

**Response:**
```json
{
  "response": "Based on what I know about you, you're experienced with Python and FastAPI...",
  "memories_retrieved": 3,
  "memories_stored": 1,
  "latency_ms": 1240.5
}
```

---

### List Memories

```http
GET /memories/{user_id}
```

### Get Single Memory

```http
GET /memories/detail/{memory_id}
```

### Delete Memory

```http
DELETE /memories/{memory_id}
```

### Semantic Search

```http
POST /memories/search
Content-Type: application/json

{
  "user_id": "alice",
  "query": "programming skills",
  "top_k": 5
}
```

### Health Check

```http
GET /health
```

### Active Configuration

```http
GET /config
```

---

## Folder Structure

```
bullet-memory/
├── app/
│   ├── api/
│   │   ├── chat.py          # POST /chat endpoint
│   │   ├── memory.py        # Memory CRUD + search endpoints
│   │   ├── router.py        # Root router + health/config
│   │   └── deps.py          # FastAPI dependency injection
│   │
│   ├── core/
│   │   ├── orchestrator.py  # Request lifecycle coordinator
│   │   ├── config.py        # Pydantic-settings configuration
│   │   ├── logging.py       # Structlog setup
│   │   └── prompts.py       # All LLM prompt templates
│   │
│   ├── memory/
│   │   ├── service.py       # MemoryService facade (entry point)
│   │   ├── extractor.py     # Conversation → structured facts
│   │   ├── scorer.py        # Importance threshold filter
│   │   ├── embeddings.py    # Embedding generation wrapper
│   │   ├── retriever.py     # Vector similarity search
│   │   ├── updater.py       # Deduplication + conflict resolution
│   │   └── models.py        # Canonical Pydantic models
│   │
│   ├── adapters/
│   │   ├── llm.py           # LLM provider (OpenAI + interface)
│   │   ├── embedding.py     # Embedding provider (OpenAI + interface)
│   │   ├── database.py      # SQLite via SQLAlchemy (async)
│   │   └── vector.py        # ChromaDB + in-memory implementations
│   │
│   ├── utils/
│   │   └── helpers.py
│   │
│   └── main.py              # FastAPI app factory
│
├── tests/
│   ├── test_scorer.py
│   ├── test_extractor.py
│   └── test_vector_store.py
│
├── examples/
│   └── basic_chat.py
│
├── pyproject.toml
├── .env.example
├── Dockerfile
└── docker-compose.yml
```

---

## Configuration

All configuration is through environment variables (or `.env`):

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | — | Required for OpenAI LLM + embeddings |
| `LLM_PROVIDER` | `openai` | LLM backend |
| `LLM_MODEL` | `gpt-4o-mini` | Model name |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | Embedding model |
| `IMPORTANCE_THRESHOLD` | `0.4` | Minimum importance to persist (0–1) |
| `SIMILARITY_THRESHOLD` | `0.75` | Minimum similarity to retrieve (0–1) |
| `TOP_K_RETRIEVAL` | `5` | Max memories retrieved per request |
| `VECTOR_STORE_PROVIDER` | `chroma` | `chroma` or `in_memory` |
| `DATABASE_URL` | SQLite | SQLAlchemy async connection string |
| `LOG_LEVEL` | `INFO` | `DEBUG` / `INFO` / `WARNING` |

---

## Memory Lifecycle

```
Conversation Turn
      ↓
  Extraction (LLM-powered)
      ↓
  Importance Scoring (threshold filter)
      ↓
  Embedding Generation
      ↓
  Duplicate Detection (cosine ≥ 0.90 → merge)
      ↓
  Persistence (SQLite + ChromaDB)
      ↓
  Semantic Retrieval (next request)
      ↓
  Prompt Enrichment
      ↓
  LLM Inference
```

---

## Memory Categories

`Skills` · `Preferences` · `Goals` · `Projects` · `Interests` · `Career` · `PersonalFacts` · `Relationships` · `Habits` · `Learning` · `Technologies` · `ImportantEvents`

---

## Running Tests

```bash
pytest tests/ -v
```

---

## Docker

```bash
docker-compose up --build
```

---

## Adding New Providers

All providers implement a simple abstract interface:

- **LLM**: Implement `LLMAdapter` in `app/adapters/llm.py`, register in `get_llm_adapter()`
- **Embeddings**: Implement `EmbeddingAdapter` in `app/adapters/embedding.py`
- **Vector Store**: Implement `VectorStoreAdapter` in `app/adapters/vector.py`

No other files need to change.

---

## MVP Scope

**Included:** REST API · Memory extraction · Importance scoring · Embedding generation · SQLite persistence · ChromaDB vector search · Prompt enrichment · Deduplication · Configurable providers · Structured logging

**Deferred:** Memory compression · Decay · Reflection · Summarization · Knowledge graphs · Multi-tenancy · Streaming · Caching

---

## License

MIT
