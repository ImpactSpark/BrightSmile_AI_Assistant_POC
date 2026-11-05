from functools import lru_cache

from fastapi import Cookie, Depends, HTTPException

from app.core.config import settings
from app.services.chat_service import ChatService
from app.services.gallery_service import GalleryService
from app.services.llm.factory import LLMConfigError, get_llm_client
from app.services.predictor import ModelPredictor, get_predictor
from app.services.prediction_service import PredictionService
from app.services.rag.embeddings import EmbeddingModel, get_embedding_model
from app.services.rag.reranker import Reranker, get_reranker
from app.services.rag.retriever import Retriever
from app.services.review_service import ReviewService
from app.storage.auth_interface import AuthStorage
from app.storage.interface import CaseStorage
from app.storage.local_storage import LocalFilesystemCaseStorage
from app.storage.rag_interface import RagIndex

SESSION_COOKIE_NAME = "bsai_session"


@lru_cache
def get_storage() -> CaseStorage:
    if settings.storage_backend == "postgres":
        from app.storage.postgres_storage import PostgresCaseStorage

        return PostgresCaseStorage(settings.database_url, settings.storage_root)
    return LocalFilesystemCaseStorage(settings.storage_root)


@lru_cache
def get_auth_storage() -> AuthStorage:
    if settings.storage_backend == "postgres":
        from app.storage.postgres_auth_storage import PostgresAuthStorage

        return PostgresAuthStorage(settings.database_url)
    from app.storage.inmemory_auth_storage import InMemoryAuthStorage

    return InMemoryAuthStorage()


def get_current_user(
    bsai_session: str | None = Cookie(default=None),
    auth: AuthStorage = Depends(get_auth_storage),
) -> tuple[str, str]:
    if bsai_session:
        session = auth.get_session(bsai_session)
        if session is not None:
            return session
    raise HTTPException(status_code=401, detail="not authenticated")


def require_doctor(user: tuple[str, str] = Depends(get_current_user)) -> tuple[str, str]:
    role, subject_id = user
    if role != "doctor":
        raise HTTPException(status_code=403, detail="doctor access required")
    return user


def require_admin(user: tuple[str, str] = Depends(get_current_user)) -> tuple[str, str]:
    role, subject_id = user
    if role != "admin":
        raise HTTPException(status_code=403, detail="admin access required")
    return user


def get_prediction_service(storage: CaseStorage = Depends(get_storage)) -> PredictionService:
    predictor: ModelPredictor = get_predictor()
    return PredictionService(predictor=predictor, storage=storage)


def get_review_service(storage: CaseStorage = Depends(get_storage)) -> ReviewService:
    return ReviewService(storage=storage)


def get_gallery_service(storage: CaseStorage = Depends(get_storage)) -> GalleryService:
    return GalleryService(storage=storage)


@lru_cache
def get_rag_index() -> RagIndex | None:
    if not settings.rag_enabled:
        return None
    if settings.rag_backend == "pgvector":
        from app.storage.pgvector_rag_storage import PgVectorRagIndex

        return PgVectorRagIndex(settings.rag_database_url or settings.database_url)
    raise ValueError(f"unsupported rag_backend: {settings.rag_backend}")


@lru_cache
def get_rag_embedding_model() -> EmbeddingModel | None:
    if not settings.rag_enabled:
        return None
    return get_embedding_model(settings.rag_embedding_model)


@lru_cache
def get_rag_reranker() -> Reranker | None:
    if not settings.rag_enabled:
        return None
    return get_reranker(settings.rag_reranker_model)


def get_retriever() -> Retriever | None:
    index = get_rag_index()
    embedding_model = get_rag_embedding_model()
    if index is None or embedding_model is None:
        return None
    return Retriever(index=index, embedding_model=embedding_model, reranker=get_rag_reranker())


def get_chat_service(
    storage: CaseStorage = Depends(get_storage),
    retriever: Retriever | None = Depends(get_retriever),
) -> ChatService:
    try:
        llm_client = get_llm_client()
    except LLMConfigError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return ChatService(storage=storage, llm_client=llm_client, retriever=retriever)
