import uuid
import json
from datetime import datetime
from fastapi import HTTPException, status
from supabase import Client
from src.Config.database import get_db
from src.Config.redis import get_redis
from src.events.schema.file_event import FileUploadEventPayload


def evict_user_files_cache(user_id: str | None) -> None:
    if not user_id:
        return
    r = get_redis()
    if r is not None:
        try:
            r.delete(f"files:user:{user_id}")
        except Exception:
            pass


def get_user_files_cached(db: Client, user_id: str) -> list[dict]:
    r = get_redis()
    key = f"files:user:{user_id}"
    if r is not None:
        try:
            cached = r.get(key)
            if cached:
                return json.loads(cached)
        except Exception:
            pass

    response = db.table("files").select("*").eq("user_id", user_id).eq("is_active", True).order("created_at", desc=True).execute()
    files = response.data or []

    if r is not None and files:
        try:
            r.setex(key, 1800, json.dumps(files))
        except Exception:
            pass

    return files


def get_file_status(db: Client, file_id: str, user_id: str) -> dict:
    file_res = db.table("files").select("*").eq("id", file_id).eq("user_id", user_id).execute()
    if not file_res.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    file_record = file_res.data[0]

    chunks_res = db.table("document_chunks").select("id", count="exact").eq("file_id", file_id).execute()
    total_chunks = chunks_res.count if chunks_res.count is not None else len(chunks_res.data or [])

    status_str = "completed" if total_chunks > 0 else "processing"

    return {
        "file_id": file_id,
        "filename": file_record.get("name"),
        "status": status_str,
        "total_chunks": total_chunks
    }


def save_file_to_storage(payload: FileUploadEventPayload) -> dict:
    db = get_db()
    file_bytes = payload.file_content.encode("utf-8")
    unique_id = payload.id or str(uuid.uuid4())
    storage_path = f"{unique_id}_{payload.filename}"

    try:
        db.storage.from_("files").upload(
            path=storage_path,
            file=file_bytes,
            file_options={"content-type": payload.content_type}
        )
    except Exception:
        pass

    now = datetime.utcnow().isoformat()
    file_record = {
        "id": unique_id,
        "name": payload.filename,
        "path": storage_path,
        "type": ".txt",
        "user_id": payload.user_id,
        "is_active": True,
        "created_at": now,
        "updated_at": now
    }

    db.table("files").insert(file_record).execute()
    evict_user_files_cache(payload.user_id)
    return file_record
