import io

from app.dependencies import get_chat_service
from app.main import app
from app.models.schemas import ChatMessage, RetrievedChunk
from app.services.chat_service import ChatService
from app.services.llm.base import LLMClient
from tests.conftest import make_jpeg_bytes


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
        return f"echo: {user_message} | findings: {findings_context}"


def _override_chat_service(storage):
    def _factory():
        return ChatService(storage=storage, llm_client=FakeLLMClient())

    return _factory


def test_chat_replies_grounded_on_findings(client, storage):
    app.dependency_overrides[get_chat_service] = _override_chat_service(storage)
    data = make_jpeg_bytes()
    r = client.post(
        "/api/v1/predictions", data={"patient_name": "Test Patient"}, files={"file": ("xray.jpg", io.BytesIO(data), "image/jpeg")}
    )
    case_id = r.json()["case_id"]

    r2 = client.post(
        f"/api/v1/cases/{case_id}/chat",
        json={"message": "What did you find?"},
    )
    assert r2.status_code == 200
    body = r2.json()
    assert "What did you find?" in body["reply"]
    assert "Caries" in body["reply"]

    r3 = client.get(f"/api/v1/cases/{case_id}/chat")
    assert r3.status_code == 200
    history = r3.json()
    assert history[0]["role"] == "user"
    assert history[0]["content"] == "What did you find?"
    assert history[0]["created_at"]
    assert history[1]["role"] == "assistant"


def test_chat_history_persists_across_requests(client, storage):
    app.dependency_overrides[get_chat_service] = _override_chat_service(storage)
    data = make_jpeg_bytes()
    r = client.post(
        "/api/v1/predictions", data={"patient_name": "Test Patient"}, files={"file": ("xray.jpg", io.BytesIO(data), "image/jpeg")}
    )
    case_id = r.json()["case_id"]

    client.post(f"/api/v1/cases/{case_id}/chat", json={"message": "first"})
    client.post(f"/api/v1/cases/{case_id}/chat", json={"message": "second"})

    history = client.get(f"/api/v1/cases/{case_id}/chat").json()
    assert [m["content"] for m in history] == [
        "first",
        "echo: first | findings: - Caries (confidence 0.87): Possible Caries detected in this region — dentist review required.",
        "second",
        "echo: second | findings: - Caries (confidence 0.87): Possible Caries detected in this region — dentist review required.",
    ]


def test_chat_on_nonexistent_case_returns_404(client, storage):
    app.dependency_overrides[get_chat_service] = _override_chat_service(storage)
    r = client.post(
        "/api/v1/cases/does-not-exist/chat",
        json={"message": "hi"},
    )
    assert r.status_code == 404


def test_get_chat_history_on_nonexistent_case_returns_404(client, storage):
    app.dependency_overrides[get_chat_service] = _override_chat_service(storage)
    r = client.get("/api/v1/cases/does-not-exist/chat")
    assert r.status_code == 404


def test_get_chat_history_empty_for_new_case(client, storage):
    app.dependency_overrides[get_chat_service] = _override_chat_service(storage)
    data = make_jpeg_bytes()
    r = client.post(
        "/api/v1/predictions", data={"patient_name": "Test Patient"}, files={"file": ("xray.jpg", io.BytesIO(data), "image/jpeg")}
    )
    case_id = r.json()["case_id"]
    r2 = client.get(f"/api/v1/cases/{case_id}/chat")
    assert r2.status_code == 200
    assert r2.json() == []


def test_clear_chat_history(client, storage):
    app.dependency_overrides[get_chat_service] = _override_chat_service(storage)
    data = make_jpeg_bytes()
    r = client.post(
        "/api/v1/predictions", data={"patient_name": "Test Patient"}, files={"file": ("xray.jpg", io.BytesIO(data), "image/jpeg")}
    )
    case_id = r.json()["case_id"]
    client.post(f"/api/v1/cases/{case_id}/chat", json={"message": "hello"})
    assert client.get(f"/api/v1/cases/{case_id}/chat").json() != []

    r2 = client.delete(f"/api/v1/cases/{case_id}/chat")
    assert r2.status_code == 204
    assert client.get(f"/api/v1/cases/{case_id}/chat").json() == []


def test_clear_chat_history_on_nonexistent_case_returns_404(client, storage):
    app.dependency_overrides[get_chat_service] = _override_chat_service(storage)
    r = client.delete("/api/v1/cases/does-not-exist/chat")
    assert r.status_code == 404
