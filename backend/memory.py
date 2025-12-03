"""Conversation memory with optional embeddings backend.

Defaults to free local sentence-transformers; can switch to OpenAI embeddings
when ENABLE_OPENAI_EMBEDDINGS=true and OPENAI_API_KEY is set.
"""

from __future__ import annotations

import os
from typing import Optional
from pathlib import Path

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma


def get_embeddings():
    """Return embeddings implementation based on env flags."""
    if os.getenv("ENABLE_OPENAI_EMBEDDINGS", "false").lower() == "true":
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            try:
                from langchain_openai import OpenAIEmbeddings

                return OpenAIEmbeddings(api_key=api_key)
            except Exception:
                # Fall back to local embeddings on failure
                pass

    # Free local embeddings
    return HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")


class CouncilMemorySystem:
    """Lightweight per-conversation memory backed by Chroma."""

    def __init__(self, conversation_id: str):
        self.enabled = os.getenv("ENABLE_MEMORY", "true").lower() == "true"
        self.conversation_id = conversation_id
        self.retriever = None
        self.vectorstore = None

        if not self.enabled:
            return

        embeddings = get_embeddings()
        store_path = Path("./data/memory") / conversation_id
        store_path.mkdir(parents=True, exist_ok=True)

        self.vectorstore = Chroma(
            collection_name=f"conv_{conversation_id}",
            embedding_function=embeddings,
            persist_directory=str(store_path),
        )
        self.retriever = self.vectorstore.as_retriever(search_kwargs={"k": 3})

    def get_context(self, query: str) -> str:
        """Retrieve relevant context for a query."""
        if not self.enabled or self.retriever is None:
            return ""
        try:
            docs = self.retriever.get_relevant_documents(query)
            if not docs:
                return ""
            return "\n".join(doc.page_content for doc in docs if doc.page_content).strip()
        except Exception:
            return ""

    def save_exchange(self, user_msg: str, assistant_msg: str):
        """Persist a user/assistant exchange."""
        if not self.enabled or self.vectorstore is None:
            return
        try:
            content = f"User: {user_msg}\nAssistant: {assistant_msg}"
            self.vectorstore.add_texts([content])
        except Exception:
            return
