from datetime import datetime, timezone

from app.core import constants
from app.models.schemas import (
    CaseDetailResponse,
    ReviewAction,
    ReviewedFinding,
    ReviewSubmission,
)
from app.storage.interface import CaseStorage


class CaseNotFoundError(Exception):
    pass


class FindingNotFoundError(Exception):
    pass


class InvalidReviewError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class ReviewService:
    def __init__(self, storage: CaseStorage):
        self._storage = storage

    def get_case(self, case_id: str) -> CaseDetailResponse:
        record = self._storage.load_case_record(case_id)
        if record is None:
            raise CaseNotFoundError(case_id)
        reviews = self._storage.load_reviews(case_id)
        return CaseDetailResponse(
            case_id=record.case_id,
            model_version=record.model_version,
            image_dimensions=record.image_dimensions,
            findings=record.original_findings,
            reviews=reviews,
            disclaimer=record.disclaimer,
            dentist_name=record.dentist_name,
            patient_name=record.patient_name,
        )

    def submit_review(self, case_id: str, submission: ReviewSubmission) -> ReviewedFinding:
        record = self._storage.load_case_record(case_id)
        if record is None:
            raise CaseNotFoundError(case_id)

        original = next(
            (f for f in record.original_findings if f.finding_id == submission.finding_id),
            None,
        )
        if original is None:
            raise FindingNotFoundError(submission.finding_id)

        if submission.action == ReviewAction.CORRECTED:
            if submission.condition not in constants.SUPPORTED_CONDITIONS:
                raise InvalidReviewError(
                    f"unsupported condition: {submission.condition}"
                )

        reviewed = ReviewedFinding(
            finding_id=submission.finding_id,
            original_finding=original,
            action=submission.action,
            corrected_condition=submission.condition
            if submission.action == ReviewAction.CORRECTED
            else None,
            corrected_bbox=submission.bbox
            if submission.action == ReviewAction.CORRECTED
            else None,
            reviewed_at=datetime.now(timezone.utc).isoformat(),
        )

        existing_reviews = self._storage.load_reviews(case_id)
        # Replace any prior review of this finding (dentist can revise their review),
        # original AI prediction in `record` is never touched.
        existing_reviews = [
            r for r in existing_reviews if r.finding_id != submission.finding_id
        ]
        existing_reviews.append(reviewed)
        self._storage.save_reviews(case_id, existing_reviews)

        return reviewed
