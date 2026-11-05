import io

from tests.conftest import login_as_doctor, login_as_patient, make_jpeg_bytes


def test_doctor_login_success(anonymous_client):
    r = anonymous_client.post(
        "/api/v1/auth/doctor/login", json={"id": "Dr. New", "password": "123456"}
    )
    assert r.status_code == 200
    assert r.json() == {"role": "doctor", "id": "Dr. New"}


def test_doctor_login_wrong_password(anonymous_client):
    login_as_doctor(anonymous_client, "Dr. New")
    r = anonymous_client.post(
        "/api/v1/auth/doctor/login", json={"id": "Dr. New", "password": "wrong"}
    )
    assert r.status_code == 401


def test_protected_route_requires_session(anonymous_client):
    r = anonymous_client.get("/api/v1/cases")
    assert r.status_code == 401


def test_protected_route_works_after_login(anonymous_client):
    login_as_doctor(anonymous_client, "Dr. New")
    r = anonymous_client.get("/api/v1/cases")
    assert r.status_code == 200


def test_reset_password_restores_default(anonymous_client):
    login_as_doctor(anonymous_client, "Dr. Reset")
    r = anonymous_client.post("/api/v1/auth/doctor/reset-password", json={"id": "Dr. Reset"})
    assert r.status_code == 200
    r2 = anonymous_client.post(
        "/api/v1/auth/doctor/login", json={"id": "Dr. Reset", "password": "123456"}
    )
    assert r2.status_code == 200


def test_patient_sees_only_own_case(client):
    data = make_jpeg_bytes()
    r1 = client.post(
        "/api/v1/predictions",
        data={"dentist_name": "Dr. Smith", "patient_name": "Alice"},
        files={"file": ("xray.jpg", io.BytesIO(data), "image/jpeg")},
    )
    case_id = r1.json()["case_id"]
    owner_patient_id = client.get("/api/v1/cases").json()[0]["patient_id"]

    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app, base_url="http://testserver.local") as patient_client:
        login_as_patient(patient_client, owner_patient_id)
        r_owner = patient_client.get(f"/api/v1/cases/{case_id}")
        assert r_owner.status_code == 200

    with TestClient(app, base_url="http://testserver.local") as other_client:
        login_as_patient(other_client, "someone-else")
        r_other = other_client.get(f"/api/v1/cases/{case_id}")
        assert r_other.status_code == 403
