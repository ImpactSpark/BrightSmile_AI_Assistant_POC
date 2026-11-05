from abc import ABC, abstractmethod
from pathlib import Path

from app.models.schemas import CaseRecord, ChatMessage, DoctorSummary, ReviewedFinding


class CaseStorage(ABC):
    """Storage interface for case persistence.

    Kept abstract so a PostgreSQL-backed implementation can be added later
    without changing callers. Do not add PostgreSQL until case-tracking
    needs (e.g. querying/filtering across cases) actually require it.
    """

    @abstractmethod
    def save_original_image(self, case_id: str, image_bytes: bytes, extension: str) -> str:
        ...

    @abstractmethod
    def save_case_record(self, case: CaseRecord) -> None:
        ...

    @abstractmethod
    def load_case_record(self, case_id: str) -> CaseRecord | None:
        ...

    @abstractmethod
    def save_reviews(self, case_id: str, reviews: list[ReviewedFinding]) -> None:
        ...

    @abstractmethod
    def load_reviews(self, case_id: str) -> list[ReviewedFinding]:
        ...

    @abstractmethod
    def case_exists(self, case_id: str) -> bool:
        ...

    @abstractmethod
    def list_cases(self) -> list[CaseRecord]:
        ...

    @abstractmethod
    def get_original_image_path(self, case_id: str) -> Path | None:
        ...

    @abstractmethod
    def save_chat_history(self, case_id: str, messages: list[ChatMessage]) -> None:
        ...

    @abstractmethod
    def load_chat_history(self, case_id: str) -> list[ChatMessage]:
        ...

    @abstractmethod
    def list_doctors(self) -> list[DoctorSummary]:
        ...

    @abstractmethod
    def list_cases_for_doctor(self, doctor_id: str) -> list[CaseRecord]:
        ...

    @abstractmethod
    def list_cases_for_patient(self, patient_id: str) -> list[CaseRecord]:
        ...
