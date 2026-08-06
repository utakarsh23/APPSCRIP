from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class UserSignupRequest(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)


class UserLoginRequest(BaseModel):
    username: str
    email: EmailStr
    password: str


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

    model_config = {
        "from_attributes": True
    }
