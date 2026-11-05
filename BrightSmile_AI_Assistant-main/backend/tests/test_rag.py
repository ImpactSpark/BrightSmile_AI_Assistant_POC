import io

from app.dependencies import get_chat_service
from app.main import app
from app.models.schemas import ChatMessage, RetrievedChunk
from app.services.chat_service import ChatService
from app.services.llm.base import LLMClient
from tests.conftest import make_jpeg_bytes


class FakeRetriever:
    def __init__(self, chunks: list[RetrievedChunk]):
        self._chunks = chunks

    def retrieve(self, query: str, k: int, condition_filter: str | None = None):
        return self._chunks


class FakeLLMClient(LLMClient):
    async def chat(
        self,
        *,
        image_bytes: bytes,
        image_media_type: str,
        findings_context: str,
        history: list[ChatMessage],
        user_message: str,
        retrieved_chunks: list[RetrievedChunk] | None = None,
    ) -> str:
        self.received_chunks = retrieved_chunks
        return "reply"


def _override_chat_service(storage, retriever=None):
    llm_client = FakeLLMClient()

    def _factory():
        return ChatService(storage=storage, llm_client=llm_client, retriever=retriever)

    _factory.llm_client = llm_client
    return _factory


def test_chat_without_retriever_has_no_citations(client, storage):
    factory = _override_chat_service(storage, retriever=None)
    app.dependency_overrides[get_chat_service] = factory
    data = make_jpeg_bytes()
    r = client.post(
        "/api/v1/predictions",
        data={"patient_name": "Test Patient"},
        files={"file": ("xray.jpg", io.BytesIO(data), "image/jpeg")},
    )
    case_id = r.json()["case_id"]

    r2 = client.post(f"/api/v1/cases/{case_id}/chat", json={"message": "hello"})
    assert r2.status_code == 200
    assert r2.json()["citations"] == []
    assert factory.llm_client.received_chunks is None


def test_chat_with_retriever_returns_citations(client, storage):
    chunks = [
        RetrievedChunk(
            chunk_id="abc123",
            text="Caries management guidance text.",
            source="ADA Caries Management Guidelines",
            doc_type="ada_guideline",
            url="https://example.org/ada-caries",
            score=0.9,
        )
    ]
    factory = _override_chat_service(storage, retriever=FakeRetriever(chunks))
    app.dependency_overrides[get_chat_service] = factory
    data = make_jpeg_bytes()
    r = client.post(
        "/api/v1/predictions",
        data={"patient_name": "Test Patient"},
        files={"file": ("xray.jpg", io.BytesIO(data), "image/jpeg")},
    )
    case_id = r.json()["case_id"]

    r2 = client.post(f"/api/v1/cases/{case_id}/chat", json={"message": "how should I manage this cavity?"})
    assert r2.status_code == 200
    body = r2.json()
    assert body["citations"] == [
        {
            "chunk_id": "abc123",
            "source": "ADA Caries Management Guidelines",
            "url": "https://example.org/ada-caries",
        }
    ]
    assert factory.llm_client.received_chunks == chunks
