from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from app.dependencies import (
    get_chat_service,
    get_current_user,
    get_gallery_service,
    get_review_service,
    get_storage,
    require_admin,
    require_doctor,
)
from app.models.schemas import (
    CaseDetailResponse,
    CaseSummary,
    ChatMessage,
    ChatRequest,
    ChatResponse,
    DoctorSummary,
    ReviewedFinding,
    ReviewSubmission,
)
from app.services.chat_service import ChatService
from app.services.chat_service import CaseNotFoundError as ChatCaseNotFoundError
from app.services.gallery_service import GalleryService
from app.services.llm.base import LLMServiceUnavailableError
from app.services.review_service import (
    CaseNotFoundError,
    FindingNotFoundError,
    InvalidReviewError,
    ReviewService,
)
from app.storage.interface import CaseStorage

router = APIRouter(tags=["cases"])


def _authorize_case_access(case_id: str, user: tuple[str, str], storage: CaseStorage) -> None:
    role, subject_id = user
    record = storage.load_case_record(case_id)
    if record is None:
        raise HTTPException(status_code=404, detail="case not found")
    if role == "admin":
        return
    if role == "doctor" and record.dentist_name == subject_id:
        return
    if role == "patient" and record.patient_id == subject_id:
        return
    raise HTTPException(status_code=403, detail="not authorized for this case")


@router.get("/admin/cases", response_model=list[CaseSummary])
def list_all_cases_admin(
    service: GalleryService = Depends(get_gallery_service), _user: tuple = Depends(require_admin)
) -> list[CaseSummary]:
    return service.list_cases()


@router.get("/cases", response_model=list[CaseSummary])
def list_cases(
    service: GalleryService = Depends(get_gallery_service), _user: tuple = Depends(require_doctor)
) -> list[CaseSummary]:
    return service.list_cases()


@router.get("/doctors", response_model=list[DoctorSummary])
def list_doctors(
    service: GalleryService = Depends(get_gallery_service), _user: tuple = Depends(require_doctor)
) -> list[DoctorSummary]:
    return service.list_doctors()


@router.get("/doctors/{doctor_id}/cases", response_model=list[CaseSummary])
def list_cases_for_doctor(
    doctor_id: str,
    service: GalleryService = Depends(get_gallery_service),
    user: tuple = Depends(require_doctor),
) -> list[CaseSummary]:
    _role, subject_id = user
    if subject_id != doctor_id:
        raise HTTPException(status_code=403, detail="not authorized for this dentist's cases")
    return service.list_cases_for_doctor(doctor_id)


@router.get("/patients/{patient_id}/cases", response_model=list[CaseSummary])
def list_cases_for_patient(
    patient_id: str,
    service: GalleryService = Depends(get_gallery_service),
    user: tuple = Depends(get_current_user),
) -> list[CaseSummary]:
    role, subject_id = user
    if role != "patient" or subject_id != patient_id:
        raise HTTPException(status_code=403, detail="not authorized")
    return service.list_cases_for_patient(patient_id)


@router.get("/cases/{case_id}", response_model=CaseDetailResponse)
def get_case(
    case_id: str,
    service: ReviewService = Depends(get_review_service),
    storage: CaseStorage = Depends(get_storage),
    user: tuple = Depends(get_current_user),
) -> CaseDetailResponse:
    _authorize_case_access(case_id, user, storage)
    try:
        return service.get_case(case_id)
    except CaseNotFoundError:
        raise HTTPException(status_code=404, detail="case not found")


@router.post("/cases/{case_id}/review", response_model=ReviewedFinding)
def submit_review(
    case_id: str,
    submission: ReviewSubmission,
    service: ReviewService = Depends(get_review_service),
    storage: CaseStorage = Depends(get_storage),
    user: tuple = Depends(require_doctor),
) -> ReviewedFinding:
    _authorize_case_access(case_id, user, storage)
    try:
        return service.submit_review(case_id, submission)
    except CaseNotFoundError:
        raise HTTPException(status_code=404, detail="case not found")
    except FindingNotFoundError:
        raise HTTPException(status_code=404, detail="finding not found")
    except InvalidReviewError as exc:
        raise HTTPException(status_code=422, detail=exc.message)


@router.get("/cases/{case_id}/image")
def get_case_image(
    case_id: str,
    storage: CaseStorage = Depends(get_storage),
    user: tuple = Depends(get_current_user),
) -> FileResponse:
    _authorize_case_access(case_id, user, storage)
    path = storage.get_original_image_path(case_id)
    if path is None:
        raise HTTPException(status_code=404, detail="case not found")
    return FileResponse(path)


@router.get("/cases/{case_id}/chat", response_model=list[ChatMessage])
def get_chat_history(
    case_id: str,
    service: ChatService = Depends(get_chat_service),
    storage: CaseStorage = Depends(get_storage),
    user: tuple = Depends(get_current_user),
) -> list[ChatMessage]:
    _authorize_case_access(case_id, user, storage)
    try:
        return service.get_history(case_id)
    except ChatCaseNotFoundError:
        raise HTTPException(status_code=404, detail="case not found")


@router.post("/cases/{case_id}/chat", response_model=ChatResponse)
async def chat_with_case(
    case_id: str,
    request: ChatRequest,
    service: ChatService = Depends(get_chat_service),
    storage: CaseStorage = Depends(get_storage),
    user: tuple = Depends(require_doctor),
) -> ChatResponse:
    _authorize_case_access(case_id, user, storage)
    try:
        return await service.ask(case_id, request)
    except ChatCaseNotFoundError:
        raise HTTPException(status_code=404, detail="case not found")


@router.delete("/cases/{case_id}/chat", status_code=204)
def clear_chat_history(
    case_id: str,
    service: ChatService = Depends(get_chat_service),
    storage: CaseStorage = Depends(get_storage),
    user: tuple = Depends(require_doctor),
) -> None:
    _authorize_case_access(case_id, user, storage)
    try:
        service.clear_history(case_id)
    except ChatCaseNotFoundError:
        raise HTTPException(status_code=404, detail="case not found")
    except LLMServiceUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
