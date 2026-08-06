from datetime import datetime
from pydantic import BaseModel, Field, EmailStr


class FileModel(BaseModel):
    id: str | None = None
    name: str
    path: str
    user_id: str | None = None
    type: str[allowed_formats=[".txt", ".pdf", ".doc", ".docx"]]
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {
        "from_attributes": True,
        "json_encoders": {datetime: lambda v: v.isoformat()}
    }
