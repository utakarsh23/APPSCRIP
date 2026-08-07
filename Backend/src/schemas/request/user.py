from pydantic import BaseModel, EmailStr, Field


class UserSignupRequest(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)


class UserLoginRequest(BaseModel):
    username: str | None = None
    email: EmailStr | None = None
    password: str
