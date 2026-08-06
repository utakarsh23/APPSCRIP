# FastAPI + AI (RAG) Backend Project

## Problem Statement
Build a FastAPI backend demonstrating solid backend engineering practices and implementing a Retrieval-Augmented Generation (RAG) pipeline.

## System Architecture & Guidelines
- **Framework**: FastAPI (clean, modular structure in `Backend/src/`: routes, services, Schema, events, middleware, utils, config, Config)
- **Design Pattern**: Functional architecture (classes are used exclusively for models and schemas in `src/Schema/` and `src/events/schema/`; services, event handlers, routes, middleware, and utilities use standalone functions)
- **Message Broker**: NATS JetStream (`FILES_STREAM` stream, `files.upload` & `files.embed` subjects)
- **Parallel Pipeline**: Upload router splits raw file event (`files.upload`) and in-memory chunk events (`files.embed`), publishing both concurrently via `asyncio.gather()`
- **Database & Storage**: Supabase (PostgreSQL with `pgvector` extension for `document_chunks` table & Supabase Storage for text files)
- **Embedding Model**: `Qwen/Qwen3-Embedding-8B` via Hugging Face `InferenceClient` (`feature_extraction`) using `settings.HF_TOKEN`
- **Authentication**: JWT authentication with password hashing (`passlib` + `bcrypt`, `python-jose`)
- **JWT Verification Middleware**: Global HTTP middleware (`src/middleware/auth.py`) enforcing JWT Bearer token authentication on all protected routes, populating `request.state.user` (`id`, `username`, `email`)
- **AI/RAG Pipeline**: Text document ingestion via NATS pub/sub, chunking, vector embedding generation via HF Inference API & storage in `document_chunks` (`pgvector`), vector similarity search, and LLM query generation (`/chat` endpoint)
- **Middleware**: Custom exception-handling middleware logging errors to DB (timestamp, endpoint, HTTP method, error message, stack trace, user ID) returning standardized JSON error responses

---

## Core Requirements & Progress
1. **Authentication**: [DONE] JWT Signup (`/auth/signup`) & Login (`/auth/login`) endpoints with password hashing, functional `auth_service`, and global JWT verification middleware.
2. **Database & Indexing**: [DONE] Supabase (PostgreSQL + `pgvector`) client configured in `src/utils/database.py`.
3. **Document Ingestion Endpoint**: [DONE] Parallel event-driven file upload & chunk embedding pipeline (`POST /files/upload` -> `asyncio.gather` pub to `files.upload` & `files.embed` -> raw file worker + HF Inference Qwen embedding worker).
4. **Chat Endpoint (`/chat`)**: [PENDING] Vector similarity search over stored chunks in PostgreSQL (`pgvector`), construct RAG prompt, call LLM, return answer.
5. **Exception Middleware**: [PENDING] Global error handler catching unhandled exceptions and logging to DB.
6. **Project Structure**: [DONE] Modular structure created in `Backend/src/` (`config.py`, `main.py`, `Config/`, `events/`, `middleware/`, `Schema/`, `services/`, `utils/`, `routes/`).

---

## TODO Checklist

### Core Tasks
- [x] Initialize project structure in `src/` (`routes`, `services`, `Schema`, `events`, `middleware`, `utils`, `Config`, `config.py`, `main.py`).
- [x] Refactor architecture to standalone functions (classes restricted to `Schema/` & `events/schema/`).
- [x] Configure Supabase Database client & PostgreSQL User models.
- [x] Implement Password Hashing & JWT Auth (Signup & Login endpoints, auth service, security utility).
- [x] Implement JWT Verification Middleware (`src/middleware/auth.py`).
- [x] Configure `Qwen/Qwen3-Embedding-8B` & `HF_TOKEN` in `src/config.py`.
- [x] Configure NATS & JetStream setup in `src/Config/nats.py`.
- [x] Implement File Upload Router (`POST /files/upload` extracting authenticated `user_id` from JWT state).
- [x] Implement NATS Parallel Event Pipeline (`events/schema`, `events/publisher`, `events/subscriber`).
- [x] Implement File Storage Service saving text files to Supabase Storage & DB.
- [x] Implement Chunking & Hugging Face Inference API Qwen Embedding Service (`embed_text`, `to_pgvector`, `document_chunks` table).
- [ ] Implement Custom Exception Middleware (DB logging for errors + standardized JSON response).
- [ ] Implement `/chat` Endpoint (vector retrieval + LLM query answer).
- [ ] Write `README.md` (setup instructions, indexing choices) and `.env.example`.

### Good to Have
- [ ] **Redis**: Caching embeddings/responses or session management.
- [x] **Kafka / Message Broker**: NATS JetStream implemented for file upload & ingestion pipeline.
- [ ] **Docker & Docker Compose**: Containerization for app, DB, and services.
- [ ] **Background Jobs**: Async NATS background worker for document processing.
- [ ] **Streaming LLM Responses**: Server-Sent Events (SSE) or WebSocket / StreamingResponse for `/chat`.
- [ ] **Unit Tests**: Test suite using `pytest` & `httpx` for routes and services.
