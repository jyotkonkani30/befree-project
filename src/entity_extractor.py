import re
from .text_normalizer import normalize_description


RAILS = ("UPI", "NEFT", "IMPS", "RTGS", "ACH", "ECS", "CHQ", "CHEQUE")
GOVERNMENT_TERMS = ("GST", "TAX", "INCOME TAX", "TDS", "GOVERNMENT")
BUSINESS_TERMS = (
    "LTD", "LIMITED", "LLP", "PVT", "PRIVATE", "CORP", "CORPORATION",
    "INDUSTRIES", "ENTERPRISES", "SOLUTIONS", "SERVICES", "SYSTEMS",
    "TECHNOLOGIES", "PRODUCTS", "WORKS", "COMPANY",
)


def extract_entity(description: str):
    original = str(description or "").strip()
    text = normalize_description(original).upper()
    raw_upper = original.upper()
    rail = next((rail for rail in RAILS if re.search(rf"\b{rail}\b", raw_upper)), None)
    if any(term in raw_upper for term in GOVERNMENT_TERMS):
        return {
            "counterparty_name": next((term.title() for term in GOVERNMENT_TERMS if term in text), None),
            "counterparty_type": "GOVERNMENT / TAX",
            "counterparty_industry": "Government / Tax",
            "counterparty_confidence": 0.9,
            "payment_rail": rail,
        }
    parts = [part.strip(" -_/") for part in re.split(r"[/|-]", original) if part.strip(" -_/")]
    candidate = ""
    for part in reversed(parts):
        cleaned = re.sub(r"\b(?:CR|DR)\b.*$", "", part, flags=re.I).strip(" -_/")
        cleaned = re.sub(r"\b\d{5,}\b|[\w.+-]+@[\w.-]+", "", cleaned).strip(" -_/")
        if cleaned and cleaned.upper() not in {"UPI", "NEFT", "IMPS", "RTGS", "CR", "DR"}:
            candidate = cleaned
            break
    if not candidate or len(candidate.split()) > 7:
        return {
            "counterparty_name": None,
            "counterparty_type": "UNKNOWN",
            "counterparty_industry": None,
            "counterparty_confidence": 0.0,
            "payment_rail": rail,
        }
    upper = candidate.upper()
    if any(term in upper.split() for term in BUSINESS_TERMS):
        entity_type = "BUSINESS"
        confidence = 0.88
    elif len(candidate.split()) in {2, 3} and all(re.fullmatch(r"[A-Za-z.'-]+", part) for part in candidate.split()):
        entity_type = "PERSON"
        confidence = 0.72 if rail else 0.55
    else:
        entity_type = "UNKNOWN"
        confidence = 0.0
    return {
        "counterparty_name": candidate.title() if entity_type != "UNKNOWN" else None,
        "counterparty_type": entity_type,
        "counterparty_industry": None,
        "counterparty_confidence": confidence,
        "payment_rail": rail,
    }
