import nats
from nats.js import JetStreamContext
from nats.js.api import StreamConfig
from src.config import settings

nc = None
js: JetStreamContext | None = None


async def connect_nats() -> None:
    global nc, js
    nc = await nats.connect(settings.NATS_URL)
    js = nc.jetstream()
    await setup_streams()


async def setup_streams() -> None:
    global js
    if js:
        try:
            await js.add_stream(name="FILES_STREAM", subjects=["files.upload", "files.embed"])
        except Exception:
            pass


async def disconnect_nats() -> None:
    global nc, js
    if nc:
        await nc.close()
        nc = None
        js = None


def get_js() -> JetStreamContext:
    global js
    if js is None:
        raise RuntimeError("NATS JetStream connection is not initialized.")
    return js
