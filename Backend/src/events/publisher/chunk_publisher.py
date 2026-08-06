import asyncio
from src.Config.nats import get_js
from src.events.schema.chunk_event import FileChunkEventPayload


async def publish_chunk_embed_events(chunks: list[FileChunkEventPayload]) -> None:
    js = get_js()
    tasks = [
        js.publish("files.embed", chunk.model_dump_json().encode("utf-8"))
        for chunk in chunks
    ]
    if tasks:
        await asyncio.gather(*tasks)
