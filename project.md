# FastAPI + AI (RAG) Backend Project

## Problem Statement
Build a FastAPI backend demonstrating solid backend engineering practices and implementing a Retrieval-Augmented Generation (RAG) pipeline.

## System Architecture & Guidelines
- **Framework**: FastAPI (clean, modular structure in `Backend/src/`: routes, services, Schema, events, middleware, templates, utils, config, Config)
- **Reverse Proxy & Edge Rate Limiting**: Nginx (`nginx:alpine` in Docker Compose) serving as API Gateway / Reverse Proxy on port `80`, enforcing IP rate limiting (`10r/s` general API burst 20, `15r/m` chat streaming burst 5) with custom JSON 429 responses and unbuffered SSE streaming (`proxy_buffering off`)
- **Design Pattern**: Functional architecture (classes are used exclusively for models and schemas in `src/Schema/` and `src/events/schema/`; services, event handlers, routes, middleware, and utilities use standalone functions)
- **Message Broker**: NATS JetStream (`FILES_STREAM` for upload/embed, dedicated `CHAT_STREAM` for `chat.messages` micro-batching)
- **Parallel Upload Pipeline**: Upload router splits raw file event (`files.upload`) and in-memory chunk events (`files.embed`), publishing both concurrently via `asyncio.gather()`
- **File Processing Status Endpoint**: `GET /files/{file_id}/status` returns current processing status (`queued`, `processing`, `completed`) and `total_chunks` count
- **Database & Storage**: Supabase (PostgreSQL with `pgvector` extension for `document_chunks` table & Supabase Storage for text files, bucket name `files`)
- **SQL Migrations Directory**: [Backend/migrations/](file:///Users/utkarshmani/Desktop/GitHub/BC06/Backend/migrations/) containing modular migration DDL files with explicit B-tree and HNSW indexes:
  - [01_auth.sql](file:///Users/utkarshmani/Desktop/GitHub/BC06/Backend/migrations/01_auth.sql) (`users` table + username/email B-tree indexes)
  - [02_files_and_embeddings.sql](file:///Users/utkarshmani/Desktop/GitHub/BC06/Backend/migrations/02_files_and_embeddings.sql) (`pgvector`, `files` user_id index, `document_chunks` 1024-dim `vector` & HNSW vector_cosine_ops index, `match_document_chunks` RPC)
  - [03_chat.sql](file:///Users/utkarshmani/Desktop/GitHub/BC06/Backend/migrations/03_chat.sql) (`chat_sessions` user/file index, `chat_messages` session/created_at index)
  - [04_error_logs.sql](file:///Users/utkarshmani/Desktop/GitHub/BC06/Backend/migrations/04_error_logs.sql) (`error_logs` timestamp/user_id indexes)
- **Embedding Model**: Google GenAI SDK `gemini-embedding-001` (1024 dimensions) via `GEMINI_API_KEY` with fallback to HF Inference API
- **LLM & Context Caching**: Google Gemini SDK (`google-genai` `gemini-3.1-flash-lite`) with native `CachedContent` per file for static system instruction prompts
- **Direct Conversational Persona**: Prompt template `system_prompt.j2` instructs the LLM to deliver direct, natural answers without meta-phrases or self-referential intros ("The document states...", "I contain...")
- **Jinja2 Prompt Templating**: `system_prompt.j2` (static direct conversational instruction) and `context_prompt.j2` (dynamic RAG context + conversation history + user query)
- **Conversation-Aware Consecutive Duplicate Caching**: `get_consecutive_duplicate_response()` in `chat_service.py` detects back-to-back duplicate queries without intervening context shifts, serving cached assistant responses directly (0 LLM cost)
- **Vector Search Caching**: Redis caching in `search_similar_chunks()` (`chat:chunks_cache:{file_id}:{vec_hash}`) to skip repetitive pgvector queries
- **File List Redis Caching & Eviction**: `get_user_files_cached()` in `file_service.py` caches `GET /files` under `files:user:{user_id}` (30m TTL), automatically evicted via `evict_user_files_cache()` when a user uploads a new file
- **Redis Hot-Read Cache & Eviction**: Instant zero-latency chat history reads from Redis list `chat:{session_id}:messages`; Redis caching for session queries (`chat:session:{session_id}`, `chat:user:{user_id}:sessions`, `chat:file:{file_id}:user:{user_id}:sessions`) with automatic cache eviction on `create_session`
- **NATS Micro-Batching**: Async NATS worker micro-batches chat messages into Supabase DB every 2 min or 100 messages
- **Authentication**: JWT authentication with password hashing (native `bcrypt` functions with 72-byte truncation, `python-jose`, `email-validator`)
- **JWT Verification Middleware**: Global HTTP middleware (`src/middleware/auth.py`) enforcing JWT Bearer token authentication on all protected routes, populating `request.state.user` (`id`, `username`, `email`)
- **Custom Exception Middleware**: Global HTTP middleware (`src/middleware/exception.py`) catching unhandled exceptions and logging 4xx/5xx HTTP errors (`timestamp`, `endpoint`, `http_method`, `error_message`, `stack_trace`, `ip_address`, `user_id`) to Supabase `error_logs` table
- **AI/RAG Pipeline**: Document ingestion via NATS pub/sub, chunking, vector embedding generation via Google GenAI SDK & storage in `document_chunks` (`pgvector`), Top-K similarity search, and SSE streaming chat response (`POST /chat/session/{session_id}`)

---

## Core Requirements & Progress
1. **Authentication**: [DONE] JWT Signup (`/auth/signup`) & Login (`/auth/login`) endpoints with password hashing, functional `auth_service`, and global JWT verification middleware.
2. **Database & Indexing**: [DONE] Supabase (PostgreSQL + `pgvector`) client configured in `src/utils/database.py`.
3. **Document Ingestion Endpoint**: [DONE] Parallel event-driven file upload & chunk embedding pipeline (`POST /files/upload` returning `file_id`, `GET /files/{file_id}/status`, `GET /files` with Redis caching & upload eviction -> `asyncio.gather` pub to `files.upload` & `files.embed` -> raw file worker + Google GenAI `gemini-embedding-001` worker).
4. **Chat Endpoint (`/chat`)**: [DONE] File-scoped chat sessions (`POST /chat/session`, `GET /chat/sessions/{file_id}`, `GET /chat/sessions`, `GET /chat/session/{session_id}/messages`, `POST /chat/session/{session_id}`) with Top-K `pgvector` similarity search, Jinja2 prompt rendering, Gemini Context Caching, conversation-aware consecutive duplicate response caching, vector search caching, SSE streaming, Redis hot-cache with session eviction, and NATS micro-batching.
5. **Exception Middleware**: [DONE] Global error handler catching unhandled exceptions & 4xx HTTP responses, logging telemetry (`ip_address`, `stack_trace`, `user_id`, etc.) to `error_logs` DB table, and returning standardized 500 JSON responses.
6. **Project Structure**: [DONE] Modular structure created in `Backend/src/` (`config.py`, `main.py`, `Config/`, `events/`, `middleware/`, `templates/`, `Schema/`, `services/`, `utils/`, `routes/`).

---

## TODO Checklist

### Core Tasks
- [x] Initialize project structure in `src/` (`routes`, `services`, `Schema`, `events`, `middleware`, `templates`, `utils`, `Config`, `config.py`, `main.py`).
- [x] Refactor architecture to standalone functions (classes restricted to `Schema/` & `events/schema/`).
- [x] Configure Supabase Database client & PostgreSQL User models.
- [x] Implement Password Hashing & JWT Auth (Signup & Login endpoints, auth service, security utility).
- [x] Implement JWT Verification Middleware (`src/middleware/auth.py`).
- [x] Configure `gemini-embedding-001` in `src/services/embedding_service.py`.
- [x] Configure NATS & JetStream setup in `src/Config/nats.py` (`FILES_STREAM` & `CHAT_STREAM`).
- [x] Configure Redis in `src/Config/redis.py`.
- [x] Implement File Upload Router (`POST /files/upload` with `file_id`, `GET /files/{file_id}/status`, `GET /files` with Redis caching & eviction).
- [x] Implement NATS Parallel Event Pipeline (`events/schema`, `events/publisher`, `events/subscriber`).
- [x] Implement File Storage Service saving text files to Supabase Storage & DB.
- [x] Implement Chunking & Google GenAI Embedding Service (`embed_text`, `to_pgvector`, `document_chunks` table).
- [x] Implement Jinja2 Prompt Templates (`system_prompt.j2`, `context_prompt.j2` with direct conversational persona).
- [x] Implement Gemini SDK (`google-genai` `gemini-3.1-flash-lite`) with streaming & Context Caching.
- [x] Implement `get_consecutive_duplicate_response()` Conversation-Aware Caching.
- [x] Implement Vector Search Caching in `search_similar_chunks()`.
- [x] Implement Redis Hot-Cache (with session caching & eviction) & NATS Micro-Batching Chat Message Writer.
- [x] Implement RAG Chat Endpoints (`POST /chat/session`, `GET /chat/sessions/{file_id}`, `GET /chat/sessions`, `GET /chat/session/{session_id}/messages`, `POST /chat/session/{session_id}`).
- [x] Implement Custom Exception Middleware (`src/middleware/exception.py` logging all 4xx HTTP responses + 500 crashes + `ip_address` to `error_logs` DB table).
- [x] Create `migrations/` directory with modular SQL migration files (`01_auth.sql`, `02_files_and_embeddings.sql`, `03_chat.sql`, `04_error_logs.sql`) and explicit indexes.
- [x] Write `.env.example` and update `.env`.
- [x] Write `README.md` (setup instructions, indexing choices).

### Good to Have
- [x] **Redis**: Hot-cache for chat history, file lists, vector search cache, and active session memory with eviction on new session/file creation.
- [x] **Kafka / Message Broker**: NATS JetStream implemented for file upload, chunk embedding, and chat micro-batching.
- [x] **Docker & Docker Compose**: `Dockerfile` + `docker-compose.yml` + `nginx/nginx.conf` for reverse proxy, rate limiting, backend, NATS+JetStream, and Redis.
- [x] **Background Jobs**: Async NATS background workers for storage, embeddings, and chat batch inserts.
- [x] **Streaming LLM Responses**: Server-Sent Events (SSE) `StreamingResponse` for `/chat`.
- [x] **Unit Tests**: Test suite using `pytest` & `httpx` (`tests/test_unit.py` and `tests/test_routes.py` passing 9 tests).
