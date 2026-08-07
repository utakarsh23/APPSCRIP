from src.Config.nats import get_js
from src.events.schema.file_event import FileUploadEventPayload


async def publish_file_event(payload: FileUploadEventPayload) -> None:
    js = get_js()
    payload_json = payload.model_dump_json()
    await js.publish("files.upload", payload_json.encode("utf-8"))
