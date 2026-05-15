"""Image OCR using Tesseract via pytesseract with Pillow preprocessing.

Extracts text from scanned document images. Supports:
  - PDFs redirected here (fallback when pdfplumber returns empty)
  - Image files (PNG, JPG, TIFF, WEBP)

Applies Pillow-based preprocessing before OCR:
  1. Grayscale conversion
  2. Contrast enhancement (histogram stretching)
  3. Binarization (Otsu-like threshold)
  4. Optional deskew (requires numpy + scipy)
"""
import io
from app.ocr.providers.base import OCRProvider, OCRPage, OCRResult


# ---------------------------------------------------------------------------
# Pillow image preprocessing helpers
# ---------------------------------------------------------------------------

def _build_contrast_stretch_lut(
    histogram: list[int],
    min_percentile: float = 2.0,
    max_percentile: float = 98.0,
) -> list[int]:
    """Build a look-up table for contrast stretching.

    Maps the pixel range between *min_percentile* and *max_percentile*
    of the cumulative histogram to the full 0‑255 range.
    """
    total = sum(histogram)
    if total == 0:
        return list(range(256))

    cum = 0
    lo = 0
    hi = 255
    lo_target = total * (min_percentile / 100.0)
    hi_target = total * (max_percentile / 100.0)

    for i, count in enumerate(histogram):
        cum += count
        if cum >= lo_target and lo == 0:
            lo = i
        if cum >= hi_target:
            hi = i
            break

    if hi <= lo:
        return list(range(256))

    scale = 255.0 / (hi - lo)
    lut = []
    for i in range(256):
        if i <= lo:
            lut.append(0)
        elif i >= hi:
            lut.append(255)
        else:
            lut.append(int((i - lo) * scale))
    return lut


def _otsu_threshold(histogram: list[int]) -> int:
    """Calculate a binarisation threshold using Otsu's method.

    Iterates over all possible thresholds and picks the one that
    maximises between-class variance.
    """
    total = sum(histogram)
    if total == 0:
        return 128

    sum_total = sum(i * count for i, count in enumerate(histogram))

    w_b = 0
    sum_b = 0
    best_var = 0.0
    best_t = 128

    for t in range(256):
        w_b += histogram[t]
        if w_b == 0:
            continue
        w_f = total - w_b
        if w_f == 0:
            break

        sum_b += t * histogram[t]
        m_b = sum_b / w_b
        m_f = (sum_total - sum_b) / w_f

        var = w_b * w_f * (m_b - m_f) ** 2
        if var > best_var:
            best_var = var
            best_t = t

    return best_t


def _deskew(img: "Image.Image") -> "Image.Image":
    """Correct skew in the image (requires numpy + scipy).

    If numpy and/or scipy are not available, the image is returned
    unchanged.
    """
    try:
        import numpy as np
        from PIL import Image as PILImage  # needed for BICUBIC constant
        from scipy.ndimage import rotate as nd_rotate
    except ImportError:
        return img

    w, h = img.size
    if w < 64 or h < 64:
        return img

    arr = np.array(img.convert("L"))

    best_angle = 0.0
    best_score = 0.0

    # Try angles from -5° to +5° in 0.5° steps
    for deg in range(-10, 11):
        angle = deg * 0.5
        if abs(angle) < 0.001:
            rotated = arr
        else:
            rotated = nd_rotate(arr, angle, reshape=False, order=1, cval=255)

        # Score: variance of row projections (darker = higher weight)
        row_proj = np.sum(255 - rotated, axis=1)
        score = np.var(row_proj)

        if score > best_score:
            best_score = score
            best_angle = angle

    if abs(best_angle) < 0.3:
        return img

    return img.rotate(
        best_angle, expand=False, fillcolor=(255, 255, 255), resample=PILImage.BICUBIC
    )


def _preprocess_image(img: "Image.Image") -> "Image.Image":
    """Apply Pillow preprocessing to improve Tesseract OCR accuracy.

    Pipeline: grayscale → contrast stretch → Otsu binarisation → deskew.
    """
    # 1. Grayscale
    gray = img.convert("L")

    # 2. Contrast stretch
    lut = _build_contrast_stretch_lut(gray.histogram())
    enhanced = gray.point(lut)

    # 3. Otsu binarisation
    threshold = _otsu_threshold(enhanced.histogram())
    binary = enhanced.point(lambda p: 255 if p > threshold else 0, mode="1")

    # 4. Convert back to RGB (pytesseract expects RGB or L)
    result = binary.convert("RGB")

    # 5. Optional deskew
    result = _deskew(result)

    return result


# ---------------------------------------------------------------------------
# Per-page OCR logic  (extracted to eliminate single‑/multi‑page duplication)
# ---------------------------------------------------------------------------

def _ocr_page(page_img: "Image.Image", page_number: int) -> OCRPage:
    """Run Tesseract OCR on a single preprocessed page image.

    Confidence is derived from the mean of tesseract's per-character
    confidence data, normalised to 0‑1.  Falls back to 0.5 when no
    per-character data is available.
    """
    import pytesseract

    preprocessed = _preprocess_image(page_img)

    page_data = pytesseract.image_to_data(
        preprocessed, output_type=pytesseract.Output.DICT
    )

    text_lines: list[str] = []
    confidences: list[int] = []

    for idx, conf_str in enumerate(page_data.get("conf", [])):
        try:
            conf = int(conf_str)
        except (ValueError, TypeError):
            continue
        if conf > 0:
            confidences.append(conf)
            text = page_data.get("text", [""])[idx] or ""
            if text.strip():
                text_lines.append(text)

    text = " ".join(text_lines)
    avg_conf = (sum(confidences) / len(confidences) / 100.0) if confidences else 0.5

    return OCRPage(
        page_number=page_number,
        text=text,
        confidence=round(avg_conf, 2),
    )


# ---------------------------------------------------------------------------
# OCRProvider implementation
# ---------------------------------------------------------------------------

class TesseractProvider(OCRProvider):
    """Extract text from images using Tesseract OCR with Pillow preprocessing."""

    async def extract(self, data: bytes, mime_type: str) -> OCRResult:
        """Run Tesseract OCR on image bytes.

        Handles both single images and multi‑page TIFFs.
        Each page is preprocessed (grayscale → contrast stretch → binarisation
        → deskew) before being passed to pytesseract.
        """
        try:
            from PIL import Image
            import pytesseract  # noqa: F401 — triggers ImportError if missing
        except ImportError:
            return OCRResult(
                pages=[OCRPage(page_number=1, text="", confidence=0.0)],
                method="tesseract",
            )

        try:
            img = Image.open(io.BytesIO(data))
        except Exception:
            return OCRResult(
                pages=[OCRPage(page_number=1, text="", confidence=0.0)],
                method="tesseract_not_an_image",
            )

        try:
            pages: list[OCRPage] = []

            n_frames = getattr(img, "n_frames", 1)
            if n_frames > 1:
                # Multi-page TIFF
                for i in range(n_frames):
                    img.seek(i)
                    frame = img.copy().convert("RGB")
                    pages.append(_ocr_page(frame, i + 1))
            else:
                # Single image
                pages.append(_ocr_page(img.convert("RGB"), 1))

            if not pages:
                pages.append(OCRPage(page_number=1, text="", confidence=0.0))

            return OCRResult(pages=pages, method="tesseract")

        except Exception as e:
            return OCRResult(
                pages=[OCRPage(page_number=1, text="", confidence=0.0)],
                method=f"tesseract_error: {e}",
            )
