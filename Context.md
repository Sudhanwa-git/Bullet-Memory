# Bullet Memory

Bullet Memory is a lightweight, production-oriented backend service that gives Large Language Model (LLM) applications persistent semantic memory.

Its only responsibility is managing memory.

The engine sits between an application and an LLM, automatically retrieving relevant knowledge before inference and learning new knowledge after inference.

The project should feel like a reusable infrastructure component that any AI application can integrate in a few API calls.

The primary objective is clean architecture, modularity, simplicity, maintainability, and production readiness without unnecessary complexity.

---

# Core Idea

Traditional LLMs are stateless.

Every request starts from zero context.

Memory Engine introduces a persistent semantic memory layer that continuously learns structured knowledge from conversations.

Instead of storing conversations, it stores meaningful knowledge.

Conversation:

> "I've been building AI infrastructure with Python and FastAPI."

Stored Memory:

* Category: Skill
* Content: Experienced with Python and FastAPI
* Importance: High
* Confidence: High

The system remembers knowledge rather than replaying chat history.

---

# Responsibilities

The Memory Engine is responsible for:

* Extracting meaningful memories from conversations
* Deciding whether memories should be stored
* Generating semantic embeddings
* Persisting structured memories
* Retrieving relevant memories for future requests
* Updating conflicting or outdated memories
* Enriching prompts with retrieved context

The engine is not responsible for:

* Building chat interfaces
* User authentication
* Conversation history
* Workflow automation
* Tool calling
* Agent planning
* Frontend rendering

It is a memory subsystem.

---

# High-Level Request Flow

Every request should follow the exact same lifecycle.

Incoming User Message

↓

Retrieve Relevant Memories

↓

Build Context

↓

Send Context + User Message to LLM

↓

Receive LLM Response

↓

Extract Candidate Memories

↓

Score Importance

↓

Generate Embeddings

↓

Deduplicate / Update

↓

Persist Memory

↓

Return Final Response

Memory retrieval always occurs before model inference.

Memory extraction and storage always occur after model inference.

The two pipelines should remain independent.

---

# System Architecture

```
                Client Application
                       │
                       ▼
                 FastAPI Endpoints
                       │
                       ▼
                Memory Orchestrator
                       │
        ┌──────────────┼──────────────┐
        │              │              │
        ▼              ▼              ▼
   Memory Service   Prompt Builder   Providers
        │
        ▼
 ┌──────────────────────────────┐
 │  Extract                     │
 │  Score                       │
 │  Embed                       │
 │  Retrieve                    │
 │  Update                      │
 └──────────────────────────────┘
        │
        ▼
Database + Vector Index
```

The Orchestrator coordinates the application.

The Memory Service owns the complete memory lifecycle.

Providers communicate with external systems.

Everything else remains independent.

---

# Core Components

## Memory Orchestrator

Acts as the application's central coordinator.

Responsibilities:

* Receive API requests
* Coordinate retrieval
* Coordinate prompt construction
* Call LLM provider
* Trigger memory pipeline
* Return final response
* Handle failures
* Log execution

The orchestrator should delegate work rather than implementing business logic.

---

## Memory Service

The Memory Service is the heart of the application.

Every memory operation should pass through this service.

Responsibilities include:

* Extract memories
* Score importance
* Generate embeddings
* Retrieve memories
* Detect duplicates
* Update existing memories
* Persist memories
* Delete memories
* Search memories

The rest of the application should interact with memory only through this service.

---

## Memory Extractor

Converts natural language into structured knowledge.

The extractor should identify durable information rather than copying conversations.

Potential categories include:

* Skills
* Preferences
* Goals
* Projects
* Interests
* Career
* Personal Facts
* Relationships
* Habits
* Learning
* Technologies
* Important Events

Greetings, acknowledgements, filler text and temporary conversation should never become memories.

Structured outputs should be used instead of free-form text.

---

## Importance Scorer

Every extracted memory receives an importance score.

Only memories above a configurable threshold are persisted.

The scorer should minimize memory pollution while retaining valuable information.

---

## Embedding Generator

Every accepted memory receives an embedding.

Embedding generation should happen only after importance evaluation.

The embedding provider should be replaceable.

---

## Memory Store

Each memory should contain structured metadata.

Fields include:

* ID
* User ID
* Category
* Memory Content
* Importance Score
* Confidence Score
* Embedding
* Metadata
* Created Timestamp
* Updated Timestamp

The storage layer should remain isolated from business logic.

SQLite is sufficient for the MVP.

Migration to PostgreSQL should require minimal changes.

---

## Retriever

Retrieves semantically relevant memories using vector similarity.

Retrieval occurs before every model invocation.

Only the highest-quality memories should be returned.

Top-K retrieval and similarity thresholds should be configurable.

Keyword search should only be a fallback.

---

## Prompt Builder

Constructs the final prompt passed to the language model.

