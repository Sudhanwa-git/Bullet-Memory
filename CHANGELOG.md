# Changelog

All notable changes to Bullet Memory OS will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- **Working Memory Engine** (`app/memory/working_memory.py`): Ephemeral execution state with crash recovery via SQLite checkpointing
- **Episode Engine** (`app/memory/episodes.py`): Records every agent run as a complete, replayable timeline
- **Reflection Engine** (`app/memory/episodes.py`): LLM-powered background analysis of completed episodes to extract lessons
- **Prediction Engine** (`app/memory/prediction.py`): Proactive background pre-fetching daemon that pre-warms the SemanticCache
- **Context Builder** (`app/memory/context_builder.py`): Token-aware prompt packing to prevent context bloat at scale
- **Working Memory API** (`app/api/working_memory.py`): Full REST API for agent session management
- **ARCHITECTURE.md**: Complete Cognitive OS design vision document
- **Makefile**: Developer workflow shortcuts (`make test`, `make lint`, `make format`)
- **`.pre-commit-config.yaml`**: Automated code quality enforcement via ruff
- **GitHub Actions CI** (`.github/workflows/ci.yml`): Automated testing and linting on every push
- **Dependabot** (`.github/dependabot.yml`): Weekly automated dependency updates
- **MIT License**, **SECURITY.md**, **CONTRIBUTING.md**: Open-source project hygiene
- **`.editorconfig`**, **`.dockerignore`**: Developer experience and Docker build optimization

### Changed
- **SQLite WAL mode**: Enabled Write-Ahead Logging and `synchronous=NORMAL` for 3–5x faster concurrent I/O
- **FastAPI**: Switched to `ORJSONResponse` (Rust-based JSON serialization) for all endpoints
- **Streamlit**: Replaced per-request HTTP connections with `@st.cache_resource` connection pool
- **Memory Package**: Added proper `__all__` exports and cleaned up circular import risk

### Performance
- Retrieval latency reduced from ~200ms+ to ~1ms on cache hits (Prediction Engine + SemanticCache)
- JSON serialization ~10x faster across all API responses (orjson)
- Database write throughput significantly improved (WAL mode)
- Prompt construction is now token-budget-aware (no more unbounded context injection)

---

## [0.1.0] — 2026-07-04

### Added
- Initial release of Bullet Memory OS
- Semantic Memory Engine with structured knowledge extraction
- Multi-Hop Graph RAG with SQLite node/edge storage
- Batch Embedding Pipeline
- Background Memory Consolidation with LLM deduplication
- Semantic Caching via ChromaDB
- Hybrid retrieval (semantic + lexical + time-decay re-ranking)
- Fine-tuning dataset export (OpenAI, instruction, JSONL formats)
- Dataset curation UI in Streamlit
- Docker Compose deployment stack
