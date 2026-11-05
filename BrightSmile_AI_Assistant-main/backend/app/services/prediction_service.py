import time
import uuid
from datetime import datetime, timezone

from app.core import constants
from app.core.logging import get_logger
from app.models.schemas import (
    BoundingBox,
    CaseRecord,
    Finding,
    ImageDimensions,
    PredictionResponse,
    ReviewStatus,
)
from app.services.image_validation import ValidatedImage
from app.services.predictor import ModelPredictor
from app.storage.interface import CaseStorage

logger = get_logger(__name__)


def generate_case_id() -> str:
    return uuid.uuid4().hex


def generate_patient_id() -> str:
    return f"PT-{uuid.uuid4().hex[:6].upper()}"


class PredictionService:
    def __init__(self, predictor: ModelPredictor, storage: CaseStorage):
        self._predictor = predictor
        self._storage = storage

    def run_prediction(
        self,
        image_bytes: bytes,
        validated: ValidatedImage,
        dentist_name: str = "",
        patient_name: str = "",
    ) -> PredictionResponse:
        case_id = generate_case_id()
        logger.info('"request received" case_id=%s' % case_id)

        patient_id = self._resolve_patient_id(patient_name)

        image_path = self._storage.save_original_image(
            case_id, image_bytes, validated.extension
        )

        predict_start = time.perf_counter()
        logger.info('"prediction started" case_id=%s' % case_id)
        raw_detections = self._predictor.predict(
            image_path, validated.width, validated.height
        )
        inference_latency_ms = (time.perf_counter() - predict_start) * 1000

        postprocess_start = time.perf_counter()
        findings = self._postprocess(raw_detections)
        postprocess_latency_ms = (time.perf_counter() - postprocess_start) * 1000

        logger.info(
            '"prediction completed" case_id=%s inference_ms=%.2f postprocess_ms=%.2f findings=%d'
            % (case_id, inference_latency_ms, postprocess_latency_ms, len(findings))
        )

        record = CaseRecord(
            case_id=case_id,
            model_version=constants.MODEL_VERSION,
            image_dimensions=ImageDimensions(width=validated.width, height=validated.height),
            original_findings=findings,
            disclaimer=constants.CLINICAL_DISCLAIMER,
            created_at=datetime.now(timezone.utc).isoformat(),
            dentist_name=dentist_name,
            patient_id=patient_id,
            patient_name=patient_name,
        )
        self._storage.save_case_record(record)

        return PredictionResponse(
            case_id=case_id,
            model_version=constants.MODEL_VERSION,
            image_dimensions=record.image_dimensions,
            findings=findings,
            disclaimer=constants.CLINICAL_DISCLAIMER,
        )

    def _resolve_patient_id(self, patient_name: str) -> str:
        normalized = patient_name.strip().lower()
        if normalized:
            for record in self._storage.list_cases():
                if record.patient_name.strip().lower() == normalized:
                    return record.patient_id
        return generate_patient_id()

    def _postprocess(self, raw_detections) -> list[Finding]:
        findings: list[Finding] = []
        for idx, det in enumerate(raw_detections, start=1):
            if det.condition not in constants.SUPPORTED_CONDITIONS:
                continue
            if det.confidence < constants.CONFIDENCE_THRESHOLD:
                continue
            display_name = constants.CONDITION_DISPLAY_NAMES.get(det.condition, det.condition)
            findings.append(
                Finding(
                    finding_id=f"finding_{idx:03d}",
                    condition=det.condition,
                    confidence=round(det.confidence, 4),
                    bbox=BoundingBox(x1=det.x1, y1=det.y1, x2=det.x2, y2=det.y2),
                    review_required=True,
                    status=ReviewStatus.PENDING,
                    clinical_message=constants.CLINICAL_MESSAGE_TEMPLATE.format(
                        class_name=display_name
                    ),
                )
            )
        return findings
