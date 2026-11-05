import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.dependencies import (
    get_auth_storage,
    get_prediction_service,
    get_review_service,
    get_storage,
)
from app.main import app
from app.services.predictor import ModelPredictor, RawDetection
from app.services.prediction_service import PredictionService
from app.services.review_service import ReviewService
from app.storage.inmemory_auth_storage import InMemoryAuthStorage
from app.storage.local_storage import LocalFilesystemCaseStorage


class FakePredictor(ModelPredictor):
    """Deterministic predictor for tests -- returns one fixed finding."""

    @property
    def is_real_model(self) -> bool:
        return True

    def predict(self, image_path, orig_width, orig_height):
        return [RawDetection("Caries", 0.87, 100, 200, 300, 400)]


class EmptyPredictor(ModelPredictor):
    @property
    def is_real_model(self) -> bool:
        return False

    def predict(self, image_path, orig_width, orig_height):
        return []


@pytest.fixture
def storage(tmp_path):
    return LocalFilesystemCaseStorage(tmp_path / "cases")


@pytest.fixture
def client(storage):
    def _override_prediction_service():
        return PredictionService(predictor=FakePredictor(), storage=storage)

    def _override_review_service():
        return ReviewService(storage=storage)

    app.dependency_overrides[get_prediction_service] = _override_prediction_service
    app.dependency_overrides[get_review_service] = _override_review_service
    app.dependency_overrides[get_storage] = lambda: storage
    auth_storage = InMemoryAuthStorage()
    app.dependency_overrides[get_auth_storage] = lambda: auth_storage
    with TestClient(app, base_url="http://testserver.local") as c:
        login_as_doctor(c)
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def anonymous_client(storage):
    """Same as `client` but without an auto-logged-in session, for auth tests."""

    def _override_prediction_service():
        return PredictionService(predictor=FakePredictor(), storage=storage)

    def _override_review_service():
        return ReviewService(storage=storage)

    app.dependency_overrides[get_prediction_service] = _override_prediction_service
    app.dependency_overrides[get_review_service] = _override_review_service
    app.dependency_overrides[get_storage] = lambda: storage
    auth_storage = InMemoryAuthStorage()
    app.dependency_overrides[get_auth_storage] = lambda: auth_storage
    with TestClient(app, base_url="http://testserver.local") as c:
        yield c
    app.dependency_overrides.clear()


def login_as_doctor(client, doctor_id: str = "Dr. Smith") -> None:
    r = client.post("/api/v1/auth/doctor/login", json={"id": doctor_id, "password": "123456"})
    assert r.status_code == 200, r.text


def login_as_patient(client, patient_id: str) -> None:
    r = client.post("/api/v1/auth/patient/login", json={"id": patient_id, "password": "123456"})
    assert r.status_code == 200, r.text


def login_as_admin(client) -> None:
    r = client.post("/api/v1/auth/admin/login", json={"password": "123456"})
    assert r.status_code == 200, r.text


def make_jpeg_bytes(width=640, height=480) -> bytes:
    img = Image.new("RGB", (width, height), color=(120, 120, 120))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()
