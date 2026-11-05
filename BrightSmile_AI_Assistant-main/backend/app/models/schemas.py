from __future__ import annotations

from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


class ReviewStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    CORRECTED = "corrected"


class ReviewAction(str, Enum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    CORRECTED = "corrected"


class BoundingBox(BaseModel):
    x1: float
    y1: float
    x2: float
    y2: float

    @field_validator("x2")
    @classmethod
    def x2_after_x1(cls, v: float, info) -> float:
        x1 = info.data.get("x1")
        if x1 is not None and v <= x1:
            raise ValueError("x2 must be greater than x1")
        return v

    @field_validator("y2")
    @classmethod
    def y2_after_y1(cls, v: float, info) -> float:
        y1 = info.data.get("y1")
        if y1 is not None and v <= y1:
            raise ValueError("y2 must be greater than y1")
        return v


class Finding(BaseModel):
    finding_id: str
    condition: str
    confidence: float = Field(ge=0.0, le=1.0)
    bbox: BoundingBox
    review_required: bool = True
    status: ReviewStatus = ReviewStatus.PENDING
    # Rendered from the frozen model's clinical_message_template. Never a
    # diagnostic claim -- always phrased as a possible finding needing review.
    clinical_message: str = ""


class ImageDimensions(BaseModel):
    width: int
    height: int


class PredictionResponse(BaseModel):
    case_id: str
    model_version: str
    image_dimensions: ImageDimensions
    findings: list[Finding]
    disclaimer: str


class CaseRecord(BaseModel):
    case_id: str
    model_version: str
    image_dimensions: ImageDimensions
    original_findings: list[Finding]
    disclaimer: str
    created_at: str
    dentist_name: str = ""
    patient_id: str = ""
    patient_name: str = ""


class CaseSummary(BaseModel):
    case_id: str
    dentist_name: str
    patient_id: str
    patient_name: str
    model_version: str
    created_at: str
    finding_count: int


class DoctorSummary(BaseModel):
    doctor_id: str
    name: str
    case_count: int


class ReviewedFinding(BaseModel):
    finding_id: str
    original_finding: Finding
    action: ReviewAction
    corrected_condition: Optional[str] = None
    corrected_bbox: Optional[BoundingBox] = None
    reviewed_at: str


class ReviewSubmission(BaseModel):
    finding_id: str
    action: ReviewAction
    condition: Optional[str] = None
    bbox: Optional[BoundingBox] = None

    @field_validator("condition")
    @classmethod
    def condition_required_for_correction(cls, v, info):
        action = info.data.get("action")
        if action == ReviewAction.CORRECTED and not v:
            raise ValueError("condition is required when action is 'corrected'")
        return v

    @field_validator("bbox")
    @classmethod
    def bbox_required_for_correction(cls, v, info):
        action = info.data.get("action")
        if action == ReviewAction.CORRECTED and v is None:
            raise ValueError("bbox is required when action is 'corrected'")
        return v


class CaseDetailResponse(BaseModel):
    case_id: str
    model_version: str
    image_dimensions: ImageDimensions
    findings: list[Finding]
    reviews: list[ReviewedFinding]
    disclaimer: str
    dentist_name: str
    patient_name: str


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    created_at: str = ""


class ChatRequest(BaseModel):
    message: str


class RetrievedChunk(BaseModel):
    chunk_id: str
    text: str
    source: str
    doc_type: str
    url: str = ""
    condition_tags: str = ""
    score: float = 0.0


class Citation(BaseModel):
    chunk_id: str
    source: str
    url: str = ""


class ChatResponse(BaseModel):
    reply: str
    citations: list[Citation] = Field(default_factory=list)
    annotated_image: str | None = None


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    model_version: str
    model_artifacts_status: str


class ErrorResponse(BaseModel):
    error: str
    detail: str
