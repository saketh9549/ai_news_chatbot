from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_chat import router as chat_router
from app.api.routes_sources import router as sources_router
from app.api.routes_ingest import router as ingest_router
from app.api.routes_articles import router as articles_router
from app.config import settings
from app.middleware.rate_limit import RateLimitMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.db.models import Base
    from app.db.session import get_sync_engine
    from app.workers.scheduler import start_scheduler, stop_scheduler
    Base.metadata.create_all(get_sync_engine())
    start_scheduler()
    try:
        yield
    finally:
        stop_scheduler()


app = FastAPI(title="NewsPulse", version="0.1.0", lifespan=lifespan)

app.add_middleware(RateLimitMiddleware, requests_per_minute=settings.rate_limit_rpm)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)
app.include_router(sources_router)
app.include_router(ingest_router)
app.include_router(articles_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
