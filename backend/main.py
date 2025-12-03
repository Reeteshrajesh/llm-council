"""FastAPI backend for LLM Council."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import uuid
import json
import asyncio

from . import storage
from .council import run_full_council, generate_conversation_title, stage1_collect_responses, stage2_collect_rankings, stage3_synthesize_final, calculate_aggregate_rankings
from .database import init_database

app = FastAPI(title="LLM Council API")

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database tables if using database storage."""
    init_database()

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CreateConversationRequest(BaseModel):
    """Request to create a new conversation."""
    pass


class SendMessageRequest(BaseModel):
    """Request to send a message in a conversation."""
    content: str
    context: Optional[List[Dict[str, Any]]] = None
    temporary: Optional[bool] = False  # If True, don't save to storage


class UpdateTitleRequest(BaseModel):
    """Request to update conversation title."""
    title: str


class ConversationMetadata(BaseModel):
    """Conversation metadata for list view."""
    id: str
    created_at: str
    title: str
    message_count: int


class Conversation(BaseModel):
    """Full conversation with all messages."""
    id: str
    created_at: str
    title: str
    messages: List[Dict[str, Any]]


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "LLM Council API"}


@app.get("/api/conversations", response_model=List[ConversationMetadata])
async def list_conversations():
    """List all conversations (metadata only)."""
    return storage.list_conversations()


@app.post("/api/conversations", response_model=Conversation)
async def create_conversation(request: CreateConversationRequest):
    """Create a new conversation."""
    conversation_id = str(uuid.uuid4())
    conversation = storage.create_conversation(conversation_id)
    return conversation


@app.get("/api/conversations/{conversation_id}", response_model=Conversation)
async def get_conversation(conversation_id: str):
    """Get a specific conversation with all its messages."""
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@app.patch("/api/conversations/{conversation_id}/title")
async def update_conversation_title(conversation_id: str, request: UpdateTitleRequest):
    """
    Update the title of a conversation.

    Works with all storage backends: JSON, PostgreSQL, MySQL.
    """
    # Check if conversation exists
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Update title
    storage.update_conversation_title(conversation_id, request.title)

    return {
        "success": True,
        "message": "Title updated",
        "title": request.title
    }


@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """
    Delete a conversation.

    Works with all storage backends: JSON, PostgreSQL, MySQL.
    """
    success = storage.delete_conversation(conversation_id)
    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"success": True, "message": "Conversation deleted"}


@app.post("/api/conversations/{conversation_id}/message")
async def send_message(conversation_id: str, request: SendMessageRequest):
    """
    Send a message and run the 3-stage council process.
    Returns the complete response with all stages.

    Supports temporary mode: if request.temporary=True, conversation is not saved to storage.
    """
    # For temporary mode, skip conversation existence check and storage operations
    if request.temporary:
        # Run the 3-stage council process without saving
        stage1_results, stage2_results, stage3_result, metadata = await run_full_council(
            request.content,
            conversation_id=None  # No conversation_id for temporary chat
        )

        # Return the complete response with metadata (not saved to storage)
        return {
            "stage1": stage1_results,
            "stage2": stage2_results,
            "stage3": stage3_result,
            "metadata": metadata,
            "temporary": True
        }

    # Normal mode: save to storage
    # Check if conversation exists
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Check if this is the first message
    is_first_message = len(conversation["messages"]) == 0

    # Add user message
    storage.add_user_message(conversation_id, request.content)

    # If this is the first message, generate a title
    if is_first_message:
        title = await generate_conversation_title(request.content)
        storage.update_conversation_title(conversation_id, title)

    # Run the 3-stage council process
    stage1_results, stage2_results, stage3_result, metadata = await run_full_council(
        request.content,
        conversation_id=conversation_id
    )

    # Add assistant message with all stages
    storage.add_assistant_message(
        conversation_id,
        stage1_results,
        stage2_results,
        stage3_result,
        metadata
    )

    # Return the complete response with metadata
    return {
        "stage1": stage1_results,
        "stage2": stage2_results,
        "stage3": stage3_result,
        "metadata": metadata
    }


@app.post("/api/conversations/{conversation_id}/message/stream")
async def send_message_stream(conversation_id: str, request: SendMessageRequest):
    """
    Send a message and stream the 3-stage council process.
    Returns Server-Sent Events as each stage completes.

    Supports temporary mode: if request.temporary=True, conversation is not saved to storage.
    """
    # For temporary mode, skip conversation check
    if not request.temporary:
        # Check if conversation exists (normal mode only)
        conversation = storage.get_conversation(conversation_id)
        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
        is_first_message = len(conversation["messages"]) == 0
    else:
        is_first_message = False  # No title generation for temporary chats

    async def event_generator():
        try:
            # Add user message (skip for temporary mode)
            if not request.temporary:
                storage.add_user_message(conversation_id, request.content)

                # Start title generation in parallel (don't await yet)
                title_task = None
                if is_first_message:
                    title_task = asyncio.create_task(generate_conversation_title(request.content))
            else:
                title_task = None

            # Collect metadata across stages for persistence
            msg_metadata = {}

            # Stage 1: Collect responses (with context)
            yield f"data: {json.dumps({'type': 'stage1_start'})}\n\n"
            stage1_results, tool_outputs = await stage1_collect_responses(
                request.content,
                context=request.context,
                conversation_id=None if request.temporary else conversation_id
            )
            msg_metadata["tool_outputs"] = tool_outputs
            yield f"data: {json.dumps({'type': 'stage1_complete', 'data': stage1_results, 'metadata': {'tool_outputs': tool_outputs}})}\n\n"

            # Stage 2: Collect rankings
            yield f"data: {json.dumps({'type': 'stage2_start'})}\n\n"
            stage2_results, label_to_model = await stage2_collect_rankings(request.content, stage1_results)
            aggregate_rankings = calculate_aggregate_rankings(stage2_results, label_to_model)
            msg_metadata["label_to_model"] = label_to_model
            msg_metadata["aggregate_rankings"] = aggregate_rankings
            yield f"data: {json.dumps({'type': 'stage2_complete', 'data': stage2_results, 'metadata': {'label_to_model': label_to_model, 'aggregate_rankings': aggregate_rankings}})}\n\n"

            # Stage 3: Synthesize final answer
            yield f"data: {json.dumps({'type': 'stage3_start'})}\n\n"
            stage3_result = await stage3_synthesize_final(
                request.content,
                stage1_results,
                stage2_results,
                tool_outputs=tool_outputs
            )

            # Calculate token savings
            from .council import calculate_token_savings
            token_savings = calculate_token_savings(stage1_results, stage2_results)

            msg_metadata["token_savings"] = token_savings

            yield f"data: {json.dumps({'type': 'stage3_complete', 'data': stage3_result, 'metadata': {'token_savings': token_savings, 'temporary': request.temporary}})}\n\n"

            # Wait for title generation if it was started (normal mode only)
            if title_task:
                title = await title_task
                storage.update_conversation_title(conversation_id, title)
                yield f"data: {json.dumps({'type': 'title_complete', 'data': {'title': title}})}\n\n"

            # Save complete assistant message (skip for temporary mode)
            if not request.temporary:
                storage.add_assistant_message(
                    conversation_id,
                    stage1_results,
                    stage2_results,
                    stage3_result,
                    msg_metadata
                )

            # Send completion event
            yield f"data: {json.dumps({'type': 'complete', 'temporary': request.temporary})}\n\n"

        except Exception as e:
            # Send error event
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
