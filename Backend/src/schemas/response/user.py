from datetime import datetime
from pydantic import BaseModel, EmailStr


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: str | None = None
    username: str | None = None


class UserResponse(BaseModel):
    id: str
    email: EmailStr
    username: str
    created_at: datetime
