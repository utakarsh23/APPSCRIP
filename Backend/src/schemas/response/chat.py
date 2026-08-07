from datetime import datetime
from pydantic import BaseModel


class CreateSessionResponse(BaseModel):
    session_id: str
    file_id: str
    title: str | None = None
    created_at: datetime


class ChatSessionResponse(BaseModel):
    id: str
    file_id: str
    user_id: str
    title: str | None = None
    created_at: datetime


class ChatMessageItem(BaseModel):
    id: str | None = None
    session_id: str
    role: str
    content: str
    created_at: str | None = None


class GetMessagesResponse(BaseModel):
    session_id: str
    messages: list[ChatMessageItem]
