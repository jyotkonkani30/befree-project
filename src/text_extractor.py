from pathlib import Path
from io import BytesIO
import os
import time
from typing import Dict, Union
import fitz
import pdfplumber
from .ocr_engine import ocr_page


def extract_pages(source: Union[str, Path, bytes]) -> Dict:
    data = source if isinstance(source, bytes) else Path(source).read_bytes()
    max_size = int(os.getenv("BANK_STATEMENT_MAX_FILE_BYTES", str(25 * 1024 * 1024)))
    max_pages = int(os.getenv("BANK_STATEMENT_MAX_PAGES", "100"))
    if len(data) > max_size:
        raise ValueError(f"PDF exceeds the {max_size // (1024 * 1024)} MB file-size limit.")
    document = fitz.open(stream=data, filetype="pdf")
    if len(document) > max_pages:
        raise ValueError(f"PDF exceeds the {max_pages}-page processing limit.")
    pages = []
    tables = []
    page_details = []
    text_started = time.perf_counter()
    page_texts = []
    for page in document:
        text = page.get_text("text").strip()
        meaningful = len("".join(text.split())) >= 20
        page_texts.append(text)
        page_details.append({"page": page.number + 1, "has_text": meaningful, "text_length": len(text)})
    text_duration = time.perf_counter() - text_started
    table_started = time.perf_counter()
    with pdfplumber.open(BytesIO(data)) as pdf:
        for page in pdf.pages:
            tables.extend(page.extract_tables() or [])
    table_duration = time.perf_counter() - table_started
    ocr_started = time.perf_counter()
    ocr_pages = 0
    for index, page in enumerate(document):
        text = page_texts[index]
        if not page_details[index]["has_text"]:
            text = ocr_page(page)
            ocr_pages += 1
        pages.append(text)
    ocr_duration = time.perf_counter() - ocr_started
    text_pages = sum(detail["has_text"] for detail in page_details)
    pdf_type = "text-based" if text_pages == len(pages) else "image-based" if text_pages == 0 else "mixed"
    return {
        "pages": pages,
        "text": "\n\f\n".join(pages),
        "tables": tables,
        "pdf_type": pdf_type,
        "page_count": len(pages),
        "page_diagnostics": [
            {
                "page": index + 1,
                "characters": len(page),
                "text_extracted": bool(page.strip()),
                "method": "text" if page_details[index]["has_text"] else "ocr",
            }
            for index, page in enumerate(pages)
        ],
        "processing_diagnostics": {
            "file_size_bytes": len(data),
            "page_count": len(pages),
            "text_extraction_seconds": round(text_duration, 3),
            "table_extraction_seconds": round(table_duration, 3),
            "ocr_seconds": round(ocr_duration, 3),
            "ocr_pages": ocr_pages,
            "detected_tables": len(tables),
        },
    }
