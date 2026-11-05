from app.models.schemas import CaseRecord, CaseSummary, DoctorSummary
from app.storage.interface import CaseStorage


def _to_summary(r: CaseRecord) -> CaseSummary:
    return CaseSummary(
        case_id=r.case_id,
        dentist_name=r.dentist_name,
        patient_id=r.patient_id,
        patient_name=r.patient_name,
        model_version=r.model_version,
        created_at=r.created_at,
        finding_count=len(r.original_findings),
    )


class GalleryService:
    def __init__(self, storage: CaseStorage):
        self._storage = storage

    def list_cases(self) -> list[CaseSummary]:
        records = self._storage.list_cases()
        summaries = [_to_summary(r) for r in records]
        summaries.sort(key=lambda s: s.created_at, reverse=True)
        return summaries

    def list_doctors(self) -> list[DoctorSummary]:
        doctors = self._storage.list_doctors()
        return sorted(doctors, key=lambda d: d.name)

    def list_cases_for_doctor(self, doctor_id: str) -> list[CaseSummary]:
        records = self._storage.list_cases_for_doctor(doctor_id)
        summaries = [_to_summary(r) for r in records]
        summaries.sort(key=lambda s: s.created_at, reverse=True)
        return summaries

    def list_cases_for_patient(self, patient_id: str) -> list[CaseSummary]:
        records = self._storage.list_cases_for_patient(patient_id)
        summaries = [_to_summary(r) for r in records]
        summaries.sort(key=lambda s: s.created_at, reverse=True)
        return summaries
