# NewsPulse — RSS-First Hybrid RAG News Chatbot

NewsPulse is a citation-grounded news chatbot that ingests RSS feeds, deduplicates articles, embeds and indexes them in a vector store, and answers user questions using Retrieval-Augmented Generation with inline source citations.

---

## Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Python | 3.11+ | Backend runtime |
| Node.js | 18+ | Frontend build |
| Google AI API key | — | Single key for Gemini LLM + embeddings |
| Qdrant | Cloud or local | Vector store for hybrid search |
| PostgreSQL (optional) | 14+ | Supabase recommended; SQLite used as fallback |

**No Docker required** — the app runs fully locally with SQLite + local Qdrant if you prefer.

---

## 1. Clone and Install

```bash
git clone <your-repo-url> && cd newspulse

# Backend
cd backend
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
# source venv/bin/activate

pip install -r requirements.txt

# Frontend
cd ../frontend
npm install
```

---

## 2. Environment Variables

Copy the template and fill in your keys:

```bash
cd backend
cp .env.example .env   # or just edit the existing .env
```

### Required

| Variable | Description |
|----------|-------------|
| `GOOGLE_API_KEY` | Google AI Studio API key (used for both embeddings and LLM) |
| `QDRANT_HOST` | Qdrant Cloud cluster URL (e.g. `abc123-xyz.us-east4-0.gcp.cloud.qdrant.io`) or `localhost` |
| `QDRANT_API_KEY` | Qdrant Cloud API key (leave empty for local Qdrant) |

### Optional

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL_SYNC` | `sqlite:///...backend/data/newspulse.db` | Set to Supabase Postgres URL for production (format: `postgresql://postgres:PASSWORD@db.PROJECT.supabase.co:5432/postgres`) |
| `QDRANT_PORT` | `6333` | Only used for local Qdrant |
| `QDRANT_COLLECTION` | `news_chunks` | Qdrant collection name |
| `EMBEDDING_MODEL` | `models/text-embedding-004` | Google embedding model |
| `EMBEDDING_DIM` | `768` | Must match embedding model output |
| `LLM_MODEL` | `gemini-2.0-flash` | Gemini model for RAG answers |
| `RERANKER_MODEL` | `BAAI/bge-reranker-base` | Cross-encoder reranker (downloaded on first use) |
| `DEFAULT_POLL_INTERVAL_MIN` | `15` | RSS poll interval in minutes |
| `SEMANTIC_DEDUP_THRESHOLD` | `0.92` | Cosine similarity threshold for Tier 2 dedup |
| `RATE_LIMIT_RPM` | `30` | Max requests per minute per IP |

---

## 3. Running — Development Mode

### Start the backend

```bash
cd backend
# Activate venv first
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend runs at `http://localhost:8000`. The database tables are auto-created on first request.

### Start the frontend

```bash
cd frontend
npm run dev
```

Frontend runs at `http://localhost:5173` with API calls proxied to port 8000.

---

## 4. Seed RSS Sources

```bash
cd newspulse
python scripts/seed_sources.py
```

This adds 5 default feeds: BBC News, TechCrunch, Reuters, Hacker News, NPR.

You can also add sources via the API:

```bash
curl -X POST http://localhost:8000/sources \
  -H "Content-Type: application/json" \
  -d '{"name": "Ars Technica", "feed_url": "https://feeds.arstechnica.com/arstechnica/index", "category": "technology"}'
```

---

## 5. Ingestion and Indexing

### Poll RSS feeds (fetch new articles)

```bash
curl -X POST http://localhost:8000/ingest/poll
```

### Index articles into Qdrant (chunk + embed + upsert)

```bash
curl -X POST http://localhost:8000/ingest/index
```

### Run both in one call

```bash
curl -X POST http://localhost:8000/ingest/run
```

The ingestion pipeline:
1. Polls all RSS feeds (respects ETag/Last-Modified)
2. Tier 1 dedup: URL normalization + SimHash on titles (hamming distance <= 10, 48h window)
3. Chunks article text (paragraph-aware, with overlap)
4. Embeds all chunks via Google `text-embedding-004`
5. Tier 2 dedup: checks first chunk embedding against Qdrant for semantic near-duplicates (cosine >= 0.92, 72h window)
6. Upserts to Qdrant with dense + BM25 sparse vectors
7. Stores chunk records in Postgres/SQLite

---

