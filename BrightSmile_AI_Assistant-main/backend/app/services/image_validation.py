import io
from dataclasses import dataclass

from PIL import Image, UnidentifiedImageError

from app.core import constants


class ImageValidationError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


@dataclass
class ValidatedImage:
    width: int
    height: int
    extension: str
    format: str


def validate_upload(filename: str, content_type: str, data: bytes) -> ValidatedImage:
    if len(data) == 0:
        raise ImageValidationError("uploaded file is empty")

    if len(data) > constants.MAX_UPLOAD_SIZE_BYTES:
        raise ImageValidationError(
            f"file exceeds maximum upload size of {constants.MAX_UPLOAD_SIZE_BYTES} bytes"
        )

    if content_type not in constants.ALLOWED_CONTENT_TYPES:
        raise ImageValidationError(f"unsupported content type: {content_type}")

    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in constants.ALLOWED_EXTENSIONS:
        raise ImageValidationError(f"unsupported file extension: {ext}")

    try:
        with Image.open(io.BytesIO(data)) as img:
            img.verify()
        # verify() invalidates the image object; reopen to read dimensions safely.
        with Image.open(io.BytesIO(data)) as img:
            width, height = img.size
            fmt = (img.format or "").upper()
    except (UnidentifiedImageError, OSError, ValueError):
        raise ImageValidationError("file is not a valid or is a corrupted image")

    if fmt not in {"JPEG", "PNG"}:
        raise ImageValidationError(f"unsupported image format: {fmt}")

    if width < constants.MIN_IMAGE_DIMENSION or height < constants.MIN_IMAGE_DIMENSION:
        raise ImageValidationError(
            f"image dimensions too small (min {constants.MIN_IMAGE_DIMENSION}px)"
        )
    if width > constants.MAX_IMAGE_DIMENSION or height > constants.MAX_IMAGE_DIMENSION:
        raise ImageValidationError(
            f"image dimensions too large (max {constants.MAX_IMAGE_DIMENSION}px)"
        )

    return ValidatedImage(width=width, height=height, extension=ext, format=fmt)
