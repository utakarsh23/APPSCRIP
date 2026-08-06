import traceback
from datetime import datetime
from fastapi import Request, status
from fastapi.responses import JSONResponse
from src.Config.database import get_db


async def exception_handling_middleware(request: Request, call_next):
    endpoint = request.url.path
    http_method = request.method
    forwarded = request.headers.get("x-forwarded-for")
    client_ip = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else None)
    user_payload = getattr(request.state, "user", {}) or {}
    user_id = user_payload.get("id")

    try:
        response = await call_next(request)
        if response.status_code >= 400:
            try:
                db = get_db()
                db.table("error_logs").insert({
                    "endpoint": endpoint,
                    "http_method": http_method,
                    "error_message": f"HTTP {response.status_code}",
                    "stack_trace": None,
                    "ip_address": client_ip,
                    "user_id": str(user_id) if user_id else None,
                    "timestamp": datetime.utcnow().isoformat()
                }).execute()
            except Exception:
                pass
        return response
    except Exception as exc:
        error_message = str(exc)
        stack_trace = traceback.format_exc()

        try:
            db = get_db()
            db.table("error_logs").insert({
                "endpoint": endpoint,
                "http_method": http_method,
                "error_message": error_message,
                "stack_trace": stack_trace,
                "ip_address": client_ip,
                "user_id": str(user_id) if user_id else None,
                "timestamp": datetime.utcnow().isoformat()
            }).execute()
        except Exception:
            pass

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "An unexpected internal server error occurred.",
                "error_message": error_message,
                "status_code": 500
            }
        )
