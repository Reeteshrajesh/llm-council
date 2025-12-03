"""
Storage layer with automatic switching between Database (PostgreSQL/MySQL) and JSON files.

Based on DATABASE_TYPE environment variable:
- "postgresql" or "mysql": Use database storage
- "json" (default): Use JSON file storage (backward compatible)
"""

import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
from .config import DATA_DIR
from .database import get_storage_type, is_using_database, SessionLocal
from .models import Conversation as ConversationModel


# ==================== JSON FILE STORAGE (Original) ====================

def ensure_data_dir():
    """Ensure the data directory exists."""
    Path(DATA_DIR).mkdir(parents=True, exist_ok=True)


def get_conversation_path(conversation_id: str) -> str:
    """Get the file path for a conversation."""
    return os.path.join(DATA_DIR, f"{conversation_id}.json")


def _json_create_conversation(conversation_id: str) -> Dict[str, Any]:
    """Create conversation in JSON file."""
    ensure_data_dir()

    conversation = {
        "id": conversation_id,
        "created_at": datetime.utcnow().isoformat(),
        "title": "New Conversation",
        "messages": []
    }

    path = get_conversation_path(conversation_id)
    with open(path, 'w') as f:
        json.dump(conversation, f, indent=2)

    return conversation


def _json_get_conversation(conversation_id: str) -> Optional[Dict[str, Any]]:
    """Get conversation from JSON file."""
    path = get_conversation_path(conversation_id)

    if not os.path.exists(path):
        return None

    with open(path, 'r') as f:
        return json.load(f)


def _json_save_conversation(conversation: Dict[str, Any]):
    """Save conversation to JSON file."""
    ensure_data_dir()

    path = get_conversation_path(conversation['id'])
    with open(path, 'w') as f:
        json.dump(conversation, f, indent=2)


def _json_list_conversations() -> List[Dict[str, Any]]:
    """List all conversations from JSON files."""
    ensure_data_dir()

    conversations = []
    for filename in os.listdir(DATA_DIR):
        if filename.endswith('.json'):
            path = os.path.join(DATA_DIR, filename)
            with open(path, 'r') as f:
                data = json.load(f)
                conversations.append({
                    "id": data["id"],
                    "created_at": data["created_at"],
                    "title": data.get("title", "New Conversation"),
                    "message_count": len(data["messages"])
                })

    conversations.sort(key=lambda x: x["created_at"], reverse=True)
    return conversations


def _json_delete_conversation(conversation_id: str) -> bool:
    """Delete conversation from JSON file."""
    path = get_conversation_path(conversation_id)

    if not os.path.exists(path):
        return False

    os.remove(path)
    return True


# ==================== DATABASE STORAGE (New) ====================

