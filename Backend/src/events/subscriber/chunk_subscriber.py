import json
import asyncio
from src.Config.nats import get_js
from src.events.schema.chunk_event import FileChunkEventPayload
from src.services.embedding_service import generate_and_store_embedding


async def start_chunk_subscriber() -> None:
    js = get_js()
    sub = await js.subscribe(
        subject="files.embed",
        durable="file-embed-worker"
    )
    asyncio.create_task(_listen_for_chunk_embeds(sub))


async def _listen_for_chunk_embeds(sub) -> None:
    async for msg in sub.messages:
        try:
            data = json.loads(msg.data.decode("utf-8"))
            payload = FileChunkEventPayload(**data)
            generate_and_store_embedding(payload)
            await msg.ack()
        except Exception:
            await msg.nak()