## 6. Chat (RAG Query)

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What happened in tech news today?", "category": "technology"}'
```

Response includes:
- `answer` — citation-grounded text with `[1]`, `[2]` markers
- `citations` — list of sources referenced (title, URL, snippet)
- `session_id` — for multi-turn conversations

### Chat history

```bash
curl http://localhost:8000/chat/{session_id}/history
```

---

## 7. End-to-End Verification

1. **Health check:**
   ```bash
   curl http://localhost:8000/health
   # → {"status": "ok"}
   ```

2. **Seed sources:**
   ```bash
   python scripts/seed_sources.py
   ```

3. **List sources:**
   ```bash
   curl http://localhost:8000/sources
   ```

4. **Poll feeds:**
   ```bash
   curl -X POST http://localhost:8000/ingest/poll
   # → {"new_articles": N}
   ```

5. **Index into Qdrant:**
   ```bash
   curl -X POST http://localhost:8000/ingest/index
   # → {"chunks_created": N}
   ```

6. **Ask a question:**
   ```bash
   curl -X POST http://localhost:8000/chat \
     -H "Content-Type: application/json" \
     -d '{"message": "Summarize today top headlines"}'
   ```

7. **Open frontend:**
   Visit `http://localhost:5173` — type a question, see citations rendered as clickable chips.

---

## 8. Production Deployment

### Using Supabase + Qdrant Cloud

1. Create a Supabase project and copy the Postgres connection string
2. Create a Qdrant Cloud cluster and get the URL + API key
3. Set in `.env`:
   ```
   DATABASE_URL_SYNC=postgresql://postgres:YOUR_PASS@db.YOUR_REF.supabase.co:5432/postgres
   QDRANT_HOST=your-cluster.region.cloud.qdrant.io
   QDRANT_API_KEY=your-qdrant-api-key
   GOOGLE_API_KEY=your-google-api-key
   ```
4. Tables are auto-created on first backend start

### Docker Compose (dev infrastructure only)

```bash
docker-compose up -d   # starts Postgres, Redis, Qdrant locally
```

---

## 9. API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/sources` | List all RSS sources |
| POST | `/sources` | Add a new RSS source |
| DELETE | `/sources/{id}` | Remove a source |
| POST | `/ingest/poll` | Poll all RSS feeds |
| POST | `/ingest/index` | Index unindexed articles |
| POST | `/ingest/run` | Poll + index in one call |
| GET | `/articles/{id}` | Get article details |
| POST | `/chat` | Send a chat message (RAG) |
| GET | `/chat/{session_id}/history` | Get chat session history |

---

## 10. Architecture Overview

```
User ──► React (Vite) ──► FastAPI Backend
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
         PostgreSQL      Qdrant          Google Gemini
         (articles,    (dense + BM25    (embeddings +
          chunks,       vectors,          LLM answers)
          sessions)     hybrid search)
```

**Retrieval pipeline:** Dense search + BM25 sparse search → RRF fusion → Recency boost → Cross-encoder reranking → Top-K to LLM

**Deduplication:** Two-tier system prevents duplicate articles from polluting the index:
- Tier 1: URL normalization + SimHash title comparison
- Tier 2: Semantic embedding similarity check in Qdrant

---

## 11. Known Limitations

- **No background scheduler** — RSS polling requires manual triggers or an external cron job (`curl -X POST .../ingest/run` every 15 min)
- **Reranker download** — The `bge-reranker-base` model (~1.1 GB) downloads on first chat query. First response will be slow.
- **SQLite concurrency** — SQLite handles one writer at a time. Use Postgres for any multi-user deployment.
- **No auth** — No user authentication; rate limiting is IP-based only.
- **Redis unused** — Redis is in config for future Celery task queue but not currently wired up.
- **Sparse vectors** — BM25 uses a simple hash-based term frequency approach, not a trained sparse model.

---

## Project Structure

```
newspulse/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app entry point
│   │   ├── config.py            # Pydantic settings (reads .env)
│   │   ├── api/                 # Route handlers (chat, sources, ingest, articles)
│   │   ├── db/                  # SQLAlchemy models + session factory
│   │   ├── ingestion/           # RSS collector + dedup (Tier 1 & 2)
│   │   ├── indexing/            # Chunker, embedder, Qdrant client, pipeline
│   │   ├── retrieval/           # Hybrid search, reranker
│   │   ├── rag/                 # Prompt builder, LLM client, citation parser
│   │   └── middleware/          # Rate limiter
│   ├── data/                    # SQLite DB (auto-created)
│   ├── requirements.txt
│   └── .env                     # Your config (not committed)
├── frontend/
│   ├── src/                     # React components (ChatWindow, MessageBubble, etc.)
│   ├── package.json
│   └── vite.config.js           # Dev proxy to backend
├── scripts/
│   ├── seed_sources.py          # Seed default RSS feeds
│   ├── test_ingestion.py        # Test RSS polling
│   └── test_retrieval.py        # Test full pipeline
├── docker-compose.yml           # Dev infra (Postgres, Redis, Qdrant)
└── docker-compose.prod.yml      # Full production stack
```
