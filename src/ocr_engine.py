from io import BytesIO
import os
import re
from typing import List
import fitz
import pytesseract
from pytesseract import TesseractNotFoundError
from pdf2image import convert_from_bytes
from .image_preprocessor import preprocess_image


def ocr_pdf(data: bytes, dpi: int = 300) -> List[str]:
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
        processed = preprocess_image(image)
        timeout = float(os.getenv("BANK_STATEMENT_OCR_TIMEOUT_SECONDS", "45"))
        primary = pytesseract.image_to_string(processed, config="--psm 6", timeout=timeout)
        return primary
    except TesseractNotFoundError as error:
        raise RuntimeError("OCR requires the Tesseract binary. Install it with `brew install tesseract` or configure pytesseract.pytesseract.tesseract_cmd.") from error
    except RuntimeError as error:
        raise RuntimeError("OCR could not recognize the scanned page within the configured timeout.") from error
