# ⚡ NewsPulse — Real-Time Grounded Hybrid RAG Intelligence Platform

**NewsPulse** is an enterprise-grade, citation-grounded news intelligence system. It continuously ingests, deduplicates, and embeds global news from RSS feeds and NewsAPI into **Qdrant Vector Cloud**, enabling real-time conversational search powered by **Google Gemini** with sub-second streaming, visual news cards, and 100% verified source citations.

---

## 🌟 Key Features & Capabilities

* 🌐 **Dual Ingestion Engine**: Automated multi-feed RSS collector (ETag / Last-Modified caching) + real-time **NewsAPI.org** integration.
* ⚡ **Ultra-Fast Streaming RAG**: Token-by-token Server-Sent Events (SSE) streaming via `gemini-3.5-flash-lite` with **< 2.8s Time to First Token**.
* 🔍 **Concurrent Hybrid Search**: Parallelized **Dense vector search (3072d via `gemini-embedding-2`)** + **BM25 Sparse search** with **Reciprocal Rank Fusion (RRF)** and recency boosting.
* 📸 **Visual Story Cards**: Automatic thumbnail extraction (`og:image`, Media RSS, `urlToImage`) rendered in interactive cards with publisher badges, publication dates, and direct links.
* 🔗 **100% Grounded Citations**: In-text citation tags (`[1]`, `[2]`, `[3]`) and headlines are interactive markdown hyperlinks leading directly to verified reporting.
* ⏳ **Multi-Stage Loading State**: Real-time visual status indicator (Scanning feeds → Matching semantic context → Synthesizing briefing) with skeleton shimmers.
* 💬 **Continuous Session Management**: Multi-turn conversation persistence stored in Supabase PostgreSQL / SQLite with dynamic sidebar history and instant `+ New Chat` branching.

---

## 🏛️ System Architecture & Workflow

```mermaid
graph TD
    subgraph Ingestion Pipeline
        RSS[20+ Global RSS Feeds] --> Collector[Collector & Deduplicator]
        NewsAPI[NewsAPI.org Endpoint] --> Collector
        Collector --> Extractor[Metadata & Image Extractor]
        Extractor --> Chunker[Paragraph Chunker]
        Chunker --> Embedder[Gemini Embedding 2<br/>3072 Dimensions]
        Embedder --> Qdrant[(Qdrant Vector Cloud<br/>Dense + BM25 Sparse)]
        Extractor --> DB[(PostgreSQL / Supabase)]
    end

    subgraph User Query & Streaming RAG
        User([User Query]) --> Frontend[React + Vite UI]
        Frontend --> API[FastAPI /chat/stream]
        API --> ParallelSearch{Parallel Search}
        ParallelSearch -->|Dense Search| Qdrant
        ParallelSearch -->|BM25 Sparse Search| Qdrant
        Qdrant --> RRF[Reciprocal Rank Fusion & Recency Boost]
        RRF --> PromptBuilder[System Prompt + Verified Context]
        PromptBuilder --> Gemini[Gemini 3.5 Flash Lite]
        Gemini -->|SSE Token Stream| Frontend
        Frontend --> VisualCards[Interactive Executive Briefing<br/>+ Visual News Cards & Direct Links]
    end
```

---

## 🚀 How the System Works (Step-by-Step)

### 1. Multi-Tier News Ingestion & Deduplication
1. **Collection**: Ingests articles from curated channels (Tech, Global, Markets, Science) across top-tier publishers (*BBC, Reuters, TechCrunch, MIT Tech Review, Wired, NPR*).
2. **Tier 1 Deduplication**: Normalizes URLs and computes 64-bit **SimHash fingerprints** on article titles to prevent re-scraping the same story.
3. **Image & Metadata Extraction**: Extracts high-resolution OpenGraph thumbnails (`og:image`), media enclosures, authors, publisher tags, and publication timestamps.
4. **Chunking & Vectorization**: Articles are split into semantic paragraphs with sliding-window overlap and embedded into a **3072-dimensional vector space** using `models/gemini-embedding-2`.
5. **Tier 2 Deduplication**: Checks cosine similarity in Qdrant (threshold $\ge 0.92$ within 72 hours) to avoid indexing near-identical syndications.

---

### 2. Low-Latency Hybrid Search & Retrieval
When a user asks a question (e.g. *"What are the latest AI model releases and breakthroughs?"*):
1. **Parallel Vector Retrieval**: Executes two concurrent search streams across Qdrant Cloud:
   * **Dense Cosine Search**: Captures high-level semantic meaning and concepts.
   * **BM25 Sparse Search**: Matches exact keywords, entity names, and company tickers.
2. **Reciprocal Rank Fusion (RRF)**: Merges dense and sparse rankings using $RRF(d) = \sum \frac{1}{k + rank(d)}$.
3. **Recency Boosting**: Applies an exponential recency decay multiplier so breaking news from the past 24–48 hours ranks higher than older archives.
4. **Dynamic Web Fallback**: If the local vector store has fewer than 4 relevant articles for a niche query, the system transparently fetches and indexes live articles from NewsAPI in $\approx 200\text{ms}$.

