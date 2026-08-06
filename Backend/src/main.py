from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI
from src.config import settings
from src.utils.database import connect_db, disconnect_db
from src.Config.nats import connect_nats, disconnect_nats
from src.Config.redis import connect_redis, disconnect_redis
from src.events.subscriber.file_subscriber import start_file_subscriber
from src.events.subscriber.chunk_subscriber import start_chunk_subscriber
from src.events.subscriber.chat_subscriber import start_chat_batch_subscriber
from src.middleware.auth import verify_jwt_middleware
from src.middleware.exception import exception_handling_middleware
from src.routes.auth import router as auth_router
from src.routes.file import router as file_router
from src.routes.chat import router as chat_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    connect_db()
    connect_redis()
    try:
        await connect_nats()
        await start_file_subscriber()
        await start_chunk_subscriber()
        await start_chat_batch_subscriber()
    except Exception:
        pass
    yield
    try:
        await disconnect_nats()
    except Exception:
        pass
    disconnect_redis()
    disconnect_db()


app = FastAPI(
    title=settings.PROJECT_NAME,
    lifespan=lifespan
)

app.middleware("http")(exception_handling_middleware)
app.middleware("http")(verify_jwt_middleware)

app.include_router(auth_router)
app.include_router(file_router)
app.include_router(chat_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "environment": settings.ENVIRONMENT}
