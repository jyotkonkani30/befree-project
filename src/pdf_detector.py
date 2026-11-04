from pathlib import Path
from typing import BinaryIO, Dict, Union
import fitz


def detect_pdf_type(source: Union[str, Path, bytes, BinaryIO]) -> Dict:
    data = source.read() if hasattr(source, "read") else source
    document = fitz.open(stream=data, filetype="pdf") if isinstance(data, bytes) else fitz.open(str(data))
    pages = []
    for page in document:
        text = page.get_text("text").strip()
        meaningful = len("".join(text.split())) >= 20
        pages.append({"page": page.number + 1, "has_text": meaningful, "text_length": len(text)})
    text_pages = sum(p["has_text"] for p in pages)
    kind = "text-based" if text_pages == len(pages) else "image-based" if text_pages == 0 else "mixed"
    return {"type": kind, "pages": len(pages), "page_details": pages}
