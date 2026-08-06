import redis
from src.config import settings

redis_client: redis.Redis | None = None


def connect_redis() -> None:
    global redis_client
    if redis_client is None:
        try:
            redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
            redis_client.ping()
        except Exception:
            redis_client = None


def disconnect_redis() -> None:
    global redis_client
    if redis_client is not None:
        try:
            redis_client.close()
        except Exception:
            pass
        redis_client = None


def get_redis() -> redis.Redis | None:
    return redis_client
