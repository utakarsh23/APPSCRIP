import json
import asyncio
from src.Config.nats import get_js
from src.events.schema.file_event import FileUploadEventPayload
from src.services.file_service import save_file_to_storage


async def start_file_subscriber() -> None:
    js = get_js()
    sub = await js.subscribe(
        subject="files.upload",
        durable="file-upload-worker"
    )
    asyncio.create_task(listen_files_uploads(sub))


async def listen_files_uploads(sub) -> None:
    async for msg in sub.messages:
        try:
            data = json.loads(msg.data.decode("utf-8"))
            payload = FileUploadEventPayload(**data)
            save_file_to_storage(payload)
            await msg.ack()
        except Exception:
            await msg.nak()
