import io

from tests.conftest import make_jpeg_bytes


def _upload(client):
    data = make_jpeg_bytes()
    r = client.post(
        "/api/v1/predictions", data={"patient_name": "Test Patient"}, files={"file": ("xray.jpg", io.BytesIO(data), "image/jpeg")}
    )
    body = r.json()
    return body["case_id"], body["findings"][0]["finding_id"]


def test_accept_review(client):
    case_id, finding_id = _upload(client)
    r = client.post(
        f"/api/v1/cases/{case_id}/review",
        json={"finding_id": finding_id, "action": "accepted"},
    )
    assert r.status_code == 200
    assert r.json()["action"] == "accepted"
    assert r.json()["original_finding"]["condition"] == "Caries"

    detail = client.get(f"/api/v1/cases/{case_id}").json()
    assert len(detail["reviews"]) == 1
    assert detail["reviews"][0]["action"] == "accepted"
    # original AI prediction untouched
    assert detail["findings"][0]["condition"] == "Caries"


def test_reject_review(client):
    case_id, finding_id = _upload(client)
    r = client.post(
        f"/api/v1/cases/{case_id}/review",
        json={"finding_id": finding_id, "action": "rejected"},
    )
    assert r.status_code == 200
    assert r.json()["action"] == "rejected"


def test_correction_review_preserves_original_and_stores_correction_separately(client):
    case_id, finding_id = _upload(client)
    r = client.post(
        f"/api/v1/cases/{case_id}/review",
        json={
            "finding_id": finding_id,
            "action": "corrected",
            "condition": "Deep_Caries",
            "bbox": {"x1": 10, "y1": 20, "x2": 50, "y2": 80},
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["action"] == "corrected"
    assert body["corrected_condition"] == "Deep_Caries"
    assert body["corrected_bbox"] == {"x1": 10, "y1": 20, "x2": 50, "y2": 80}
    # original AI prediction preserved, unmodified
    assert body["original_finding"]["condition"] == "Caries"

    detail = client.get(f"/api/v1/cases/{case_id}").json()
    assert detail["findings"][0]["condition"] == "Caries"


def test_correction_requires_supported_condition(client):
    case_id, finding_id = _upload(client)
    r = client.post(
        f"/api/v1/cases/{case_id}/review",
        json={
            "finding_id": finding_id,
            "action": "corrected",
            "condition": "wisdom_tooth_pain",
            "bbox": {"x1": 10, "y1": 20, "x2": 50, "y2": 80},
        },
    )
    assert r.status_code == 422


def test_review_on_nonexistent_case_returns_404(client):
    r = client.post(
        "/api/v1/cases/does-not-exist/review",
        json={"finding_id": "finding_001", "action": "accepted"},
    )
    assert r.status_code == 404


def test_review_on_nonexistent_finding_returns_404(client):
    case_id, _ = _upload(client)
    r = client.post(
        f"/api/v1/cases/{case_id}/review",
        json={"finding_id": "finding_999", "action": "accepted"},
    )
    assert r.status_code == 404
