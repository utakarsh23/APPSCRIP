from pydantic import BaseModel


class CreateSessionRequest(BaseModel):
    file_id: str
    title: str | None = None


class ChatRequest(BaseModel):
    query: str
