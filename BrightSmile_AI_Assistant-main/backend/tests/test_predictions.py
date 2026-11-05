import io

from tests.conftest import make_jpeg_bytes


def test_valid_upload_returns_structured_prediction(client):
    data = make_jpeg_bytes()
    r = client.post(
        "/api/v1/predictions", data={"patient_name": "Test Patient"}, files={"file": ("xray.jpg", io.BytesIO(data), "image/jpeg")}
    )
    assert r.status_code == 200
    body = r.json()
    assert "case_id" in body
    assert body["image_dimensions"] == {"width": 640, "height": 480}
    assert len(body["findings"]) == 1
    finding = body["findings"][0]
    assert finding["finding_id"] == "finding_001"
    assert finding["condition"] == "Caries"
    assert finding["confidence"] == 0.87
    assert finding["bbox"] == {"x1": 100, "y1": 200, "x2": 300, "y2": 400}
    assert finding["review_required"] is True
    assert finding["status"] == "pending"
    assert finding["clinical_message"] == "Possible Caries detected in this region — dentist review required."
    assert "disclaimer" in body and len(body["disclaimer"]) > 0


def test_invalid_file_type_rejected(client):
    r = client.post(
        "/api/v1/predictions",
        files={"file": ("notes.txt", io.BytesIO(b"hello world"), "text/plain")},
    )
    assert r.status_code == 422


def test_malformed_image_rejected(client):
    r = client.post(
        "/api/v1/predictions",
        files={"file": ("xray.jpg", io.BytesIO(b"not-a-real-jpeg-body"), "image/jpeg")},
    )
    assert r.status_code == 422


def test_oversized_file_rejected(client, monkeypatch):
    from app.core import constants

    monkeypatch.setattr(constants, "MAX_UPLOAD_SIZE_BYTES", 10)
    data = make_jpeg_bytes()
    r = client.post(
        "/api/v1/predictions", data={"patient_name": "Test Patient"}, files={"file": ("xray.jpg", io.BytesIO(data), "image/jpeg")}
    )
    assert r.status_code == 422


def test_empty_file_rejected(client):
    r = client.post(
        "/api/v1/predictions",
        files={"file": ("xray.jpg", io.BytesIO(b""), "image/jpeg")},
    )
    assert r.status_code == 422


def test_undersized_dimensions_rejected(client):
    data = make_jpeg_bytes(width=10, height=10)
    r = client.post(
        "/api/v1/predictions", data={"patient_name": "Test Patient"}, files={"file": ("xray.jpg", io.BytesIO(data), "image/jpeg")}
    )
    assert r.status_code == 422


def test_confidence_threshold_filters_low_confidence_findings(client, storage, monkeypatch):
    from app.dependencies import get_prediction_service
    from app.main import app
    from app.services.predictor import ModelPredictor, RawDetection
    from app.services.prediction_service import PredictionService

    class LowConfPredictor(ModelPredictor):
        @property
        def is_real_model(self):
            return True

        def predict(self, image_path, orig_width, orig_height):
            return [RawDetection("Caries", 0.05, 0, 0, 10, 10)]

    app.dependency_overrides[get_prediction_service] = lambda: PredictionService(
        predictor=LowConfPredictor(), storage=storage
    )
    data = make_jpeg_bytes()
    r = client.post(
        "/api/v1/predictions", data={"patient_name": "Test Patient"}, files={"file": ("xray.jpg", io.BytesIO(data), "image/jpeg")}
    )
    assert r.status_code == 200
    assert r.json()["findings"] == []


def test_case_persisted_and_retrievable(client):
    data = make_jpeg_bytes()
    r = client.post(
        "/api/v1/predictions", data={"patient_name": "Test Patient"}, files={"file": ("xray.jpg", io.BytesIO(data), "image/jpeg")}
    )
    case_id = r.json()["case_id"]
    r2 = client.get(f"/api/v1/cases/{case_id}")
    assert r2.status_code == 200
    assert r2.json()["case_id"] == case_id
    assert r2.json()["findings"][0]["condition"] == "Caries"


def test_get_nonexistent_case_returns_404(client):
    r = client.get("/api/v1/cases/does-not-exist")
    assert r.status_code == 404
