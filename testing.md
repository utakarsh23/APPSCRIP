# API Testing Guide

Base URL: `http://localhost:8000` (Direct) or `http://localhost` (Nginx Proxy)

All endpoints except `/health` and `/auth/*` require:
`Authorization: Bearer <access_token>`

---

## 1. System Health

### `GET /health`
- **Headers**: None
- **Body**: None
- **Response** (`200 OK`):
```json
{
  "status": "ok",
  "environment": "development"
}
```

---

## 2. Authentication

### `POST /auth/signup`
- **Content-Type**: `application/json`
- **Body**:
```json
{
  "username": "johndoe",
  "email": "john@example.com",
  "password": "SecretPassword123!"
}
```
- **Response** (`201 Created`):
```json
{
  "id": "c56a4180-65aa-42ec-a945-5fd21dec0538",
  "username": "johndoe",
  "email": "john@example.com",
  "created_at": "2026-08-07T05:00:00+00:00"
}
```

### `POST /auth/login`
- **Content-Type**: `application/json`
- **Body**:
```json
{
  "email": "john@example.com",
  "password": "SecretPassword123!"
}
```
- **Response** (`200 OK`):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

---

## 3. Document Ingestion

### `POST /files/upload`
- **Headers**: `Authorization: Bearer <TOKEN>`
- **Content-Type**: `multipart/form-data`
- **Form Data**:
  - `file`: `@sample_document.txt` (Text file)
- **Response** (`202 Accepted`):
```json
{
  "message": "File processing queued successfully",
  "filename": "sample_document.txt",
  "file_id": "8f3b2a1c-9d4e-4f5a-8b2c-1d3e4f5a6b7c",
  "status": "queued"
}
```

### `GET /files/{file_id}/status`
- **Headers**: `Authorization: Bearer <TOKEN>`
- **URL Parameter**: `file_id` (UUID)
- **Response** (`200 OK`):
```json
{
  "file_id": "8f3b2a1c-9d4e-4f5a-8b2c-1d3e4f5a6b7c",
  "status": "completed",
  "total_chunks": 14
}
```

### `GET /files`
- **Headers**: `Authorization: Bearer <TOKEN>`
- **Response** (`200 OK`):
```json
[
  {
    "id": "8f3b2a1c-9d4e-4f5a-8b2c-1d3e4f5a6b7c",
    "name": "sample_document.txt",
    "path": "files/8f3b2a1c..._sample_document.txt",
    "type": ".txt",
    "created_at": "2026-08-07T05:00:00+00:00"
  }
]
```

---

## 4. RAG Chat Sessions

### `POST /chat/session`
- **Headers**: `Authorization: Bearer <TOKEN>`
- **Content-Type**: `application/json`
- **Body**:
```json
{
  "file_id": "8f3b2a1c-9d4e-4f5a-8b2c-1d3e4f5a6b7c",
  "title": "Architecture Q&A"
}
```
- **Response** (`201 Created`):
```json
{
  "session_id": "e2f1a3b4-5c6d-7e8f-9a0b-1c2d3e4f5a6b",
  "file_id": "8f3b2a1c-9d4e-4f5a-8b2c-1d3e4f5a6b7c",
  "title": "Architecture Q&A",
  "created_at": "2026-08-07T05:05:00+00:00"
}
```

### `GET /chat/sessions/{file_id}`
- **Headers**: `Authorization: Bearer <TOKEN>`
- **URL Parameter**: `file_id` (UUID)
- **Response** (`200 OK`):
```json
[
  {
    "id": "e2f1a3b4-5c6d-7e8f-9a0b-1c2d3e4f5a6b",
    "file_id": "8f3b2a1c-9d4e-4f5a-8b2c-1d3e4f5a6b7c",
    "user_id": "c56a4180-65aa-42ec-a945-5fd21dec0538",
    "title": "Architecture Q&A",
    "created_at": "2026-08-07T05:05:00+00:00"
  }
]
```

### `GET /chat/sessions`
- **Headers**: `Authorization: Bearer <TOKEN>`
- **Response** (`200 OK`): Lists all active chat sessions for the authenticated user.

### `GET /chat/session/{session_id}/messages`
- **Headers**: `Authorization: Bearer <TOKEN>`
- **URL Parameter**: `session_id` (UUID)
- **Response** (`200 OK`):
```json
{
  "session_id": "e2f1a3b4-5c6d-7e8f-9a0b-1c2d3e4f5a6b",
  "messages": [
    {
      "id": "a1b2c3d4-...",
      "session_id": "e2f1a3b4-...",
      "role": "user",
      "content": "What is the NATS JetStream retention policy?",
      "created_at": "2026-08-07T05:06:00+00:00"
    },
    {
      "id": "e5f6g7h8-...",
      "session_id": "e2f1a3b4-...",
      "role": "assistant",
      "content": "NATS JetStream uses interest-based retention...",
      "created_at": "2026-08-07T05:06:01+00:00"
    }
  ]
}
```

### `POST /chat/session/{session_id}` (RAG Stream)
- **Headers**: `Authorization: Bearer <TOKEN>`
- **Content-Type**: `application/json`
- **URL Parameter**: `session_id` (UUID)
- **Body**:
```json
{
  "query": "Summarize the key points in this architecture document."
}
```
- **Response** (`200 OK` - Server-Sent Events Stream `text/event-stream`):
```
data: The system architecture outlines three core tiers:

data:  NATS JetStream for event-driven message queuing,

data:  PostgreSQL with pgvector for HNSW similarity indexing,

data:  and Redis for hot-cache history management.
```
