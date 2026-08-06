import uuid
import asyncio
from fastapi import APIRouter, Request, UploadFile, File, HTTPException, status
from src.Schema.FileIO import FileUploadResponse
from src.utils.chunking import chunk_text
from src.events.schema.file_event import FileUploadEventPayload
from src.events.schema.chunk_event import FileChunkEventPayload
from src.events.publisher.file_publisher import publish_file_upload_event
from src.events.publisher.chunk_publisher import publish_chunk_embed_events

router = APIRouter(prefix="/files", tags=["Files"])


@router.post("/upload", response_model=FileUploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_file(request: Request, file: UploadFile = File(...)) -> FileUploadResponse:
    if not file.filename or not file.filename.endswith(".txt"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .txt files are supported for upload."
        )

    user_payload = getattr(request.state, "user", {}) or {}
    user_id = user_payload.get("id") or user_payload.get("user_id") or user_payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user session."
        )

    content_bytes = await file.read()
    file_text = content_bytes.decode("utf-8", errors="replace")

    file_id = str(uuid.uuid4())

    raw_payload = FileUploadEventPayload(
        id=file_id,
        user_id=str(user_id),
        filename=file.filename,
        file_content=file_text,
        content_type=file.content_type or "text/plain"
    )

    chunks = chunk_text(file_text)
    chunk_payloads = [
        FileChunkEventPayload(
            file_id=file_id,
            chunk_index=index,
            chunk_content=chunk,
            user_id=str(user_id)
        )
        for index, chunk in enumerate(chunks)
    ]

    await asyncio.gather(
        publish_file_upload_event(raw_payload),
        publish_chunk_embed_events(chunk_payloads)
    )

    return FileUploadResponse(
        message="File processing queued successfully",
        filename=file.filename,
        status="queued"
    )
