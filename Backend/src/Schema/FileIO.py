from pydantic import BaseModel


class FileUploadResponse(BaseModel):
    message: str
    file_id: str
    filename: str
    status: str = "queued"


class FileStatusResponse(BaseModel):
    file_id: str
    filename: str
    status: str
    total_chunks: int
