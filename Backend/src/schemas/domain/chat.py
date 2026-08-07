from datetime import datetime
from pydantic import BaseModel, Field


class ChatSessionModel(BaseModel):
    id: str
    file_id: str
    user_id: str
    title: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ChatMessageModel(BaseModel):
    id: str
    session_id: str
    role: str
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
