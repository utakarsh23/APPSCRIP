# FastAPI + AI (RAG) Backend Project

## Problem Statement
Build a FastAPI backend demonstrating solid backend engineering practices and implementing a Retrieval-Augmented Generation (RAG) pipeline.

## System Architecture & Guidelines
- **Framework**: FastAPI (clean, modular structure in `Backend/src/`: routes, services, Schema, events, middleware, templates, utils, config, Config)
- **Design Pattern**: Functional architecture (classes are used exclusively for models and schemas in `src/Schema/` and `src/events/schema/`; services, event handlers, routes, middleware, and utilities use standalone functions)
- **Message Broker**: NATS JetStream (`FILES_STREAM` for upload/embed, dedicated `CHAT_STREAM` for `chat.messages` micro-batching)
- **Parallel Upload Pipeline**: Upload router splits raw file event (`files.upload`) and in-memory chunk events (`files.embed`), publishing both concurrently via `asyncio.gather()`
- **Database & Storage**: Supabase (PostgreSQL with `pgvector` extension for `document_chunks` table & Supabase Storage for text files)
- **Embedding Model**: `Qwen/Qwen3-Embedding-8B` via Hugging Face `InferenceClient` (`feature_extraction`) using `settings.HF_TOKEN`
- **LLM & Context Caching**: Google Gemini SDK (`google-genai`) with native `CachedContent` per file for static system instruction prompts
- **Jinja2 Prompt Templating**: `system_prompt.j2` (static context instruction) and `context_prompt.j2` (dynamic RAG context + conversation history + user query)
- **Conversation-Aware Consecutive Duplicate Caching**: `get_consecutive_duplicate_response()` in `chat_service.py` detects back-to-back duplicate queries without intervening context shifts, serving cached assistant responses directly (0 LLM cost)
- **Vector Search Caching**: Redis caching in `search_similar_chunks()` (`chat:chunks_cache:{file_id}:{vec_hash}`) to skip repetitive pgvector queries
- **File List Redis Caching & Eviction**: `get_user_files_cached()` in `file_service.py` caches `GET /files` under `files:user:{user_id}` (30m TTL), automatically evicted via `evict_user_files_cache()` when a user uploads a new file
- **Redis Hot-Read Cache & Eviction**: Instant zero-latency chat history reads from Redis list `chat:{session_id}:messages`; Redis caching for session queries (`chat:session:{session_id}`, `chat:user:{user_id}:sessions`, `chat:file:{file_id}:user:{user_id}:sessions`) with automatic cache eviction on `create_session`
- **NATS Micro-Batching**: Async NATS worker micro-batches chat messages into Supabase DB every 2 min or 100 messages
- **Authentication**: JWT authentication with password hashing (`passlib` + `bcrypt`, `python-jose`)
- **JWT Verification Middleware**: Global HTTP middleware (`src/middleware/auth.py`) enforcing JWT Bearer token authentication on all protected routes, populating `request.state.user` (`id`, `username`, `email`)
- **AI/RAG Pipeline**: Document ingestion via NATS pub/sub, chunking, vector embedding generation via HF Inference API & storage in `document_chunks` (`pgvector`), Top-K similarity search, and SSE streaming chat response (`POST /chat/session/{session_id}`)
- **Middleware**: Custom exception-handling middleware logging errors to DB (timestamp, endpoint, HTTP method, error message, stack trace, user ID) returning standardized JSON error responses

---

