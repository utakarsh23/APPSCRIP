import uuid
import asyncio
from fastapi import APIRouter, Request, UploadFile, File, HTTPException, Depends, status
from supabase import Client
from src.Config.database import get_db
from src.Schema.FileIO import FileUploadResponse, FileStatusResponse
from src.Schema.File import FileModel
from src.utils.chunking import chunk_text
from src.services.file_service import get_user_files_cached, evict_user_files_cache, get_file_status
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
    user_id = user_payload.get("id")
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

    evict_user_files_cache(str(user_id))

    return FileUploadResponse(
        message="File processing queued successfully",
        file_id=file_id,
        filename=file.filename,
        status="queued"
    )


@router.get("/{file_id}/status", response_model=FileStatusResponse)
async def check_file_status(
    file_id: str,
    request: Request,
    db: Client = Depends(get_db)
) -> FileStatusResponse:
    user_payload = getattr(request.state, "user", {}) or {}
    user_id = user_payload.get("id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user session."
        )

    status_dict = get_file_status(db, file_id, str(user_id))
    return FileStatusResponse(**status_dict)


@router.get("", response_model=list[FileModel])
async def list_files(
    request: Request,
    db: Client = Depends(get_db)
) -> list[FileModel]:
    user_payload = getattr(request.state, "user", {}) or {}
    user_id = user_payload.get("id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user session."
        )

    files = get_user_files_cached(db, str(user_id))
    return [FileModel(**f) for f in files]
