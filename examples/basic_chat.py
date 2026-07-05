"""
Example: Basic memory-augmented conversation using the Bullet Memory REST API.

Usage:
    python examples/basic_chat.py

Prerequisites:
    - Bullet Memory server running at http://localhost:8000
    - OPENAI_API_KEY set in .env
"""
from __future__ import annotations

import json

import httpx

BASE_URL = "http://localhost:8000"
USER_ID = "example_user"


def chat(message: str) -> dict:
    response = httpx.post(
        f"{BASE_URL}/chat",
        json={"user_id": USER_ID, "message": message},
        timeout=60.0,
    )
    response.raise_for_status()
    return response.json()


def list_memories() -> list[dict]:
    response = httpx.get(f"{BASE_URL}/memories/{USER_ID}")
    response.raise_for_status()
    return response.json()["memories"]


def search_memories(query: str) -> list[dict]:
    response = httpx.post(
        f"{BASE_URL}/memories/search",
        json={"user_id": USER_ID, "query": query, "top_k": 5},
    )
    response.raise_for_status()
    return response.json()["memories"]


if __name__ == "__main__":
    print("=" * 60)
    print("Bullet Memory — Basic Chat Example")
    print("=" * 60)

    conversations = [
        "Hi! I'm a software engineer. I mostly work with Python and FastAPI.",
        "I'm currently building an AI-powered code review tool at my startup.",
        "My main goal this year is to ship the MVP and get our first 10 customers.",
    ]

    for msg in conversations:
        print(f"\nUser: {msg}")
        result = chat(msg)
        print(f"Assistant: {result['response'][:200]}...")
        print(f"  [memories retrieved: {result['memories_retrieved']}, stored: {result['memories_stored']}]")

    print("\n" + "=" * 60)
    print("Stored Memories:")
    print("=" * 60)
    for m in list_memories():
        print(f"  [{m['category']}] {m['content']} (importance={m['importance']:.2f})")

    print("\n" + "=" * 60)
    print("Semantic Search: 'programming skills'")
    print("=" * 60)
    for m in search_memories("programming skills"):
        print(f"  [{m['category']}] {m['content']}")
