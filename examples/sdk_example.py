"""
Bullet Memory SDK — Usage Examples

Run with: python examples/sdk_example.py
"""
import asyncio
import sys
sys.path.insert(0, "../sdk")

from bullet_memory import BulletMemoryClient


async def main():
    print("\n🧠 Bullet Memory SDK Demo\n" + "="*40)

    async with BulletMemoryClient("http://localhost:8000") as client:

        # 1. Health check
        health = await client.health()
        print(f"\n✅ Engine status: {health['status']} | Model: {health.get('llm_provider')}")

        USER_ID = "sdk-demo-user"

        # 2. Ingest raw text (with LLM extraction)
        print("\n📥 Ingesting raw text...")
        result = await client.ingest_raw(
            text="I am a senior backend engineer specializing in Python, FastAPI, and distributed systems. "
                 "My primary goal is to build production-grade AI infrastructure.",
            user_id=USER_ID,
            agent_id="demo-agent",
            session_id="demo-session-001",
            tags=["career", "tech"],
            sync=True,
        )
        print(f"   Stored {result.get('memories_stored', '?')} memories")

        # 3. Ingest a structured agent event
        print("\n📡 Logging agent observation...")
        event_result = await client.ingest_event(
            content="User consistently selects Python code examples over JavaScript alternatives.",
            user_id=USER_ID,
            agent_id="demo-agent",
            event_type="observation",
            importance=0.85,
            tags=["preference", "coding"],
        )
        print(f"   Stored: {event_result.get('memory_id')}")

        # 4. Direct store (no LLM)
        print("\n💾 Directly storing a memory...")
        store_result = await client.store(
            content="User's GitHub handle is @sudhanwa-dev.",
            user_id=USER_ID,
            importance=0.9,
            category="CoreFacts",
            tags=["identity"],
        )
        print(f"   Memory ID: {store_result.get('memory_id')}")

        # 5. Semantic retrieval
        print("\n🔍 Retrieving relevant context...")
        await asyncio.sleep(1)  # Give vector store a moment
        context = await client.get_context_string(
            query="What kind of engineer is this user?",
            user_id=USER_ID,
            top_k=3,
        )
        print(f"   Context:\n{context}")

        # 6. List all with filters
        print("\n📋 Listing all memories...")
        all_memories = await client.list_all(user_id=USER_ID, min_importance=0.7)
        print(f"   Total: {len(all_memories)} memories")
        for m in all_memories:
            print(f"   [{m['category']}] {m['content'][:60]}... (imp: {m['importance']})")

        # 7. Export fine-tuning dataset
        print("\n📦 Exporting fine-tuning dataset (OpenAI format)...")
        dataset = await client.export_finetune(user_id=USER_ID, format="openai")
        lines = [l for l in dataset.split("\n") if l.strip()]
        print(f"   Exported {len(lines)} records")
        if lines:
            import json
            sample = json.loads(lines[0])
            print(f"   Sample: {sample['messages'][1]['content'][:80]}...")

    print("\n✅ SDK demo complete!\n")


if __name__ == "__main__":
    asyncio.run(main())
