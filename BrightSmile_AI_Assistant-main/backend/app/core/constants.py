"""
Model configuration constants.

STATUS: SOURCED FROM FROZEN ARTIFACTS in `model_artifacts/`
(from dental_ai_poc_claude_package, DENTEX YOLO11m dental AI POC).

Every value below is read directly from one of these frozen artifact files
and must be kept in lockstep with them. Do not hand-edit a number here
without updating the corresponding source file, and do not tune/retrain
the model to make numbers match — the artifacts are the source of truth,
this file only mirrors them for use by the app.

Source files (all in backend/model_artifacts/):
    best.pt                        -> MODEL_WEIGHTS_PATH
    frozen_model_config.json       -> SUPPORTED_CONDITIONS, CONFIDENCE_THRESHOLD
    final_experiment_manifest.json -> MODEL_VERSION, MODEL_IMAGE_SIZE
    final_test_metrics.json        -> reported in README evaluation section
    validation_metrics.json        -> reported in README evaluation section
    threshold_selection.json       -> justifies CONFIDENCE_THRESHOLD (val-only selection)
    dataset_summary.json           -> reported in README evaluation section
    split_manifest.json            -> train/val/test split provenance
    inference_benchmark.json       -> reported in README evaluation section
"""

from pathlib import Path

MODEL_WEIGHTS_PATH = Path(__file__).resolve().parents[2] / "model_artifacts" / "best.pt"

# From model_artifacts/frozen_model_config.json -> "classes", in id order (0-3).
# These are the exact class names the frozen YOLO11m model was trained on.
# Do not rename, reorder, lowercase, or add to this list.
SUPPORTED_CONDITIONS: list[str] = [
    "Caries",
    "Deep_Caries",
    "Periapical_Lesion",
    "Impacted_Tooth",
]

# From model_artifacts/frozen_model_config.json -> "clinical_message_template".
# Rendered per-finding via CLINICAL_MESSAGE_TEMPLATE.format(class_name=...).
# This exact wording is a frozen artifact value, not app copy -- do not reword it.
CLINICAL_MESSAGE_TEMPLATE = "Possible {class_name} detected in this region — dentist review required."

CONDITION_DISPLAY_NAMES: dict[str, str] = {
    "Caries": "Caries",
    "Deep_Caries": "Deep Caries",
    "Periapical_Lesion": "Periapical Lesion",
    "Impacted_Tooth": "Impacted Tooth",
}

# From model_artifacts/frozen_model_config.json -> "confidence_threshold".
# Selected via maximum validation F1 (model_artifacts/threshold_selection.json);
# test set was NOT used for selection. Do not silently change this value.
CONFIDENCE_THRESHOLD = 0.20

# From model_artifacts/final_test_metrics.json / validation_metrics.json -> "imgsz".
MODEL_IMAGE_SIZE = 1024

# From model_artifacts/final_test_metrics.json -> "iou_threshold".
MODEL_IOU_THRESHOLD = 0.7

# From model_artifacts/final_experiment_manifest.json -> "project" + "model".
MODEL_VERSION = "dentex_dental_ai_poc-YOLO11m-conf0.20-imgsz1024"

MODEL_ARTIFACTS_STATUS = "loaded_from_frozen_package"

CLINICAL_DISCLAIMER = (
    "This tool provides AI-assisted, unverified findings for research and "
    "clinical decision-support purposes only. It is not an autonomous "
    "diagnostic system and does not produce a diagnosis. Every finding "
    "requires dentist review before any clinical use."
)

MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png"}
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}
MIN_IMAGE_DIMENSION = 100
MAX_IMAGE_DIMENSION = 8000
