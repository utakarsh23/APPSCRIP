import os
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from google import genai
from google.genai import types
from src.config import settings

template_dir = Path(__file__).parent.parent / "templates"
jinja_env = Environment(loader=FileSystemLoader(str(template_dir)))

genai_client: genai.Client | None = None
caches_map: dict[str, str] = {}


def get_genai_client() -> genai.Client:
    global genai_client
    if genai_client is None:
        genai_client = genai.Client(api_key=settings.GEMINI_API_KEY)
    return genai_client


def render_system_prompt() -> str:
    template = jinja_env.get_template("system_prompt.j2")
    return template.render()


def render_context_prompt(chunks: list[dict], history: list[dict], query: str) -> str:
    template = jinja_env.get_template("context_prompt.j2")
    return template.render(chunks=chunks, history=history, query=query)


def get_or_create_context_cache(file_id: str, system_instruction_text: str) -> str | None:
    global caches_map
    if file_id in caches_map:
        return caches_map[file_id]

    client = get_genai_client()
    try:
        cache = client.caches.create(
            model=settings.GEMINI_MODEL,
            config=types.CreateCachedContentConfig(
                contents=[system_instruction_text],
                ttl="3600s"
            )
        )
        if cache and hasattr(cache, "name"):
            caches_map[file_id] = cache.name
            return cache.name
    except Exception:
        pass
    return None


async def stream_gemini_response(cached_content_name: str | None, context_prompt: str, system_instruction: str):
    client = get_genai_client()
    config_kwargs = {}
    if cached_content_name:
        config_kwargs["cached_content"] = cached_content_name
    else:
        config_kwargs["system_instruction"] = system_instruction

    config = types.GenerateContentConfig(**config_kwargs)

    response_stream = client.models.generate_content_stream(
        model=settings.GEMINI_MODEL,
        contents=context_prompt,
        config=config
    )

    for chunk in response_stream:
        if chunk.text:
            yield chunk.text
