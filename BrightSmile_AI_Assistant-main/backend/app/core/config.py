from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "BrightSmile Dental X-ray AI POC"
    api_v1_prefix: str = "/api/v1"
    storage_root: str = "storage/cases"
    storage_backend: str = "postgres"
    database_url: str = "postgresql://brightsmile:brightsmile@localhost:5433/brightsmile"
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://localhost:3000",
    ]
    log_level: str = "INFO"

    llm_provider: str = "gemini"
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None
    gemini_api_key: str | None = None
    groq_api_key: str | None = None
    openrouter_api_key: str | None = None
    llm_model: str | None = None

    rag_enabled: bool = False
    rag_backend: str = "pgvector"
    rag_database_url: str | None = None
    rag_embedding_model: str = "BAAI/bge-base-en-v1.5"
    rag_reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    rag_top_k_retrieve: int = 20
    rag_top_k_rerank: int = 4
    rag_chunk_tokens: int = 400
    rag_chunk_overlap: int = 50
    rag_corpus_dir: str = "rag_corpus"

    class Config:
        env_prefix = "BRIGHTSMILE_"
        env_file = ".env"


settings = Settings()
