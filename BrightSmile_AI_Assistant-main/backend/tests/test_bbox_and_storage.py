import pytest
from pydantic import ValidationError

from app.models.schemas import BoundingBox
from app.storage.local_storage import LocalFilesystemCaseStorage


def test_bbox_rejects_inverted_coordinates():
    with pytest.raises(ValidationError):
        BoundingBox(x1=100, y1=100, x2=50, y2=200)
    with pytest.raises(ValidationError):
        BoundingBox(x1=100, y1=100, x2=200, y2=50)


def test_bbox_accepts_valid_coordinates():
    box = BoundingBox(x1=100, y1=200, x2=300, y2=400)
    assert box.x2 > box.x1
    assert box.y2 > box.y1


def test_storage_rejects_path_traversal(tmp_path):
    storage = LocalFilesystemCaseStorage(tmp_path / "cases")
    with pytest.raises(ValueError):
        storage.save_original_image("../../etc", b"data", ".jpg")


def test_storage_round_trips_case_record(tmp_path):
    from app.models.schemas import CaseRecord, ImageDimensions

    storage = LocalFilesystemCaseStorage(tmp_path / "cases")
    record = CaseRecord(
        case_id="abc123",
        model_version="test",
        image_dimensions=ImageDimensions(width=10, height=10),
        original_findings=[],
        disclaimer="disclaimer text",
        created_at="2024-01-01T00:00:00+00:00",
    )
    storage.save_case_record(record)
    loaded = storage.load_case_record("abc123")
    assert loaded is not None
    assert loaded.case_id == "abc123"
    assert storage.case_exists("abc123")
    assert not storage.case_exists("nope")
