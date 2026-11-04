import re


def normalize_description(value: str) -> str:
    text = str(value or "").lower()
    text = re.sub(r"\[(?:debit|credit)\]", " ", text)
    text = re.sub(r"\b(?:upi|neft|imps|rtgs|pos|ecs|nach)\b[/\s:-]*", " ", text)
    text = re.sub(r"\b(?:ref|txn|transaction|id|rrn|utr)[/\s:#-]*[a-z0-9-]{4,}\b", " ", text)
    text = re.sub(r"\b\d{5,}\b", " ", text)
    text = re.sub(r"[^a-z0-9& ]", " ", text)
    return re.sub(r"\s+", " ", text).strip()