Inputs:

* Retrieved memories
* Current user message
* System prompt

Outputs:

Single optimized prompt.

Prompt construction should remain isolated from retrieval and storage.

---

## Memory Updater

Maintains consistency inside the memory store.

If incoming knowledge contradicts an existing memory, the existing memory should be updated rather than duplicated.

Duplicate detection should happen before persistence.

The goal is maintaining one accurate representation of each fact.

---

# Providers

External services should never be tightly coupled to business logic.

All provider-specific implementations remain isolated.

Provider types include:

LLM Provider

Embedding Provider

Database Provider

Vector Store Provider

Future providers should be swappable through configuration rather than code changes.

---

# API

The service should expose REST APIs.

Core endpoints include:

Chat

Memory CRUD

Memory Search

Memory List

Health Check

Configuration

Responses should remain consistent and strongly typed.

---

# Folder Structure

```
memory-engine/

├── app/
│
│   ├── api/
│   │   ├── memory.py
│   │   ├── chat.py
│   │   └── router.py
│   │
│   ├── core/
│   │   ├── orchestrator.py
│   │   ├── config.py
│   │   ├── logging.py
│   │   └── prompts.py
│   │
│   ├── memory/
│   │   ├── extractor.py
│   │   ├── retriever.py
│   │   ├── scorer.py
│   │   ├── updater.py
│   │   ├── embeddings.py
│   │   ├── models.py
│   │   └── service.py
│   │
│   ├── adapters/
│   │   ├── llm.py
│   │   ├── vector.py
│   │   └── database.py
│   │
│   ├── utils/
│   │   └── helpers.py
│   │
│   └── main.py
│
├── tests/
├── examples/
├── docs/
│
├── README.md
├── pyproject.toml
├── .env.example
└── docker-compose.yml
```

The project intentionally favors fewer modules with higher cohesion.

Business logic should stay inside the `memory` package.

Infrastructure integrations belong in `adapters`.

Application coordination belongs in `core`.

Route handlers should remain thin and simply delegate to the orchestrator or memory service.

---

# Configuration

The application should support configuration through environment variables.

Configuration includes:

* LLM Provider
* Embedding Provider
* Database
* Vector Store
* Similarity Threshold
* Top-K Retrieval
* Importance Threshold
* Logging Level
* API Keys

Configuration should remain centralized.

---

# Logging

Every major operation should be logged.

Examples:

Incoming requests

Retrieval latency

Embedding latency

LLM latency

Similarity scores

Memory extraction

Memory updates

Storage decisions

Failures

Logs should be structured and human-readable.

---

# Error Handling

Gracefully handle:

* Invalid requests
* Provider failures
* Embedding failures
* Database failures
* Vector search failures
* Rate limits
* Timeouts
* Malformed structured outputs

Failures should never corrupt the memory store.

---

# Testing

The architecture should support isolated testing.

Primary testing targets include:

Memory extraction

Retrieval

Importance scoring

Duplicate detection

Memory updates

API endpoints

The project should be easy to extend with integration tests later.

---

# Documentation

Documentation should explain:

Project overview

Architecture

Memory lifecycle

API reference

Folder structure

Configuration

Example requests

Example responses

Deployment

Roadmap

Design decisions

Future improvements

The README should allow another engineer to understand the system without reading the implementation.

---

# Memory Lifecycle

Every memory follows the same lifecycle.

Conversation

↓

Extraction

↓

Importance Evaluation

↓

Embedding Generation

↓

Duplicate Detection

↓

Persistence

↓

Semantic Retrieval

↓

Prompt Construction

↓

Inference

↓

Repeat

This lifecycle should remain consistent across every request.

---

# MVP Scope

The first release should implement only the essential capabilities required for a functional memory engine.

Included:

* REST API
* Memory extraction
* Importance scoring
* Embedding generation
* SQLite persistence
* Vector similarity search
* Prompt enrichment
* Memory updates
* Configurable providers
* Logging
* Documentation

Deferred to future releases:

* Memory compression
* Reflection
* Memory decay
* Automatic summarization
* Temporal reasoning
* Knowledge graphs
* Memory visualization
* Multi-user tenancy
* Distributed storage
* Caching
* Streaming APIs

The architecture should make these additions possible without major restructuring.

---

# Success Criteria

A successful implementation should feel like a reusable infrastructure library rather than an application.

The completed system should:

* Learn structured knowledge automatically.
* Persist meaningful memories instead of conversations.
* Retrieve relevant memories using semantic similarity.
* Enrich prompts before every model invocation.
* Update knowledge when facts change.
* Remain provider-agnostic.
* Expose clean REST APIs.
* Maintain a simple, cohesive, and extensible architecture.

The final result should resemble a production-ready memory subsystem that developers can integrate into AI agents and LLM-powered applications to provide long-term semantic memory with minimal configuration.
