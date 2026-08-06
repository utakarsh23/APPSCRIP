from pydantic import BaseModel


class FileUploadResponse(BaseModel):
    message: str
    filename: str
    status: str = "queued"
