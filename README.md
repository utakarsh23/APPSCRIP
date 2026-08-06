# FastAPI + AI (RAG) Backend

A production-grade FastAPI backend that lets users upload text documents, have them chunked and embedded into vectors, and then chat with those documents using a Retrieval-Augmented Generation pipeline — all powered by Google Gemini, NATS JetStream, Redis, and PostgreSQL with pgvector.

---

## What This Does

1. **Upload a document** → it gets split into chunks, each chunk gets embedded into a 1024-dimensional vector using Google's `gemini-embedding-001`, and stored alongside the raw text in Supabase (PostgreSQL + pgvector).

2. **Ask questions about it** → your query gets embedded, the system finds the most relevant chunks via cosine similarity search (HNSW index), feeds them as context into Gemini `3.1 Flash Lite`, and streams the answer back to you in real-time via Server-Sent Events.

3. **Everything in between** is designed to be fast — Redis caches chat history, session lookups, file lists, and even repeated vector searches. NATS JetStream handles the async pipeline so uploads don't block, and chat messages get micro-batched into the database every 2 minutes instead of one-by-one.

---

## Architecture Overview

```
Client
  │
  ├── POST /auth/signup, /auth/login  →  JWT token
  │
  ├── POST /files/upload  →  file_id + "queued" status
  │       │
  │       ├── NATS: files.upload  →  File Worker (stores raw file in Supabase Storage + DB)
  │       └── NATS: files.embed   →  Chunk Worker (embeds each chunk via Gemini → pgvector)
  │
  ├── GET  /files/{file_id}/status  →  processing status + chunk count
  ├── GET  /files                   →  list user files (Redis cached)
  │
  ├── POST /chat/session            →  create a chat session tied to a file
  ├── GET  /chat/sessions/{file_id} →  list sessions for a file
  ├── GET  /chat/sessions           →  list all user sessions
  ├── GET  /chat/session/{id}/messages → get conversation history
  │
  └── POST /chat/session/{id}       →  SSE streaming RAG response
          │
          ├── Embed query → pgvector Top-K similarity search (Redis cached)
          ├── Jinja2 prompt rendering (context + history + query)
          ├── Gemini streaming response (with Context Caching per file)
          ├── Redis hot-cache write (message history)
          └── NATS: chat.messages → Batch Writer (flushes to DB every 2min / 100 msgs)
```

---

## Project Structure

```
Backend/
├── .env.example
├── requirements.txt
├── migrations/
│   ├── 01_auth.sql
│   ├── 02_files_and_embeddings.sql
│   ├── 03_chat.sql
│   └── 04_error_logs.sql
└── src/
    ├── config.py              # Pydantic settings (env vars)
    ├── main.py                # FastAPI app, lifespan, middleware, router registration
    ├── Config/
    │   ├── database.py        # Supabase client
    │   ├── nats.py            # NATS JetStream connection + streams
    │   └── redis.py           # Redis connection
    ├── Schema/
    │   ├── user.py            # User Pydantic model
    │   ├── File.py            # File Pydantic model
    │   ├── FileIO.py          # Upload/status request/response models
    │   ├── Chat.py            # Chat session & message models
    │   └── ChatIO.py          # Chat request/response models
    ├── routes/
    │   ├── auth.py            # /auth/signup, /auth/login
    │   ├── file.py            # /files/upload, /files, /files/{id}/status
    │   └── chat.py            # /chat/session, /chat/sessions, /chat/session/{id}
    ├── services/
    │   ├── auth_service.py    # Signup/login logic
    │   ├── file_service.py    # File queries, Redis caching, status check
    │   ├── embedding_service.py  # Gemini embeddings + pgvector insert
    │   ├── chat_service.py    # Sessions, messages, similarity search, duplicate caching
    │   └── llm_service.py     # Gemini SDK, Jinja2 rendering, Context Caching, streaming
    ├── events/
    │   ├── schema/            # FileUploadEventPayload, FileChunkEventPayload, ChatMessageEventPayload
    │   ├── publisher/         # NATS publish functions
    │   └── subscriber/        # NATS workers (file_subscriber, chunk_subscriber, chat_subscriber)
    ├── middleware/
    │   ├── auth.py            # JWT verification middleware
    │   └── exception.py       # Global error logging middleware (4xx + 5xx → error_logs table)
    ├── templates/
    │   ├── system_prompt.j2   # System instruction (conversational persona)
    │   └── context_prompt.j2  # Dynamic RAG context + history + query
    └── utils/
        ├── security.py        # Password hashing (bcrypt), JWT encode/decode
        └── chunking.py        # Text chunking logic
```

