from datetime import datetime
from pydantic import BaseModel, Field, EmailStr


class UserModel(BaseModel):
    id: str | None = None
    email: EmailStr
    username: str
    password: str
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {
        "from_attributes": True,
        "json_encoders": {datetime: lambda v: v.isoformat()}
    }
