from fastapi import APIRouter, Depends

from app.core import constants
from app.models.schemas import HealthResponse
from app.services.predictor import ModelPredictor, get_predictor

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health(predictor: ModelPredictor = Depends(get_predictor)) -> HealthResponse:
    return HealthResponse(
        status="ok",
        model_loaded=predictor.is_real_model,
        model_version=constants.MODEL_VERSION,
        model_artifacts_status=constants.MODEL_ARTIFACTS_STATUS,
    )
