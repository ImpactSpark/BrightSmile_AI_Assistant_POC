import io

from tests.conftest import login_as_admin, login_as_doctor, login_as_patient, make_jpeg_bytes


def test_admin_login_success(anonymous_client):
    r = anonymous_client.post("/api/v1/auth/admin/login", json={"password": "123456"})
    assert r.status_code == 200
    assert r.json() == {"role": "admin", "id": "admin"}


def test_admin_login_wrong_password(anonymous_client):
    r = anonymous_client.post("/api/v1/auth/admin/login", json={"password": "wrong"})
    assert r.status_code == 401


def test_admin_routes_reject_doctor_session(client):
    r = client.get("/api/v1/admin/cases")
    assert r.status_code == 403
    r2 = client.get("/api/v1/admin/tables")
    assert r2.status_code == 403


def test_admin_routes_reject_patient_session(anonymous_client):
    login_as_patient(anonymous_client, "PT-1")
    r = anonymous_client.get("/api/v1/admin/cases")
    assert r.status_code == 403


def test_admin_sees_cases_from_multiple_doctors(client):
    data = make_jpeg_bytes()
    client.post(
        "/api/v1/predictions",
        data={"dentist_name": "Dr. Smith", "patient_name": "Test Patient"},
        files={"file": ("xray.jpg", io.BytesIO(data), "image/jpeg")},
    )
    client.post(
        "/api/v1/predictions",
        data={"dentist_name": "Dr. Jones", "patient_name": "Test Patient"},
        files={"file": ("xray2.jpg", io.BytesIO(data), "image/jpeg")},
    )

    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app, base_url="http://testserver.local") as admin_client:
        login_as_admin(admin_client)
        r = admin_client.get("/api/v1/admin/cases")
        assert r.status_code == 200
        names = {c["dentist_name"] for c in r.json()}
        assert names == {"Dr. Smith", "Dr. Jones"}


def test_admin_can_view_any_case_but_not_write(client):
    data = make_jpeg_bytes()
    r1 = client.post(
        "/api/v1/predictions",
        data={"dentist_name": "Dr. Smith", "patient_name": "Test Patient"},
        files={"file": ("xray.jpg", io.BytesIO(data), "image/jpeg")},
    )
    case_id = r1.json()["case_id"]
    finding_id = r1.json()["findings"][0]["finding_id"]

    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app, base_url="http://testserver.local") as admin_client:
        login_as_admin(admin_client)
        r = admin_client.get(f"/api/v1/cases/{case_id}")
        assert r.status_code == 200

        r2 = admin_client.post(
            f"/api/v1/cases/{case_id}/review", json={"finding_id": finding_id, "action": "accepted"}
        )
        assert r2.status_code == 403


def test_admin_reset_password_then_login(anonymous_client):
    r = anonymous_client.post("/api/v1/auth/admin/reset-password")
    assert r.status_code == 200
    r2 = anonymous_client.post("/api/v1/auth/admin/login", json={"password": "123456"})
    assert r2.status_code == 200


def test_list_tables_returns_registry(anonymous_client):
    login_as_admin(anonymous_client)
    r = anonymous_client.get("/api/v1/admin/tables")
    assert r.status_code == 200
    names = {t["name"] for t in r.json()}
    assert names == {"cases", "doctors", "patients", "sessions"}


def test_table_rows_returns_redacted_rows_or_requires_postgres(anonymous_client):
    # This process's `settings` reads the real backend/.env (not the test's
    # dependency-injected storage override), so admin_service's direct-SQL
    # path hits whatever backend is actually configured in this environment.
    login_as_admin(anonymous_client)
    r = anonymous_client.get("/api/v1/admin/tables/doctors/rows")
    assert r.status_code in (200, 400)
    if r.status_code == 200:
        for row in r.json():
            assert row.get("password_hash") in (None, "[redacted]")


def test_table_rows_rejects_unknown_table(anonymous_client):
    login_as_admin(anonymous_client)
    r = anonymous_client.get("/api/v1/admin/tables/not_a_real_table/rows")
    assert r.status_code == 400