---

## Getting Started

### Prerequisites

- Python 3.12+
- A [Supabase](https://supabase.com) project (free tier works)
- [NATS Server](https://nats.io) with JetStream enabled
- [Redis](https://redis.io)
- A [Google AI Studio](https://aistudio.google.com) API key (for Gemini)

### 1. Clone & Install

```bash
git clone https://github.com/your-username/BC06.git
cd BC06/Backend

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Open `.env` and fill in your actual values:

| Variable | What It Is |
|---|---|
| `SECRET_KEY` | Any random string for signing JWTs |
| `SUPABASE_URL` | Your Supabase project URL |
| `SUPABASE_KEY` | Supabase `service_role` key (found in Project Settings → API) |
| `GEMINI_API_KEY` | Google AI Studio API key |
| `GEMINI_MODEL` | Chat model to use (default: `gemini-3.1-flash-lite`) |
| `HF_TOKEN` | HuggingFace token (optional fallback for embeddings) |
| `NATS_URL` | NATS server URL (default: `nats://localhost:4222`) |
| `REDIS_URL` | Redis URL (default: `redis://localhost:6379`) |

### 3. Run Database Migrations

Go to your Supabase Dashboard → SQL Editor and run the migration files in order:

1. `migrations/01_auth.sql`
2. `migrations/02_files_and_embeddings.sql`
3. `migrations/03_chat.sql`
4. `migrations/04_error_logs.sql`

### 4. Start Infrastructure & Server

You can run the entire system (FastAPI, NATS JetStream, and Redis) either with Docker Compose or manually.

#### Option A: Docker Compose (Recommended)

Ensure `Backend/.env` has your Supabase and Gemini keys set, then run:

```bash
docker compose up --build
```

This starts:
- **NATS JetStream** (`nats:2.10-alpine`) on `4222` with HTTP stats on `8222`
- **Redis** (`redis:7-alpine`) on `6379`
- **FastAPI Backend** (built from `Backend/Dockerfile`) on `8000`

Health checks ensure the backend starts only after NATS and Redis are healthy.

#### Option B: Manual Local Startup

In separate terminals:

```bash
# Terminal 1: NATS with JetStream
nats-server -js

# Terminal 2: Redis
redis-server

# Terminal 3: FastAPI Backend
cd Backend
source venv/bin/activate
uvicorn src.main:app --reload --port 8000
```

Hit `http://localhost:8000/health` — you should see `{"status": "ok", "environment": "development"}`.

---

## API Reference

### Auth

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/auth/signup` | Register a new user (`username`, `email`, `password`) |
| `POST` | `/auth/login` | Login and receive a JWT (`email`, `password`) |

### Files

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/files/upload` | Upload a `.txt` file (multipart form) → returns `file_id` |
| `GET` | `/files/{file_id}/status` | Check processing status (`queued` / `processing` / `completed`) |
| `GET` | `/files` | List all uploaded files for the authenticated user |

### Chat

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/chat/session` | Create a chat session tied to a `file_id` |
| `GET` | `/chat/sessions/{file_id}` | List chat sessions for a specific file |
| `GET` | `/chat/sessions` | List all chat sessions for the user |
| `GET` | `/chat/session/{session_id}/messages` | Get conversation history |
| `POST` | `/chat/session/{session_id}` | Send a query → SSE streaming RAG response |

All endpoints except `/auth/*` and `/health` require a `Authorization: Bearer <token>` header.

---

## Quick Test (curl)

```bash
# Sign up
curl -X POST http://localhost:8000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "email": "test@example.com", "password": "password123"}'

# Login (grab the token)
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "password123"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Upload a file
curl -X POST http://localhost:8000/files/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@your_document.txt"

# Check status (use the file_id from the upload response)
curl -X GET http://localhost:8000/files/<file_id>/status \
  -H "Authorization: Bearer $TOKEN"

# Create a chat session
SESSION_ID=$(curl -s -X POST http://localhost:8000/chat/session \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"file_id": "<file_id>", "title": "My Chat"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['session_id'])")

# Chat with your document (streaming)
curl -N -X POST http://localhost:8000/chat/session/$SESSION_ID \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "What are the key points?"}'
```

---

## Caching Strategy

There are multiple caching layers, each solving a different problem:

| Cache Key Pattern | What It Caches | TTL | Evicted When |
|---|---|---|---|
| `files:user:{user_id}` | `GET /files` response | 30 min | User uploads a new file |
| `chat:session:{session_id}` | Session metadata | 1 hour | — |
| `chat:user:{user_id}:sessions` | User's session list | 30 min | New session created |
| `chat:file:{file_id}:user:{user_id}:sessions` | File-scoped session list | 30 min | New session created |
| `chat:{session_id}:messages` | Conversation history (Redis list) | 1 hour | — |
| `chat:chunks_cache:{file_id}:{vec_hash}` | Vector similarity search results | 1 hour | — |
| **Consecutive duplicate detection** | Back-to-back identical queries | In-memory | Different query asked |

The consecutive duplicate detection is worth calling out — if a user sends the exact same query twice in a row, the system serves the cached assistant response immediately without hitting Gemini or pgvector at all. Zero LLM cost.

---

## Why HNSW Over IVFFlat?

Both are pgvector index types for approximate nearest-neighbor search. Here's why HNSW was chosen:

| Factor | HNSW | IVFFlat |
|---|---|---|
| **Query speed** | O(log N) — consistently fast | Depends on number of probes; can be slower |
| **Accuracy** | Higher recall out of the box | Needs careful tuning of `nlist` and `nprobes` |
| **Insert speed** | Slower builds | Faster builds |
| **Memory** | ~12–15 MB per 10k chunks (1024-dim) | Lower memory footprint |
| **Maintenance** | No retraining needed | Needs periodic `REINDEX` after large inserts |

For a RAG use case where query quality matters more than bulk insert speed, HNSW with `m=16` and `ef_construction=64` gives the best balance of recall and performance. The memory overhead is minimal at the scale this project operates at.

---

## Error Logging

Every HTTP error (4xx and 5xx) gets automatically logged to the `error_logs` table in Supabase by the global exception middleware. Each log entry captures:

- `timestamp`
- `endpoint` and `http_method`
- `error_message` and `stack_trace` (for 500s)
- `ip_address` (supports `X-Forwarded-For`)
- `user_id` (if authenticated)

This means rate limits, auth failures, bad requests, and server crashes all end up in one queryable table.

---

## NATS JetStream Design

Two streams handle different workloads:

**`FILES_STREAM`** — File processing pipeline
- `files.upload` → File worker stores the raw file in Supabase Storage and records metadata in the `files` table.
- `files.embed` → Chunk worker generates embeddings via Gemini and inserts them into `document_chunks`.
- Both events are published concurrently via `asyncio.gather()` so the upload response returns immediately.

**`CHAT_STREAM`** — Chat message persistence
- `chat.messages` → Batch writer accumulates messages in memory and flushes them to the `chat_messages` table every 2 minutes or every 100 messages, whichever comes first.
- This avoids hammering the database with individual inserts on every chat turn while Redis keeps the hot copy for instant reads.

---

## Tech Stack

| Component | Technology |
|---|---|
| Framework | FastAPI |
| Database | PostgreSQL (Supabase) + pgvector |
| Object Storage | Supabase Storage |
| Message Broker | NATS JetStream |
| Cache | Redis |
| Embeddings | Google GenAI `gemini-embedding-001` (1024-dim) |
| Chat LLM | Google Gemini `3.1 Flash Lite` |
| Auth | JWT (HS256) + bcrypt |
| Prompt Engine | Jinja2 |
