from io import BytesIO
import os
import re
import shutil
from typing import List
import fitz
import pytesseract
from pytesseract import TesseractNotFoundError
from pdf2image import convert_from_bytes
from .image_preprocessor import preprocess_image


def _configure_tesseract():
    configured = os.getenv("TESSERACT_CMD")
    candidates = [configured] if configured else []
    candidates.extend(["tesseract", "/usr/bin/tesseract", "/usr/local/bin/tesseract"])
    executable = next((candidate for candidate in candidates if candidate and (os.path.isabs(candidate) or shutil.which(candidate))), None)
    if not executable:
        raise RuntimeError(
            "OCR requires Tesseract. Render must install `tesseract-ocr`; set TESSERACT_CMD to its executable path."
        )
    pytesseract.pytesseract.tesseract_cmd = executable


def ocr_pdf(data: bytes, dpi: int = 300) -> List[str]:
    _configure_tesseract()
    pages = convert_from_bytes(data, dpi=dpi)
    return [pytesseract.image_to_string(preprocess_image(page)) for page in pages]


def ocr_page(page: fitz.Page, dpi: int = 300) -> str:
    max_dimension = 3508
    requested_scale = dpi / 72
    page_scale = max_dimension / max(page.rect.width, page.rect.height)
    scale = min(requested_scale, page_scale)
    pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
    from PIL import Image
    image = Image.open(BytesIO(pixmap.tobytes("png")))
    try:
        _configure_tesseract()
        processed = preprocess_image(image)
        timeout = float(os.getenv("BANK_STATEMENT_OCR_TIMEOUT_SECONDS", "45"))
        primary = pytesseract.image_to_string(processed, config="--psm 6", timeout=timeout)
        return primary
    except TesseractNotFoundError as error:
        raise RuntimeError(
            "OCR requires Tesseract. Render must install `tesseract-ocr`; set TESSERACT_CMD to its executable path."
        ) from error
    except RuntimeError as error:
        raise RuntimeError("OCR could not recognize the scanned page within the configured timeout.") from error
