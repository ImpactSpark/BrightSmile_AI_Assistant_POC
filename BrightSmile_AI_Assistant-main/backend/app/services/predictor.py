"""Model predictor.

Loads the frozen YOLO model exactly once (at app startup) and exposes a
single `predict` method returning raw detections in original-image pixel
coordinates. Never retrains, never modifies weights, never changes the
frozen confidence threshold or preprocessing here.

If `model_artifacts/best.pt` is not present (the case at scaffold time,
since no ML artifacts were provided), falls back to `StubPredictor`, which
returns zero detections and is clearly marked as non-clinical. Swap in the
real weights and this module will use them automatically — no code change
needed beyond confirming `app.core.constants` values were replaced from the
real artifacts.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.core import constants
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class RawDetection:
    condition: str
    confidence: float
    x1: float
    y1: float
    x2: float
    y2: float


class ModelPredictor(ABC):
    @abstractmethod
    def predict(self, image_path: str, orig_width: int, orig_height: int) -> list[RawDetection]:
        ...

    @property
    @abstractmethod
    def is_real_model(self) -> bool:
        ...


class YoloPredictor(ModelPredictor):
    """Wraps the frozen ultralytics YOLO model. Weights are never modified."""

    def __init__(self, weights_path: str):
        from ultralytics import YOLO  # imported lazily so stub path has no hard dep

        self._model = YOLO(weights_path)
        self._weights_path = weights_path

    @property
    def is_real_model(self) -> bool:
        return True

    def predict(self, image_path: str, orig_width: int, orig_height: int) -> list[RawDetection]:
        results = self._model.predict(
            source=image_path,
            imgsz=constants.MODEL_IMAGE_SIZE,
            conf=constants.CONFIDENCE_THRESHOLD,
            iou=constants.MODEL_IOU_THRESHOLD,
            verbose=False,
        )
        detections: list[RawDetection] = []
        for result in results:
            names = result.names
            boxes = result.boxes
            if boxes is None:
                continue
            for box in boxes:
                cls_idx = int(box.cls.item())
                condition = names.get(cls_idx) if isinstance(names, dict) else names[cls_idx]
                if condition not in constants.SUPPORTED_CONDITIONS:
                    # Never expose unsupported findings even if the model emits them.
                    continue
                conf = float(box.conf.item())
                if conf < constants.CONFIDENCE_THRESHOLD:
                    continue
                x1, y1, x2, y2 = [float(v) for v in box.xyxy[0].tolist()]
                detections.append(RawDetection(condition, conf, x1, y1, x2, y2))
        return detections


class StubPredictor(ModelPredictor):
    """Non-clinical placeholder used only because real weights are absent.

    Returns zero findings deterministically. This is intentional: inventing
    fake bounding boxes/conditions would violate the "do not invent medical
    findings" constraint. Replace with YoloPredictor once best.pt exists.
    """

    @property
    def is_real_model(self) -> bool:
        return False

    def predict(self, image_path: str, orig_width: int, orig_height: int) -> list[RawDetection]:
        logger.warning(
            '"stub predictor invoked - no real model weights loaded, returning zero findings"'
        )
        return []


_predictor_singleton: ModelPredictor | None = None


def load_predictor() -> ModelPredictor:
    """Call once at app startup. Idempotent."""
    global _predictor_singleton
    if _predictor_singleton is not None:
        return _predictor_singleton

    if constants.MODEL_WEIGHTS_PATH.exists():
        logger.info('"loading frozen YOLO model"')
        _predictor_singleton = YoloPredictor(str(constants.MODEL_WEIGHTS_PATH))
    else:
        logger.warning(
            '"model weights not found, loading StubPredictor - findings will be empty"'
        )
        _predictor_singleton = StubPredictor()
    return _predictor_singleton


def get_predictor() -> ModelPredictor:
    if _predictor_singleton is None:
        return load_predictor()
    return _predictor_singleton
