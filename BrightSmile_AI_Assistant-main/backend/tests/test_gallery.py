import io

from tests.conftest import make_jpeg_bytes


def test_list_cases_groups_by_dentist(client):
    data = make_jpeg_bytes()
    r1 = client.post(
        "/api/v1/predictions",
        data={"dentist_name": "Dr. Smith", "patient_name": "Test Patient"},
        files={"file": ("xray.jpg", io.BytesIO(data), "image/jpeg")},
    )
    r2 = client.post(
        "/api/v1/predictions",
        data={"dentist_name": "Dr. Jones", "patient_name": "Test Patient"},
        files={"file": ("xray2.jpg", io.BytesIO(data), "image/jpeg")},
    )
    assert r1.status_code == 200
    assert r2.status_code == 200

    r = client.get("/api/v1/cases")
    assert r.status_code == 200
    body = r.json()
    names = {c["dentist_name"] for c in body}
    assert names == {"Dr. Smith", "Dr. Jones"}
    assert all(c["finding_count"] == 1 for c in body)


def test_list_cases_empty(client):
    r = client.get("/api/v1/cases")
    assert r.status_code == 200
    assert r.json() == []


def test_get_case_image_returns_bytes(client):
    data = make_jpeg_bytes()
    r = client.post(
        "/api/v1/predictions", data={"patient_name": "Test Patient"}, files={"file": ("xray.jpg", io.BytesIO(data), "image/jpeg")}
    )
    case_id = r.json()["case_id"]
    r2 = client.get(f"/api/v1/cases/{case_id}/image")
    assert r2.status_code == 200
    assert r2.content == data


def test_get_case_image_404_for_unknown_case(client):
    r = client.get("/api/v1/cases/does-not-exist/image")
    assert r.status_code == 404


def test_list_doctors_returns_distinct_doctors(client):
    data = make_jpeg_bytes()
    client.post(
        "/api/v1/predictions",
        data={"dentist_name": "Dr. Smith", "patient_name": "Test Patient"},
        files={"file": ("xray.jpg", io.BytesIO(data), "image/jpeg")},
    )
    client.post(
        "/api/v1/predictions",
        data={"dentist_name": "Dr. Smith", "patient_name": "Test Patient"},
        files={"file": ("xray2.jpg", io.BytesIO(data), "image/jpeg")},
    )
    client.post(
        "/api/v1/predictions",
        data={"dentist_name": "Dr. Jones", "patient_name": "Test Patient"},
        files={"file": ("xray3.jpg", io.BytesIO(data), "image/jpeg")},
    )

    r = client.get("/api/v1/doctors")
    assert r.status_code == 200
    body = {d["name"]: d["case_count"] for d in r.json()}
    assert body == {"Dr. Smith": 2, "Dr. Jones": 1}


def test_list_cases_for_doctor_filters_correctly(client):
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

    r = client.get("/api/v1/doctors/Dr. Smith/cases")
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    assert body[0]["dentist_name"] == "Dr. Smith"


def test_list_cases_for_doctor_own_empty_gallery_returns_empty(client):
    r = client.get("/api/v1/doctors/Dr. Smith/cases")
    assert r.status_code == 200
    assert r.json() == []


def test_list_cases_for_other_doctor_forbidden(client):
    r = client.get("/api/v1/doctors/does-not-exist/cases")
    assert r.status_code == 403
