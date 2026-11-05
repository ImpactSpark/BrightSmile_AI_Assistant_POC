from app.models.schemas import BoundingBox, Finding, ImageDimensions
from app.services.image_annotation import (
    crop_to_finding,
    draw_annotated_image,
    find_mentioned_findings,
    select_single_finding,
    to_data_url,
    wants_zoom,
)
from tests.conftest import make_jpeg_bytes


def _finding(
    condition: str, finding_id: str = "f1", bbox=(10, 10, 100, 100), confidence: float = 0.8
) -> Finding:
    x1, y1, x2, y2 = bbox
    return Finding(
        finding_id=finding_id,
        condition=condition,
        confidence=confidence,
        bbox=BoundingBox(x1=x1, y1=y1, x2=x2, y2=y2),
    )


def test_find_mentioned_findings_matches_condition_with_underscore_replaced():
    findings = [_finding("Deep_Caries"), _finding("Impacted_Tooth")]
    mentioned = find_mentioned_findings("Here is the deep caries region", findings)
    assert len(mentioned) == 1
    assert mentioned[0].condition == "Deep_Caries"


def test_find_mentioned_findings_no_match_returns_empty():
    findings = [_finding("Caries")]
    assert find_mentioned_findings("nothing relevant here", findings) == []


def test_find_mentioned_findings_matches_irregular_plural():
    findings = [_finding("Impacted_Tooth")]
    mentioned = find_mentioned_findings("multiple possible impacted teeth detected", findings)
    assert len(mentioned) == 1


def test_find_mentioned_findings_matches_regular_plural():
    findings = [_finding("Caries")]
    mentioned = find_mentioned_findings("possible caries in two regions", findings)
    assert len(mentioned) == 1


def test_draw_annotated_image_produces_valid_jpeg():
    image_bytes = make_jpeg_bytes()
    findings = [_finding("Caries")]
    annotated = draw_annotated_image(image_bytes, findings)
    assert annotated[:3] == b"\xff\xd8\xff"  # JPEG magic bytes


def test_to_data_url_format():
    url = to_data_url(b"abc", "image/jpeg")
    assert url.startswith("data:image/jpeg;base64,")


def test_wants_zoom_detects_keywords():
    assert wants_zoom("can you zoom into that tooth")
    assert wants_zoom("give me a close up")
    assert not wants_zoom("what should I do about this")


def test_select_single_finding_disambiguates_by_left_right():
    dims = ImageDimensions(width=1000, height=500)
    left = _finding("Caries", finding_id="left", bbox=(50, 100, 150, 200))
    right = _finding("Caries", finding_id="right", bbox=(800, 100, 900, 200))
    result = select_single_finding("zoom into the caries on the left", [left, right], dims)
    assert result.finding_id == "left"


def test_select_single_finding_disambiguates_by_upper_lower():
    dims = ImageDimensions(width=1000, height=500)
    upper = _finding("Caries", finding_id="upper", bbox=(400, 50, 500, 100))
    lower = _finding("Caries", finding_id="lower", bbox=(400, 400, 500, 450))
    result = select_single_finding("zoom into the lower caries", [upper, lower], dims)
    assert result.finding_id == "lower"


def test_select_single_finding_disambiguates_by_ordinal():
    dims = ImageDimensions(width=1000, height=500)
    findings = [
        _finding("Caries", finding_id="a", bbox=(10, 10, 50, 50)),
        _finding("Caries", finding_id="b", bbox=(60, 10, 100, 50)),
    ]
    result = select_single_finding("zoom into the second caries", findings, dims)
    assert result.finding_id == "b"


def test_select_single_finding_falls_back_to_highest_confidence():
    dims = ImageDimensions(width=1000, height=500)
    findings = [
        _finding("Caries", finding_id="low", confidence=0.4, bbox=(10, 10, 50, 50)),
        _finding("Caries", finding_id="high", confidence=0.9, bbox=(60, 10, 100, 50)),
    ]
    result = select_single_finding("zoom into the caries", findings, dims)
    assert result.finding_id == "high"


def test_select_single_finding_no_candidates_returns_none():
    dims = ImageDimensions(width=1000, height=500)
    assert select_single_finding("zoom in", [], dims) is None


def test_crop_to_finding_produces_smaller_valid_jpeg():
    image_bytes = make_jpeg_bytes(width=1000, height=500)
    finding = _finding("Caries", bbox=(400, 200, 500, 300))
    cropped = crop_to_finding(image_bytes, finding)
    assert cropped[:3] == b"\xff\xd8\xff"
    assert len(cropped) < len(image_bytes)
