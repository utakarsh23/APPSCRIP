from datetime import datetime
from pydantic import BaseModel, Field


class FileChunkEventPayload(BaseModel):
    file_id: str
    chunk_index: int
    chunk_content: str
    user_id: str | None = None
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
