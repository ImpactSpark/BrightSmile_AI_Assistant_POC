from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile

from app.dependencies import get_prediction_service, require_doctor
from app.models.schemas import PredictionResponse
from app.services.image_validation import ImageValidationError, validate_upload
from app.services.prediction_service import PredictionService

router = APIRouter(tags=["predictions"])


@router.post("/predictions", response_model=PredictionResponse)
async def create_prediction(
    file: UploadFile,
    dentist_name: str = Form(""),
    patient_name: str = Form(""),
    service: PredictionService = Depends(get_prediction_service),
    user: tuple = Depends(require_doctor),
) -> PredictionResponse:
    if not patient_name.strip():
        raise HTTPException(status_code=422, detail="patient_name is required")

    data = await file.read()

    try:
        validated = validate_upload(
            filename=file.filename or "", content_type=file.content_type or "", data=data
        )
    except ImageValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.message)

    _role, subject_id = user
    return service.run_prediction(
        image_bytes=data,
        validated=validated,
        dentist_name=dentist_name or subject_id,
        patient_name=patient_name,
    )
