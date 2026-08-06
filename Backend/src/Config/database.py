from supabase import create_client, Client
from src.config import settings

_supabase_client: Client | None = None


def connect_db() -> None:
    global _supabase_client
    _supabase_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)


def disconnect_db() -> None:
    global _supabase_client
    _supabase_client = None


def get_db() -> Client:
    global _supabase_client
    if _supabase_client is None:
        connect_db()
    return _supabase_client
