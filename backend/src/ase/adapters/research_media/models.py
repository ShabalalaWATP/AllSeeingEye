"""Bounded media output for the isolated research worker, not an authenticity verdict."""

from dataclasses import dataclass

from ase.adapters.research_imports.models import ExtractedUnit

MAX_PIXELS = 8_000_000
MAX_DIMENSION = 8192
MAX_FRAME_BYTES = 1024 * 1024
MAX_VIDEO_SECONDS = 600
MAX_FRAMES = 3


@dataclass(frozen=True, slots=True)
class MediaTools:
    """Composition-root configuration only. Never construct these paths from upload fields."""

    tesseract: str | None = None
    ffmpeg: str | None = None
    ffprobe: str | None = None


@dataclass(frozen=True, slots=True)
class MediaFrame:
    seconds: float
    png: bytes
    sha256: str


@dataclass(frozen=True, slots=True)
class MediaExtractionResult:
    filename: str
    media_type: str
    sha256: str
    units: tuple[ExtractedUnit, ...]
    limitations: tuple[str, ...]
    metadata: tuple[tuple[str, str], ...]
    frames: tuple[MediaFrame, ...]
    verification_leads: tuple[str, ...]


VERIFICATION_LEADS = (
    "Compare visible signage, landmarks and weather with independent dated sources.",
    "Use the sanitised preview for a manually authorised reverse-image search if appropriate.",
    "Seek the earliest available publication and the original uploader's account of capture.",
    "Metadata dates, locations and software labels are editable claims requiring corroboration.",
)
COMMON_LIMITATIONS = (
    "Extraction does not establish authenticity, manipulation, capture time, location or identity.",
    "A SHA-256 digest identifies uploaded bytes; it does not verify their origin or truth.",
    "Previews are resized and metadata-stripped derivatives, not original evidence files.",
    "OCR is fallible, uses English only and must be checked against the visible image.",
)
