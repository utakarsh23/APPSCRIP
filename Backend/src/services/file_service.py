import uuid
from datetime import datetime
from src.utils.database import get_db
from src.events.schema.file_event import FileUploadEventPayload


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
    return file_record
