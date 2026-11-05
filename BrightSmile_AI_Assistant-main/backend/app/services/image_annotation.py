import base64
import io
import re

from PIL import Image, ImageDraw

from app.models.schemas import Finding, ImageDimensions

IRREGULAR_PLURALS = {"tooth": "teeth"}

BOX_COLOR = (255, 64, 64)
BOX_WIDTH = 4

ZOOM_KEYWORDS = ("zoom", "close up", "closeup", "focus on", "crop", "just that", "specific tooth")
ORDINAL_WORDS = {"first": 0, "second": 1, "third": 2, "fourth": 3, "last": -1}
LEFT_WORDS = ("left",)
RIGHT_WORDS = ("right",)
UPPER_WORDS = ("upper", "top")
LOWER_WORDS = ("lower", "bottom")


def draw_annotated_image(image_bytes: bytes, findings: list[Finding]) -> bytes:
    """Draws the real YOLO bounding boxes for the given findings onto a copy
    of the original image. Server-side rendering with the model's actual
    coordinates -- not asked of the LLM, which can't reliably produce
    pixel-accurate boxes and would otherwise just hallucinate a location."""
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    draw = ImageDraw.Draw(image)

    for finding in findings:
        box = finding.bbox
        draw.rectangle(
            [(box.x1, box.y1), (box.x2, box.y2)], outline=BOX_COLOR, width=BOX_WIDTH
        )
        label = finding.condition.replace("_", " ")
        draw.text((box.x1 + 4, max(box.y1 - 18, 0)), label, fill=BOX_COLOR)

    out = io.BytesIO()
    image.save(out, format="JPEG", quality=90)
    return out.getvalue()


def to_data_url(image_bytes: bytes, media_type: str = "image/jpeg") -> str:
    encoded = base64.b64encode(image_bytes).decode("ascii")
    return f"data:{media_type};base64,{encoded}"


def _condition_pattern(condition: str) -> re.Pattern:
    """Matches a condition label allowing simple/irregular plurals (e.g.
    "impacted tooth" must also match "impacted teeth") -- LLM replies
    naturally pluralize when multiple findings share a condition, and a
    strict substring match silently drops those findings from annotation."""
    words = condition.replace("_", " ").lower().split()
    word_patterns = []
    for word in words:
        plural = IRREGULAR_PLURALS.get(word)
        if plural:
            word_patterns.append(f"(?:{re.escape(word)}|{re.escape(plural)})")
        else:
            word_patterns.append(f"{re.escape(word)}e?s?")
    return re.compile(r"\b" + r"\s+".join(word_patterns) + r"\b")


def find_mentioned_findings(text: str, findings: list[Finding]) -> list[Finding]:
    lower = text.lower()
    return [f for f in findings if _condition_pattern(f.condition).search(lower)]


def wants_zoom(text: str) -> bool:
    lower = text.lower()
    return any(kw in lower for kw in ZOOM_KEYWORDS)


def select_single_finding(
    text: str, candidates: list[Finding], image_dimensions: ImageDimensions
) -> Finding | None:
    """Narrows multiple same-condition candidates down to one using
    positional/ordinal language in the message (e.g. "the left one",
    "the second caries", "the lower tooth") -- so "zoom into the caries on
    the left" picks the specific finding instead of all matches."""
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]

    lower = text.lower()
    narrowed = candidates

    if any(w in lower for w in LEFT_WORDS):
        narrowed = [f for f in narrowed if (f.bbox.x1 + f.bbox.x2) / 2 < image_dimensions.width / 2]
    elif any(w in lower for w in RIGHT_WORDS):
        narrowed = [f for f in narrowed if (f.bbox.x1 + f.bbox.x2) / 2 >= image_dimensions.width / 2]

    if any(w in lower for w in UPPER_WORDS):
        narrowed = [f for f in narrowed if (f.bbox.y1 + f.bbox.y2) / 2 < image_dimensions.height / 2]
    elif any(w in lower for w in LOWER_WORDS):
        narrowed = [f for f in narrowed if (f.bbox.y1 + f.bbox.y2) / 2 >= image_dimensions.height / 2]

    if len(narrowed) == 1:
        return narrowed[0]

    for word, index in ORDINAL_WORDS.items():
        if word in lower:
            pool = narrowed if narrowed else candidates
            try:
                return pool[index]
            except IndexError:
                return pool[-1]

    # No disambiguating language and still ambiguous: default to the
    # highest-confidence match rather than guessing at position.
    pool = narrowed if narrowed else candidates
    return max(pool, key=lambda f: f.confidence)


def crop_to_finding(image_bytes: bytes, finding: Finding, padding_ratio: float = 0.6) -> bytes:
    """Crops tightly around one finding's real bbox with margin, for
    "zoom into this tooth" requests -- shows the actual detected region up
    close instead of the full X-ray with a small box on it."""
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    box = finding.bbox
    width, height = box.x2 - box.x1, box.y2 - box.y1
    pad_x, pad_y = width * padding_ratio, height * padding_ratio

    left = max(0, box.x1 - pad_x)
    top = max(0, box.y1 - pad_y)
    right = min(image.width, box.x2 + pad_x)
    bottom = min(image.height, box.y2 + pad_y)

    cropped = image.crop((left, top, right, bottom))
    draw = ImageDraw.Draw(cropped)
    draw.rectangle(
        [(box.x1 - left, box.y1 - top), (box.x2 - left, box.y2 - top)],
        outline=BOX_COLOR,
        width=BOX_WIDTH,
    )
    label = finding.condition.replace("_", " ")
    draw.text((max(box.x1 - left, 0) + 4, max(box.y1 - top - 18, 0)), label, fill=BOX_COLOR)

    out = io.BytesIO()
    cropped.save(out, format="JPEG", quality=92)
    return out.getvalue()