def _db_create_conversation(conversation_id: str) -> Dict[str, Any]:
    """Create conversation in database."""
    db = SessionLocal()
    try:
        conversation = ConversationModel(
            id=conversation_id,
            title="New Conversation",
            messages=[]
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        return conversation.to_dict()
    finally:
        db.close()


def _db_get_conversation(conversation_id: str) -> Optional[Dict[str, Any]]:
    """Get conversation from database."""
    db = SessionLocal()
    try:
        conversation = db.query(ConversationModel).filter(
            ConversationModel.id == conversation_id
        ).first()

        if conversation is None:
            return None

        return conversation.to_dict()
    finally:
        db.close()


def _db_save_conversation(conversation: Dict[str, Any]):
    """Save conversation to database."""
    db = SessionLocal()
    try:
        db_conversation = db.query(ConversationModel).filter(
            ConversationModel.id == conversation['id']
        ).first()

        if db_conversation:
            db_conversation.title = conversation['title']
            db_conversation.messages = conversation['messages']
            db.commit()
    finally:
        db.close()


def _db_list_conversations() -> List[Dict[str, Any]]:
    """List all conversations from database."""
    db = SessionLocal()
    try:
        conversations = db.query(ConversationModel).order_by(
            ConversationModel.created_at.desc()
        ).all()

        return [
            {
                "id": c.id,
                "created_at": c.created_at.isoformat(),
                "title": c.title,
                "message_count": len(c.messages or [])
            }
            for c in conversations
        ]
    finally:
        db.close()


def _db_delete_conversation(conversation_id: str) -> bool:
    """Delete conversation from database."""
    db = SessionLocal()
    try:
        conversation = db.query(ConversationModel).filter(
            ConversationModel.id == conversation_id
        ).first()

        if conversation is None:
            return False

        db.delete(conversation)
        db.commit()
        return True
    finally:
        db.close()


# ==================== UNIFIED API (Auto-switches based on flag) ====================

def create_conversation(conversation_id: str) -> Dict[str, Any]:
    """
    Create a new conversation.

    Automatically uses database or JSON based on DATABASE_TYPE.

    Args:
        conversation_id: Unique identifier for the conversation

    Returns:
        New conversation dict
    """
    if is_using_database():
        return _db_create_conversation(conversation_id)
    else:
        return _json_create_conversation(conversation_id)


def get_conversation(conversation_id: str) -> Optional[Dict[str, Any]]:
    """
    Load a conversation from storage.

    Automatically uses database or JSON based on DATABASE_TYPE.

    Args:
        conversation_id: Unique identifier for the conversation

    Returns:
        Conversation dict or None if not found
    """
    if is_using_database():
        return _db_get_conversation(conversation_id)
    else:
        return _json_get_conversation(conversation_id)


def save_conversation(conversation: Dict[str, Any]):
    """
    Save a conversation to storage.

    Automatically uses database or JSON based on DATABASE_TYPE.

    Args:
        conversation: Conversation dict to save
    """
    if is_using_database():
        _db_save_conversation(conversation)
    else:
        _json_save_conversation(conversation)


def list_conversations() -> List[Dict[str, Any]]:
    """
    List all conversations (metadata only).

    Automatically uses database or JSON based on DATABASE_TYPE.

    Returns:
        List of conversation metadata dicts
    """
    if is_using_database():
        return _db_list_conversations()
    else:
        return _json_list_conversations()


def add_user_message(conversation_id: str, content: str):
    """
    Add a user message to a conversation.

    Args:
        conversation_id: Conversation identifier
        content: User message content
    """
    conversation = get_conversation(conversation_id)
    if conversation is None:
        raise ValueError(f"Conversation {conversation_id} not found")

    conversation["messages"].append({
        "role": "user",
        "content": content
    })

    save_conversation(conversation)


def add_assistant_message(
    conversation_id: str,
    stage1: List[Dict[str, Any]],
    stage2: List[Dict[str, Any]],
    stage3: Dict[str, Any],
    metadata: Optional[Dict[str, Any]] = None
):
    """
    Add an assistant message with all 3 stages to a conversation.

    Args:
        conversation_id: Conversation identifier
        stage1: List of individual model responses
        stage2: List of model rankings
        stage3: Final synthesized response
        metadata: Optional metadata (e.g., tool outputs, token savings)
    """
    conversation = get_conversation(conversation_id)
    if conversation is None:
        raise ValueError(f"Conversation {conversation_id} not found")

    conversation["messages"].append({
        "role": "assistant",
        "stage1": stage1,
        "stage2": stage2,
        "stage3": stage3,
        "metadata": metadata
    })

    save_conversation(conversation)


def update_conversation_title(conversation_id: str, title: str):
    """
    Update the title of a conversation.

    Args:
        conversation_id: Conversation identifier
        title: New title for the conversation
    """
    conversation = get_conversation(conversation_id)
    if conversation is None:
        raise ValueError(f"Conversation {conversation_id} not found")

    conversation["title"] = title
    save_conversation(conversation)


def delete_conversation(conversation_id: str) -> bool:
    """
    Delete a conversation from storage.

    Automatically uses database or JSON based on DATABASE_TYPE.
    Works with JSON, PostgreSQL, and MySQL backends.

    Args:
        conversation_id: Unique identifier for the conversation

    Returns:
        True if conversation was deleted, False if not found
    """
    if is_using_database():
        return _db_delete_conversation(conversation_id)
    else:
        return _json_delete_conversation(conversation_id)


# ==================== UTILITY FUNCTIONS ====================

def get_storage_info() -> Dict[str, str]:
    """
    Get information about current storage backend.

    Returns:
        Dict with storage type and status
    """
    storage_type = get_storage_type()

    return {
        "type": storage_type,
        "using_database": is_using_database(),
        "description": {
            "postgresql": "PostgreSQL database storage",
            "mysql": "MySQL database storage",
            "json": "JSON file storage (default)"
        }.get(storage_type, "Unknown")
    }
