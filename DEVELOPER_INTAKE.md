# Developer Intake & Future Architectural Roadmap

This document outlines potential future architectural enhancements and high-ROI features for scaling and improving the RAG pipeline.

---

## 1. High-Throughput Upload Staging via Redis Queue (FIFO Buffer)

### Problem
During massive burst traffic (e.g., 1,000+ concurrent user file uploads), issuing direct network I/O calls to cloud storage (Supabase Storage) and database tables creates connection pool exhaustion and network bottlenecks.

### Proposed Solution
- **In-Memory FIFO Buffer**: When a user uploads a file, store the raw payload immediately in Redis using Redis Streams or a FIFO List (`RPUSH`) with a sub-millisecond response time.
- **Asynchronous Worker Consumption**: Background NATS/Celery workers consume items from the FIFO queue (`LPOP`), upload raw files to object storage, chunk text, generate vector embeddings, and delete the item from Redis once successfully processed.
- **Benefit**: Absorbs extreme write spikes without dropping incoming client requests or overloading persistent database storage.

---

## 2. Post-Retrieval: Cross-Encoder Reranking

### Problem
Bi-encoder embedding models (such as `gemini-embedding-001` or `Qwen/Qwen3-Embedding-8B`) are fast at scanning millions of vectors using cosine similarity, but vector proximity alone can sometimes rank mildly relevant chunks above exact matches.

### Proposed Solution: Two-Stage Retrieval Pipeline
1. **Coarse Candidate Retrieval**: Retrieve a wider pool of candidate chunks (`top_k = 20`) from the PostgreSQL `pgvector` HNSW index.
2. **Cross-Encoder Rescoring**: Pass the user query and the 20 candidate chunks through a dedicated Cross-Encoder Reranker (e.g., `BAAI/bge-reranker-v2-m3` via Hugging Face Inference API).
3. **Context Selection**: Select the top 3–5 highest-scoring chunks after reranking to feed into the Gemini LLM context prompt.
- **Benefit**: Significantly improves answer precision and eliminates irrelevant context without sacrificing search speed.

---

## 3. Storage Efficiency: File Compression vs. Post-Processing Eviction

### Problem & Redundancy
Storing raw text files in cloud storage (Supabase Storage) while simultaneously storing chunk text inside the `document_chunks` database table creates storage redundancy and increases storage costs over time.

### Proposed Solutions
- **Option A: Post-Processing Eviction (Default Recommendation)**: Once NATS workers finish chunking, embedding, and inserting all text chunks into `document_chunks`, issue an async deletion call to remove the raw file from Supabase Storage. The chunk records in PostgreSQL serve as the sole source of truth for RAG queries.
- **Option B: Compression Before Upload (Gzip / Zstandard)**: If raw document retention is mandatory for user downloads, compress raw file payloads using `zstd` or `gzip` (60–80% compression ratio for text) before writing to object storage, decompressing only when explicit full document downloads are triggered.

---

## 4. Architectural Note: Docker Compose vs. Kubernetes

### Decision Rationale
Kubernetes was intentionally omitted in favor of Docker Compose for the following reasons:
- **Scope & Complexity**: The current system runs as a clean FastAPI application stack with Nats, Redis, and Nginx. Introducing a Kubernetes cluster (Ingress Controllers, etcd, PVCs, HPA) adds heavy operational overhead without concrete scaling metrics.
- **Resource Efficiency**: Docker Compose with Nginx edge rate limiting and health checks provides container isolation, zero orchestration overhead, and single-command deployment (`docker compose up --build`).

---

## 5. Hybrid Search (Keyword BM25 + Vector Cosine with RRF)

### Problem
Dense vector embeddings excel at semantic concepts, but can miss exact keyword matches like technical model numbers, serial codes, or rare domain terminology (e.g., `NATS-JS-4222`).

### Proposed Solution
- Combine PostgreSQL Full-Text Search (`tsvector` / `tsquery`) with `pgvector` HNSW similarity search.
- Use **Reciprocal Rank Fusion (RRF)** to combine the keyword rankings and vector rankings:
  $$\text{RRF Score}(d) = \sum_{m \in M} \frac{1}{k + r_m(d)}$$
- **Benefit**: Retrieves exact domain terms while maintaining deep semantic understanding.
