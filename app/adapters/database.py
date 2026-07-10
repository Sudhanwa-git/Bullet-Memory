"""
Database Adapter — async SQLite persistence via SQLAlchemy + aiosqlite.

Responsible for all relational CRUD operations on Memory records.
The vector index lives separately in the Vector Store adapter.

Schema is intentionally rich to support:
  - Multi-agent ingestion (agent_id, source_type)
  - Session grouping (session_id)
  - Fine-tuning export (source_text preserved)
  - Retrieval tracking (access_count, last_accessed_at)
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

import structlog
from sqlalchemy import Column, DateTime, Float, Integer, String, Text, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings
from app.memory.models import ExtractedMemory, Memory, MemoryCategory, SourceType

logger = structlog.get_logger(__name__)


# ── ORM Schema ────────────────────────────────────────────────────────────────


class Base(DeclarativeBase):
    pass


class MemoryRow(Base):
    __tablename__ = "memories"

    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False, index=True)
    agent_id = Column(String, nullable=True, index=True)
    session_id = Column(String, nullable=True, index=True)
    category = Column(String, nullable=False)
    source_type = Column(String, nullable=False, default="chat")
    content = Column(Text, nullable=False)
    source_text = Column(Text, nullable=True)
    importance = Column(Float, nullable=False)
    confidence = Column(Float, nullable=False, default=1.0)
    tags_json = Column(Text, default="[]")
    access_count = Column(Integer, nullable=False, default=0)
    metadata_json = Column(Text, default="{}")
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    last_accessed_at = Column(DateTime, nullable=True)
    is_shared = Column(Integer, nullable=False, default=0)  # sqlite bool
    expires_at = Column(DateTime, nullable=True)
    roles_json = Column(Text, default="[]")


class NodeRow(Base):
    __tablename__ = "nodes"

    id = Column(String, primary_key=True)
    memory_id = Column(String, nullable=True, index=True)
    label = Column(String, nullable=False, index=True)
    properties_json = Column(Text, default="{}")


class EdgeRow(Base):
    __tablename__ = "edges"

    id = Column(String, primary_key=True)
    source_node_id = Column(String, nullable=False, index=True)
    target_node_id = Column(String, nullable=False, index=True)
    relationship_type = Column(String, nullable=False, index=True)
    properties_json = Column(Text, default="{}")


# ── Adapter ───────────────────────────────────────────────────────────────────


class DatabaseAdapter:
    def __init__(self) -> None:
        self._engine = create_async_engine(settings.DATABASE_URL, echo=False)
        self._session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
            self._engine, expire_on_commit=False
        )

    async def initialise(self) -> None:
        """Create tables if they don't exist."""
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("database.initialised")

    async def create_memory(
        self,
        user_id: str,
        candidate: ExtractedMemory,
        embedding: list[float],
        agent_id: str | None = None,
        session_id: str | None = None,
        source_type: SourceType = SourceType.CHAT,
    ) -> Memory:
        import uuid

        now = datetime.now(UTC)
        memory = Memory(
            id=str(uuid.uuid4()),
            user_id=user_id,
            agent_id=agent_id,
            session_id=session_id,
            category=candidate.category,
            source_type=source_type,
            content=candidate.content,
            source_text=candidate.source_text,
            importance=candidate.importance,
            confidence=candidate.confidence,
            tags=candidate.tags,
            created_at=now,
            updated_at=now,
        )
        row = MemoryRow(
            id=memory.id,
            user_id=memory.user_id,
            agent_id=memory.agent_id,
            session_id=memory.session_id,
            category=memory.category.value,
            source_type=memory.source_type.value,
            content=memory.content,
            source_text=memory.source_text,
            importance=memory.importance,
            confidence=memory.confidence,
            tags_json=json.dumps(memory.tags),
            access_count=0,
            metadata_json=json.dumps(memory.metadata),
            created_at=memory.created_at,
            updated_at=memory.updated_at,
            is_shared=1 if memory.is_shared else 0,
            expires_at=memory.expires_at,
            roles_json=json.dumps(memory.roles),
        )
        async with self._session_factory() as session:
            session.add(row)
            await session.commit()
        logger.debug("database.create_memory", memory_id=memory.id)
        return memory

    async def create_direct_memory(self, memory: Memory) -> Memory:
        """Persist a pre-formed Memory object directly (no extraction)."""
        row = MemoryRow(
            id=memory.id,
            user_id=memory.user_id,
            agent_id=memory.agent_id,
            session_id=memory.session_id,
            category=memory.category.value,
            source_type=memory.source_type.value,
            content=memory.content,
            source_text=memory.source_text,
            importance=memory.importance,
            confidence=memory.confidence,
            tags_json=json.dumps(memory.tags),
            access_count=0,
            metadata_json=json.dumps(memory.metadata),
            created_at=memory.created_at,
            updated_at=memory.updated_at,
            is_shared=1 if memory.is_shared else 0,
            expires_at=memory.expires_at,
            roles_json=json.dumps(memory.roles),
        )
        async with self._session_factory() as session:
            session.add(row)
            await session.commit()
        return memory

    async def get_memory(self, memory_id: str) -> Memory | None:
        async with self._session_factory() as session:
            row = await session.get(MemoryRow, memory_id)
            if row is None:
                return None
            return self._to_model(row)

    async def list_memories(
        self,
        user_id: str,
        agent_id: str | None = None,
        session_id: str | None = None,
        source_type: SourceType | None = None,
        category: MemoryCategory | None = None,
        min_importance: float = 0.0,
    ) -> list[Memory]:
        async with self._session_factory() as session:
            q = select(MemoryRow).where(MemoryRow.user_id == user_id)
            if agent_id:
                q = q.where(MemoryRow.agent_id == agent_id)
            if session_id:
                q = q.where(MemoryRow.session_id == session_id)
            if source_type:
                q = q.where(MemoryRow.source_type == source_type.value)
            if category:
                q = q.where(MemoryRow.category == category.value)
            if min_importance > 0.0:
                q = q.where(MemoryRow.importance >= min_importance)
            q = q.order_by(MemoryRow.created_at.desc())
            result = await session.execute(q)
            return [self._to_model(r) for r in result.scalars()]

    async def get_memories_by_ids(self, memory_ids: list[str]) -> list[Memory]:
        """Fetch multiple memories by their IDs in a single query."""
        if not memory_ids:
            return []
        async with self._session_factory() as session:
            stmt = select(MemoryRow).where(MemoryRow.id.in_(memory_ids))
            result = await session.execute(stmt)
            rows = result.scalars().all()
            return [self._to_model(row) for row in rows]

    async def increment_access_count(self, memory_id: str) -> None:
        """Track how often a memory is retrieved."""
        async with self._session_factory() as session:
            row = await session.get(MemoryRow, memory_id)
            if row:
                row.access_count = (row.access_count or 0) + 1
                row.last_accessed_at = datetime.now(UTC)
                await session.commit()

    async def update_memory(
        self,
        memory_id: str,
        content: str,
        importance: float,
        confidence: float,
    ) -> Memory:
        async with self._session_factory() as session:
            row = await session.get(MemoryRow, memory_id)
            if row is None:
                raise ValueError(f"Memory {memory_id} not found")
            row.content = content
            row.importance = importance
            row.confidence = confidence
            row.updated_at = datetime.now(UTC)
            await session.commit()
            await session.refresh(row)
        return self._to_model(row)

    async def delete_memory(self, memory_id: str) -> None:
        async with self._session_factory() as session:
            row = await session.get(MemoryRow, memory_id)
            if row:
                await session.delete(row)
                await session.commit()

    async def search_memories_text(self, user_id: str, query: str) -> list[Memory]:
        """Simple lexical search across content and tags using ILIKE for Hybrid Search."""
        async with self._session_factory() as session:
            q = select(MemoryRow).where(
                MemoryRow.user_id == user_id,
                (MemoryRow.content.ilike(f"%{query}%")) | (MemoryRow.tags_json.ilike(f"%{query}%"))
            ).order_by(MemoryRow.created_at.desc()).limit(10)
            result = await session.execute(q)
            return [self._to_model(r) for r in result.scalars()]

    # ── Graph Methods ─────────────────────────────────────────────────────────

    async def create_node(self, label: str, memory_id: str | None = None, properties: dict | None = None) -> str:
        import uuid
        node_id = str(uuid.uuid4())
        row = NodeRow(
            id=node_id,
            memory_id=memory_id,
            label=label,
            properties_json=json.dumps(properties or {})
        )
        async with self._session_factory() as session:
            session.add(row)
            await session.commit()
        return node_id

    async def create_edge(self, source_id: str, target_id: str, rel_type: str, properties: dict | None = None) -> str:
        import uuid
        edge_id = str(uuid.uuid4())
        row = EdgeRow(
            id=edge_id,
            source_node_id=source_id,
            target_node_id=target_id,
            relationship_type=rel_type,
            properties_json=json.dumps(properties or {})
        )
        async with self._session_factory() as session:
            session.add(row)
            await session.commit()
        return edge_id

    async def get_graph_context_for_memories(self, memory_ids: list[str]) -> list[str]:
        """Multi-Hop Graph RAG: Given a set of retrieved memory IDs, fetch related node relationships."""
        if not memory_ids:
            return []
            
        async with self._session_factory() as session:
            # 1. Get all nodes associated with these memories
            nodes_stmt = select(NodeRow).where(NodeRow.memory_id.in_(memory_ids))
            nodes_result = await session.execute(nodes_stmt)
            start_nodes = {n.id: n.label for n in nodes_result.scalars().all()}
            
            if not start_nodes:
                return []
                
            node_ids = list(start_nodes.keys())
            
            # 2. Get all edges connected to these nodes (1-hop traversal)
            from sqlalchemy import or_
            edges_stmt = select(EdgeRow).where(
                or_(EdgeRow.source_node_id.in_(node_ids), EdgeRow.target_node_id.in_(node_ids))
            )
            edges_result = await session.execute(edges_stmt)
            edges = edges_result.scalars().all()
            
            if not edges:
                return []
                
            # 3. We need labels for the adjacent nodes we just discovered
            all_node_ids = set(node_ids)
            for e in edges:
                all_node_ids.add(e.source_node_id)
                all_node_ids.add(e.target_node_id)
                
            all_nodes_stmt = select(NodeRow).where(NodeRow.id.in_(list(all_node_ids)))
            all_nodes_result = await session.execute(all_nodes_stmt)
            node_labels = {n.id: n.label for n in all_nodes_result.scalars().all()}
            
            # 4. Format into readable graph triples
            context_triples = []
            for e in edges:
                src_label = node_labels.get(e.source_node_id, "Unknown")
                tgt_label = node_labels.get(e.target_node_id, "Unknown")
                context_triples.append(f"({src_label}) -[{e.relationship_type}]-> ({tgt_label})")
                
            return list(set(context_triples))

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _to_model(row: MemoryRow) -> Memory:
        return Memory(
            id=row.id,
            user_id=row.user_id,
            agent_id=row.agent_id,
            session_id=row.session_id,
            category=MemoryCategory(row.category) if row.category else MemoryCategory.GENERAL,
            source_type=SourceType(row.source_type) if row.source_type else SourceType.CHAT,
            content=row.content,
            source_text=row.source_text,
            importance=row.importance,
            confidence=row.confidence,
            tags=json.loads(row.tags_json or "[]"),
            access_count=row.access_count or 0,
            metadata=json.loads(row.metadata_json or "{}"),
            created_at=row.created_at,
            updated_at=row.updated_at,
            last_accessed_at=row.last_accessed_at,
            is_shared=bool(row.is_shared),
            expires_at=row.expires_at,
            roles=json.loads(row.roles_json or "[]"),
        )

