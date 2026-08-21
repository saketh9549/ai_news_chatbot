import os

from pydantic_settings import BaseSettings

_db_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
os.makedirs(_db_dir, exist_ok=True)
_default_sqlite = f"sqlite:///{os.path.join(_db_dir, 'newspulse.db')}"


_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env")
_root_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".env")


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://newspulse:newspulse@localhost:5432/newspulse"
    database_url_sync: str = _default_sqlite
    redis_url: str = "redis://localhost:6379/0"
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_api_key: str = ""
    qdrant_collection: str = "news_chunks"
    google_api_key: str = ""
    newsapi_key: str = ""
    embedding_model: str = "models/text-embedding-004"
    embedding_dim: int = 768
    llm_model: str = "gemini-2.0-flash"
    reranker_model: str = "BAAI/bge-reranker-base"
    enable_reranker: bool = False
    default_poll_interval_min: int = 15
    semantic_dedup_threshold: float = 0.92
    semantic_dedup_time_window_hours: int = 72
    rate_limit_rpm: int = 30

    model_config = {
        "env_file": (_env_path, _root_env_path, ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()
