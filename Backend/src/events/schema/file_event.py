from pydantic import BaseModel, Field
from datetime import datetime


class FileUploadEventPayload(BaseModel):
    id: str | None = None
    filename: str
    file_content: str
    content_type: str = "text/plain"
    user_id: str | None = None
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