---

### 3. Real-Time Streaming & Interactive Grounding
1. **Immediate SSE Handshake**: The server establishes the streaming connection in $< 10\text{ms}$, dispatching the session identifier and engaging the frontend loading state.
2. **Multi-Stage Loading State**:
   * 📡 *Scanning 20+ global feeds & Qdrant vector database...*
   * ⚡ *Matching semantic context & verifying factual citations...*
   * ✍️ *Synthesizing verified executive news briefing...*
3. **Streaming Synthesis**: `models/gemini-3.5-flash-lite` streams a concise executive briefing formatted with bold takeaways, structured bullet points, and citation markers.
4. **Automatic Link & Card Grounding**:
   * In-text citation badges (`[1]`, `[2]`, `[3]`) are linked directly to verified source URLs.
   * On stream completion, the **Verified News Sources & Intel** grid populates with rich visual story cards, thumbnail images, publisher badges, and **`Read Story ↗`** action buttons.

---

## 🛠️ Prerequisites & Stack

| Component | Technology | Role |
| :--- | :--- | :--- |
| **Frontend** | React 18, Vite, Tailwind CSS, Lucide Icons | Reactive UI, SSE streaming, Visual News Cards |
| **Backend** | FastAPI, Python 3.11+, Uvicorn, SQLAlchemy | High-concurrency async REST & SSE endpoints |
| **Vector DB** | Qdrant Cloud (AWS / GCP) | Hybrid Dense (3072d) + Sparse BM25 indexing |
| **Primary DB** | PostgreSQL (Supabase) / SQLite | Chat history, session persistence, article metadata |
| **LLM & Embeddings** | Google Gemini (`gemini-3.5-flash-lite`, `gemini-embedding-2`) | Semantic embeddings and executive synthesis |
| **External News** | NewsAPI.org + Curated RSS Feeds | Real-time global intelligence feeds |

---

## 📦 Quick Start & Local Setup

### 1. Clone & Install Dependencies

```bash
# Clone the repository
git clone <your-repo-url>
cd newspulse

# Backend setup
cd backend
python -m venv venv

# Windows:
venv\Scripts\activate
# macOS/Linux:
# source venv/bin/activate

pip install -r requirements.txt

# Frontend setup
cd ../frontend
npm install
```

---

### 2. Configure Environment Variables

Create `.env` inside `newspulse/backend/.env`:

```env
# === Database (Supabase Postgres or local SQLite) ===
DATABASE_URL_SYNC=postgresql://postgres:PASSWORD@aws-0-REGION.pooler.supabase.com:5432/postgres
# SQLite local fallback: sqlite:///backend/data/newspulse.db

# === Qdrant Vector Cloud ===
QDRANT_HOST=your-cluster-id.region.aws.cloud.qdrant.io
QDRANT_PORT=6333
QDRANT_API_KEY=your-qdrant-api-key
QDRANT_COLLECTION=news_chunks

# === Google Gemini AI (Embeddings & LLM) ===
GOOGLE_API_KEY=your-google-api-key
EMBEDDING_MODEL=models/gemini-embedding-2
EMBEDDING_DIM=3072
LLM_MODEL=models/gemini-3.5-flash-lite

# === NewsAPI.org Key (For live news fallback) ===
NEWSAPI_KEY=your-newsapi-key
```

---

### 3. Seed Default Feeds & Run Ingestion

```bash
cd newspulse

# Seed top tier RSS feeds (BBC, TechCrunch, Reuters, MIT Tech Review, Wired)
python scripts/seed_sources.py

# Poll and index latest global news into Qdrant Cloud
curl -X POST http://localhost:8000/ingest/run
```

---

### 4. Start Development Servers

```bash
# Terminal 1: Start Backend (FastAPI)
cd newspulse/backend
uvicorn app.main:app --reload --port 8000

# Terminal 2: Start Frontend (React + Vite)
cd newspulse/frontend
npm run dev
```

Open **[http://localhost:5173](http://localhost:5173)** in your browser!

---

## 📡 API Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/chat/stream` | Token-by-token SSE streaming with grounded citations and visual cards |
| `POST` | `/chat` | Standard JSON RAG query endpoint |
| `GET` | `/chat/sessions` | Fetch recent conversation threads with query preview |
| `GET` | `/chat/{session_id}/history` | Fetch complete chat history with restored citations & images |
| `DELETE` | `/chat/{session_id}` | Delete a chat session and all associated messages |
| `POST` | `/ingest/run` | Trigger instantaneous RSS polling and Qdrant indexing |
| `GET` | `/sources` | List all active RSS feeds and channels |
| `POST` | `/sources` | Add a new custom RSS feed |
| `GET` | `/articles/recent` | Fetch latest indexed articles with thumbnail URLs |

---

## 🔒 Security & Secrets Management

All production secrets (Gemini API keys, NewsAPI tokens, Qdrant Cloud JWTs, Database credentials) are isolated in `.env` and strictly guarded by `.gitignore`. No private keys or database passwords are ever committed to version control.
