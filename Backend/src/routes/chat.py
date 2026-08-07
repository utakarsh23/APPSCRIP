from datetime import datetime
from fastapi import APIRouter, Request, HTTPException, Depends, status
from fastapi.responses import StreamingResponse
from supabase import Client
from src.Config.database import get_db
from src.services.embedding_service import embed_text
from src.schemas.request.chat import CreateSessionRequest, ChatRequest
from src.schemas.response.chat import (
    CreateSessionResponse,
    ChatSessionResponse,
    GetMessagesResponse,
    ChatMessageItem
)
from src.events.schema.chat_event import ChatMessageEventPayload
from src.events.publisher.chat_publisher import publish_chat_message_event
from src.services.chat_service import (
    create_session,
    get_session_by_id,
    get_sessions_for_file,
    get_sessions_for_user,
    get_messages,
    get_consecutive_duplicate_response,
    cache_messages,
    search_similar_chunks
)
from src.services.llm_service import (
    render_system_prompt,
    render_context_prompt,
    get_or_create_context_cache,
    stream_gemini_response
)

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("/session", response_model=CreateSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_chat_session(
    request: Request,
    body: CreateSessionRequest,
    db: Client = Depends(get_db)
) -> CreateSessionResponse:
    user_payload = getattr(request.state, "user", {}) or {}
    user_id = user_payload.get("id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user session.")

    session_data = create_session(db, body.file_id, str(user_id), body.title)
    return CreateSessionResponse(
        session_id=str(session_data["id"]),
        file_id=str(session_data["file_id"]),
        title=session_data.get("title"),
        created_at=datetime.fromisoformat(str(session_data["created_at"]).replace("Z", "+00:00"))
    )


@router.get("/sessions/{file_id}", response_model=list[ChatSessionResponse])
async def list_sessions_for_file(
    file_id: str,
    request: Request,
    db: Client = Depends(get_db)
) -> list[ChatSessionResponse]:
    user_payload = getattr(request.state, "user", {}) or {}
    user_id = user_payload.get("id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user session.")

    sessions = get_sessions_for_file(db, file_id, str(user_id))
    return [
        ChatSessionResponse(
            id=str(s["id"]),
            file_id=str(s["file_id"]),
            user_id=str(s["user_id"]),
            title=s.get("title"),
            created_at=datetime.fromisoformat(str(s["created_at"]).replace("Z", "+00:00"))
        )
        for s in sessions
    ]


@router.get("/sessions", response_model=list[ChatSessionResponse])
async def list_user_sessions(
    request: Request,
    db: Client = Depends(get_db)
) -> list[ChatSessionResponse]:
    user_payload = getattr(request.state, "user", {}) or {}
    user_id = user_payload.get("id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user session.")

    sessions = get_sessions_for_user(db, str(user_id))
    return [
        ChatSessionResponse(
            id=str(s["id"]),
            file_id=str(s["file_id"]),
            user_id=str(s["user_id"]),
            title=s.get("title"),
            created_at=datetime.fromisoformat(str(s["created_at"]).replace("Z", "+00:00"))
        )
        for s in sessions
    ]


@router.get("/session/{session_id}/messages", response_model=GetMessagesResponse)
async def get_session_messages(
    session_id: str,
    request: Request,
    db: Client = Depends(get_db)
) -> GetMessagesResponse:
    user_payload = getattr(request.state, "user", {}) or {}
    user_id = user_payload.get("id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user session.")

    session = get_session_by_id(db, session_id)
    if not session or str(session["user_id"]) != str(user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")

    messages = get_messages(db, session_id, limit=50)
    items = [
        ChatMessageItem(
            id=str(m.get("id")) if m.get("id") else None,
            session_id=session_id,
            role=m["role"],
            content=m["content"],
            created_at=str(m.get("created_at")) if m.get("created_at") else None
        )
        for m in messages
    ]
    return GetMessagesResponse(session_id=session_id, messages=items)


@router.post("/session/{session_id}")
async def chat_query(
    session_id: str,
    body: ChatRequest,
    request: Request,
    db: Client = Depends(get_db)
):
    user_payload = getattr(request.state, "user", {}) or {}
    user_id = user_payload.get("id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user session.")

    session = get_session_by_id(db, session_id)
    if not session or str(session["user_id"]) != str(user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")

    file_id = str(session["file_id"])
    query_text = body.query

    history = get_messages(db, session_id, limit=10)
    cached_duplicate_response = get_consecutive_duplicate_response(history, query_text)

    user_now = datetime.utcnow().isoformat()
    cache_messages(session_id, "user", query_text, user_now)
    await publish_chat_message_event(
        ChatMessageEventPayload(session_id=session_id, role="user", content=query_text, created_at=user_now)
    )

    if cached_duplicate_response:
        async def cached_sse_generator():
            yield f"data: {cached_duplicate_response}\n\n"
            assistant_now = datetime.utcnow().isoformat()
            cache_messages(session_id, "assistant", cached_duplicate_response, assistant_now)
            await publish_chat_message_event(
                ChatMessageEventPayload(session_id=session_id, role="assistant", content=cached_duplicate_response, created_at=assistant_now)
            )

        return StreamingResponse(cached_sse_generator(), media_type="text/event-stream")

    query_vector = embed_text(query_text)
    top_chunks = search_similar_chunks(db, file_id, query_vector, top_k=5)

    system_prompt_text = render_system_prompt()
    cached_content_name = get_or_create_context_cache(file_id, system_prompt_text)
    context_prompt_text = render_context_prompt(top_chunks, history, query_text)

    async def sse_event_generator():
        full_assistant_text = ""
        async for chunk_text in stream_gemini_response(cached_content_name, context_prompt_text, system_prompt_text):
            full_assistant_text += chunk_text
            yield f"data: {chunk_text}\n\n"

        assistant_now = datetime.utcnow().isoformat()
        cache_messages(session_id, "assistant", full_assistant_text, assistant_now)
        await publish_chat_message_event(
            ChatMessageEventPayload(session_id=session_id, role="assistant", content=full_assistant_text, created_at=assistant_now)
        )

    return StreamingResponse(sse_event_generator(), media_type="text/event-stream")
