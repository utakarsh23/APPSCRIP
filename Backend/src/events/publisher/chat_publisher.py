from src.Config.nats import get_js
from src.events.schema.chat_event import ChatMessageEventPayload


async def publish_chat_message_event(payload: ChatMessageEventPayload) -> None:
    js = get_js()
    await js.publish("chat.messages", payload.model_dump_json().encode("utf-8"))
