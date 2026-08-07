from supabase import create_client, Client
from src.config import settings

supabase_client: Client | None = None


def connect_db() -> None:
    global supabase_client
    supabase_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)


def disconnect_db() -> None:
    global supabase_client
    supabase_client = None


def get_db() -> Client:
    global supabase_client
    if supabase_client is None:
        connect_db()
    return supabase_client