## Core Requirements & Progress
1. **Authentication**: [DONE] JWT Signup (`/auth/signup`) & Login (`/auth/login`) endpoints with password hashing, functional `auth_service`, and global JWT verification middleware.
2. **Database & Indexing**: [DONE] Supabase (PostgreSQL + `pgvector`) client configured in `src/utils/database.py`.
3. **Document Ingestion Endpoint**: [DONE] Parallel event-driven file upload & chunk embedding pipeline (`POST /files/upload`, `GET /files` with Redis caching & upload eviction -> `asyncio.gather` pub to `files.upload` & `files.embed` -> raw file worker + HF Inference Qwen embedding worker).
4. **Chat Endpoint (`/chat`)**: [DONE] File-scoped chat sessions (`POST /chat/session`, `GET /chat/sessions/{file_id}`, `GET /chat/sessions`, `GET /chat/session/{session_id}/messages`, `POST /chat/session/{session_id}`) with Top-K `pgvector` similarity search, Jinja2 prompt rendering, Gemini Context Caching, conversation-aware consecutive duplicate response caching, vector search caching, SSE streaming, Redis hot-cache with session eviction, and NATS micro-batching.
5. **Exception Middleware**: [PENDING] Global error handler catching unhandled exceptions and logging to DB.
6. **Project Structure**: [DONE] Modular structure created in `Backend/src/` (`config.py`, `main.py`, `Config/`, `events/`, `middleware/`, `templates/`, `Schema/`, `services/`, `utils/`, `routes/`).

---

## TODO Checklist

### Core Tasks
- [x] Initialize project structure in `src/` (`routes`, `services`, `Schema`, `events`, `middleware`, `templates`, `utils`, `Config`, `config.py`, `main.py`).
- [x] Refactor architecture to standalone functions (classes restricted to `Schema/` & `events/schema/`).
- [x] Configure Supabase Database client & PostgreSQL User models.
- [x] Implement Password Hashing & JWT Auth (Signup & Login endpoints, auth service, security utility).
- [x] Implement JWT Verification Middleware (`src/middleware/auth.py`).
- [x] Configure `Qwen/Qwen3-Embedding-8B` & `HF_TOKEN` in `src/config.py`.
- [x] Configure NATS & JetStream setup in `src/Config/nats.py` (`FILES_STREAM` & `CHAT_STREAM`).
- [x] Configure Redis in `src/Config/redis.py`.
- [x] Implement File Upload Router (`POST /files/upload` & `GET /files` with Redis caching & eviction).
- [x] Implement NATS Parallel Event Pipeline (`events/schema`, `events/publisher`, `events/subscriber`).
- [x] Implement File Storage Service saving text files to Supabase Storage & DB.
- [x] Implement Chunking & Hugging Face Inference API Qwen Embedding Service (`embed_text`, `to_pgvector`, `document_chunks` table).
- [x] Implement Jinja2 Prompt Templates (`system_prompt.j2`, `context_prompt.j2`).
- [x] Implement Gemini SDK (`google-genai`) with streaming & Context Caching.
- [x] Implement `get_consecutive_duplicate_response()` Conversation-Aware Caching.
- [x] Implement Vector Search Caching in `search_similar_chunks()`.
- [x] Implement Redis Hot-Cache (with session caching & eviction) & NATS Micro-Batching Chat Message Writer.
- [x] Implement RAG Chat Endpoints (`POST /chat/session`, `GET /chat/sessions/{file_id}`, `GET /chat/sessions`, `GET /chat/session/{session_id}/messages`, `POST /chat/session/{session_id}`).
- [ ] Implement Custom Exception Middleware (DB logging for errors + standardized JSON response).
- [ ] Write `README.md` (setup instructions, indexing choices) and `.env.example`.

### Good to Have
- [x] **Redis**: Hot-cache for chat history, file lists, vector search cache, and active session memory with eviction on new session/file creation.
- [x] **Kafka / Message Broker**: NATS JetStream implemented for file upload, chunk embedding, and chat micro-batching.
- [ ] **Docker & Docker Compose**: Containerization for app, DB, and services.
- [x] **Background Jobs**: Async NATS background workers for storage, embeddings, and chat batch inserts.
- [x] **Streaming LLM Responses**: Server-Sent Events (SSE) `StreamingResponse` for `/chat`.
- [ ] **Unit Tests**: Test suite using `pytest` & `httpx` for routes and services.
