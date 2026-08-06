import logging
from huggingface_hub import InferenceClient
from huggingface_hub.errors import HfHubHTTPError
from src.config import settings
from src.utils.database import get_db
from src.events.schema.chunk_event import FileChunkEventPayload

logger = logging.getLogger(__name__)


def embed_text(text: str) -> list[float]:
    if not settings.HF_TOKEN:
        raise ValueError("HF_TOKEN is not configured in settings")

    client = InferenceClient(token=settings.HF_TOKEN)
    result = client.feature_extraction(text, model=settings.EMBEDDING_MODEL)

    vector = result.tolist() if hasattr(result, "tolist") else result
    if isinstance(vector, list) and vector and isinstance(vector[0], list):
        vector = vector[0]

    return vector


def to_pgvector(vector: list[float]) -> str:
    return "[" + ",".join(str(x) for x in vector) + "]"


def generate_and_store_embedding(payload: FileChunkEventPayload) -> dict | None:
    try:
        embedding = embed_text(payload.chunk_content)
        db = get_db()

        record = {
            "file_id": payload.file_id,
            "chunk_index": payload.chunk_index,
            "content": payload.chunk_content,
            "embedding": to_pgvector(embedding),
            "user_id": payload.user_id,
            "created_at": payload.created_at
        }

        db.table("document_chunks").insert(record).execute()
        return record
    except HfHubHTTPError as e:
        status_code = e.response.status_code if e.response is not None else None
        logger.error(f"HF Hub HTTP error {status_code} processing chunk {payload.chunk_index}: {e}")
        raise e
    except Exception as e:
        logger.error(f"Failed to generate embedding for chunk {payload.chunk_index}: {e}")
        raise e
