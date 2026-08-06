from datetime import datetime
from pydantic import BaseModel, Field


class ChatMessageEventPayload(BaseModel):
    session_id: str
    role: str
    content: str
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
