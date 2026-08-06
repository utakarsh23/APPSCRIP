import json
from datetime import datetime
from supabase import Client
from src.Config.redis import get_redis
from src.Schema.Chat import ChatSessionModel, ChatMessageModel


def create_session(db: Client, file_id: str, user_id: str, title: str | None = None) -> dict:
    now = datetime.utcnow().isoformat()
    record = {
        "file_id": file_id,
        "user_id": user_id,
        "title": title or "New Chat Session",
        "created_at": now
    }
    response = db.table("chat_sessions").insert(record).execute()
    if response.data and len(response.data) > 0:
        return response.data[0]
    return record


def get_session_by_id(db: Client, session_id: str) -> dict | None:
    response = db.table("chat_sessions").select("*").eq("id", session_id).execute()
    if response.data and len(response.data) > 0:
        return response.data[0]
    return None


def get_sessions_for_file(db: Client, file_id: str, user_id: str) -> list[dict]:
    response = db.table("chat_sessions").select("*").eq("file_id", file_id).eq("user_id", user_id).order("created_at", desc=True).execute()
    return response.data or []


def get_sessions_for_user(db: Client, user_id: str) -> list[dict]:
    response = db.table("chat_sessions").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
    return response.data or []


def cache_message_in_redis(session_id: str, role: str, content: str, created_at: str) -> None:
    r = get_redis()
    if r is None:
        return
    try:
        key = f"chat:{session_id}:messages"
        item = json.dumps({"role": role, "content": content, "created_at": created_at})
        r.rpush(key, item)
        r.expire(key, 3600)
    except Exception:
        pass


def get_messages_cached(db: Client, session_id: str, limit: int = 5) -> list[dict]:
    r = get_redis()
    key = f"chat:{session_id}:messages"
    if r is not None:
        try:
            items = r.lrange(key, -limit, -1)
            if items:
                return [json.loads(i) for i in items]
        except Exception:
            pass

    response = db.table("chat_messages").select("*").eq("session_id", session_id).order("created_at", desc=False).limit(limit).execute()
    messages = response.data or []

    if r is not None and messages:
        try:
            r.delete(key)
            for m in messages:
                r.rpush(key, json.dumps({
                    "role": m["role"],
                    "content": m["content"],
                    "created_at": str(m["created_at"])
                }))
            r.expire(key, 3600)
        except Exception:
            pass

    return messages


def search_similar_chunks(db: Client, file_id: str, query_vector: list[float], top_k: int = 5) -> list[dict]:
    try:
        rpc_response = db.rpc(
            "match_document_chunks",
            {
                "file_id_filter": file_id,
                "query_embedding": query_vector,
                "match_threshold": 0.0,
                "match_count": top_k
            }
        ).execute()
        if rpc_response.data:
            return rpc_response.data
    except Exception:
        pass

    fallback_response = db.table("document_chunks").select("id, chunk_index, content").eq("file_id", file_id).limit(top_k).execute()
    return fallback_response.data or []
