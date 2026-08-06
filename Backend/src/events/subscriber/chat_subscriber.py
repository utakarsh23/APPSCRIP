import json
import asyncio
import logging
from src.config import settings
from src.Config.nats import get_js
from src.Config.database import get_db

logger = logging.getLogger(__name__)


async def start_chat_batch_subscriber() -> None:
    js = get_js()
    sub = await js.subscribe(
        subject="chat.messages",
        durable="chat-batch-worker"
    )
    asyncio.create_task(listen_and_batch_chat_messages(sub))


async def listen_and_batch_chat_messages(sub) -> None:
    buffer = []
    ack_msgs = []
    last_flush_time = asyncio.get_event_loop().time()

    async def flush_buffer():
        nonlocal buffer, ack_msgs, last_flush_time
        if not buffer:
            return
        try:
            db = get_db()
            db.table("chat_messages").insert(buffer).execute()
            for m in ack_msgs:
                await m.ack()
        except Exception as e:
            logger.error(f"Failed to bulk insert chat messages batch: {e}")
            for m in ack_msgs:
                await m.nak()
        finally:
            buffer = []
            ack_msgs = []
            last_flush_time = asyncio.get_event_loop().time()

    async for msg in sub.messages:
        try:
            data = json.loads(msg.data.decode("utf-8"))
            buffer.append({
                "session_id": data["session_id"],
                "role": data["role"],
                "content": data["content"],
                "created_at": data["created_at"]
            })
            ack_msgs.append(msg)

            now = asyncio.get_event_loop().time()
            if len(buffer) >= settings.BATCH_FLUSH_SIZE or (now - last_flush_time) >= settings.BATCH_FLUSH_INTERVAL:
                await flush_buffer()
        except Exception:
            await msg.nak()
