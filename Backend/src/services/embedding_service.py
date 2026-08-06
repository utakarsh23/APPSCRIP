import logging
from google import genai
from src.config import settings
from src.Config.database import get_db
from src.events.schema.chunk_event import FileChunkEventPayload

logger = logging.getLogger(__name__)


def embed_text(text: str) -> list[float]:
    if settings.GEMINI_API_KEY:
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        response = client.models.embed_content(
            model="gemini-embedding-001",
            contents=text,
            config={"output_dimensionality": 1024}
        )
        if hasattr(response, "embedding") and response.embedding:
            return list(response.embedding.values)
        if hasattr(response, "embeddings") and response.embeddings:
            return list(response.embeddings[0].values)

    if settings.HF_TOKEN:
        from huggingface_hub import InferenceClient
        client = InferenceClient(token=settings.HF_TOKEN)
        result = client.feature_extraction(text, model=settings.EMBEDDING_MODEL)
        vector = result.tolist() if hasattr(result, "tolist") else result
        if isinstance(vector, list) and vector and isinstance(vector[0], list):
            vector = vector[0]
        return vector

    raise ValueError("Neither GEMINI_API_KEY nor HF_TOKEN is configured")


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
    except Exception as e:
        logger.error(f"Failed to generate embedding for chunk {payload.chunk_index}: {e}")
        raise e
