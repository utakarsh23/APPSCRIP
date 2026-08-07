import json
import hashlib
from datetime import datetime
from supabase import Client
from src.Config.redis import get_redis
from src.schemas.domain.chat import ChatSessionModel, ChatMessageModel


def create_session(db: Client, file_id: str, user_id: str, title: str | None = None) -> dict:
    now = datetime.utcnow().isoformat()
    record = {
        "file_id": file_id,
        "user_id": user_id,
        "title": title or "New Chat Session",
        "created_at": now
    }
    response = db.table("chat_sessions").insert(record).execute()
    created_record = response.data[0] if (response.data and len(response.data) > 0) else record

    r = get_redis()
    if r is not None:
        try:
            r.delete(f"chat:user:{user_id}:sessions")
            r.delete(f"chat:file:{file_id}:user:{user_id}:sessions")
            if "id" in created_record:
                r.setex(f"chat:session:{created_record['id']}", 3600, json.dumps(created_record))
        except Exception:
            pass

    return created_record


def get_session_by_id(db: Client, session_id: str) -> dict | None:
    r = get_redis()
    key = f"chat:session:{session_id}"
    if r is not None:
        try:
            cached = r.get(key)
            if cached:
                return json.loads(cached)
        except Exception:
            pass

    response = db.table("chat_sessions").select("*").eq("id", session_id).execute()
    if response.data and len(response.data) > 0:
        session_data = response.data[0]
        if r is not None:
            try:
                r.setex(key, 3600, json.dumps(session_data))
            except Exception:
                pass
        return session_data

    return None


def get_sessions_for_file(db: Client, file_id: str, user_id: str) -> list[dict]:
    r = get_redis()
    key = f"chat:file:{file_id}:user:{user_id}:sessions"
    if r is not None:
        try:
            cached = r.get(key)
            if cached:
                return json.loads(cached)
        except Exception:
            pass

    response = db.table("chat_sessions").select("*").eq("file_id", file_id).eq("user_id", user_id).order("created_at", desc=True).execute()
    sessions = response.data or []

    if r is not None and sessions:
        try:
            r.setex(key, 1800, json.dumps(sessions))
        except Exception:
            pass

    return sessions


def get_sessions_for_user(db: Client, user_id: str) -> list[dict]:
    r = get_redis()
    key = f"chat:user:{user_id}:sessions"
    if r is not None:
        try:
            cached = r.get(key)
            if cached:
                return json.loads(cached)
        except Exception:
            pass

    response = db.table("chat_sessions").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
    sessions = response.data or []

    if r is not None and sessions:
        try:
            r.setex(key, 1800, json.dumps(sessions))
        except Exception:
            pass

    return sessions


def cache_messages(session_id: str, role: str, content: str, created_at: str) -> None:
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


def get_messages(db: Client, session_id: str, limit: int = 6) -> list[dict]:
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


def get_consecutive_duplicate_response(history: list[dict], current_query: str) -> str | None:
    if not history:
        return None

    normalized_current = current_query.strip().lower()

    last_user_idx = -1
    for i in range(len(history) - 1, -1, -1):
        if history[i].get("role") == "user":
            last_user_idx = i
            break

    if last_user_idx == -1:
        return None

    last_user_content = history[last_user_idx].get("content", "").strip().lower()
    if last_user_content != normalized_current:
        return None

    for i in range(last_user_idx + 1, len(history)):
        if history[i].get("role") == "assistant":
            return history[i].get("content")

    return None


def search_similar_chunks(db: Client, file_id: str, query_vector: list[float], top_k: int = 5) -> list[dict]:
    vec_hash = hashlib.md5(str(query_vector).encode("utf-8")).hexdigest()
    cache_key = f"chat:chunks_cache:{file_id}:{vec_hash}"

    r = get_redis()
    if r is not None:
        try:
            cached = r.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception:
            pass

    results = []
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
            results = rpc_response.data
    except Exception:
        pass

    if not results:
        fallback_response = db.table("document_chunks").select("id, chunk_index, content").eq("file_id", file_id).limit(top_k).execute()
        results = fallback_response.data or []

    if r is not None and results:
        try:
            r.setex(cache_key, 3600, json.dumps(results))
        except Exception:
            pass

    return results
