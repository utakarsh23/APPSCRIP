from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI
from src.config import settings
from src.utils.database import connect_db, disconnect_db
from src.Config.nats import connect_nats, disconnect_nats
from src.events.subscriber.file_subscriber import start_file_subscriber
from src.events.subscriber.chunk_subscriber import start_chunk_subscriber
from src.middleware.auth import verify_jwt_middleware
from src.routes.auth import router as auth_router
from src.routes.file import router as file_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    connect_db()
    try:
        await connect_nats()
        await start_file_subscriber()
        await start_chunk_subscriber()
    except Exception:
        pass
    yield
    try:
        await disconnect_nats()
    except Exception:
        pass
    disconnect_db()


app = FastAPI(
    title=settings.PROJECT_NAME,
    lifespan=lifespan
)

app.middleware("http")(verify_jwt_middleware)

app.include_router(auth_router)
app.include_router(file_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "environment": settings.ENVIRONMENT}
