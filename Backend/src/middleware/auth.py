from fastapi import Request, status
from fastapi.responses import JSONResponse
from src.utils.security import decode_access_token

EXEMPT_PATHS = ["/auth", "/health", "/docs", "/redoc", "/openapi.json"]


async def verify_jwt_middleware(request: Request, call_next):
    path = request.url.path

    if any(path.startswith(exempt) for exempt in EXEMPT_PATHS):
        return await call_next(request)

    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Missing or invalid authorization header"}
        )

    token = auth_header[7:].strip()
    payload = decode_access_token(token)
    if not payload:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Invalid or expired token"}
        )

    request.state.user = payload
    return await call_next(request)
