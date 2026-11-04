import re


GENERIC_HEADINGS = {
    "account statement",
    "statement of account",
    "customer copy",
    "statement",
    "account details",
    "customer details",
    "transaction details",
}
INSTITUTION_TERMS = re.compile(
    r"\b(?:bank|banking|finance|financial|credit|co[\s-]?operative|cooperative|"
    r"small\s+finance|trust|society|mutual)\b",
    re.I,
)
SUPPORT_TERMS = re.compile(r"\b(?:ifsc|ifs\s*c|branch|micr|swift|routing|statement)\b", re.I)
EXCLUDED_TERMS = re.compile(
    r"\b(?:account\s+holder|customer|account\s+(?:number|no|type)|"
    r"statement\s+period|opening|closing|balance|address|date|page|"
    r"phone|email|details|information|transaction|debit|credit)\b",
    re.I,
)


def _clean_candidate(value):
    value = re.sub(r"\s+", " ", value or "").strip(" \t|:;,.\"'`“”‘’")
    value = re.sub(r"^[^A-Za-z]+", "", value)
    value = re.sub(r"[^A-Za-z0-9&.'()/-]+$", "", value).strip()
    value = re.sub(r"\s+[a-z]$", "", value)
    return value


def _pages(text):
    return [
        [re.sub(r"\s+", " ", line).strip() for line in page.splitlines() if line.strip()]
        for page in str(text).split("\f")
    ]


def extract_bank_heading(text, source="combined"):
    candidates = []
    for page_number, lines in enumerate(_pages(text), start=1):
        header_limit = max(8, min(len(lines), int(len(lines) * 0.3)))
        header = lines[:header_limit]
        for index, raw_line in enumerate(header):
            value = _clean_candidate(raw_line)
            normalized = re.sub(r"[^a-z0-9 ]", "", value.casefold()).strip()
            if len(value) < 3 or normalized in GENERIC_HEADINGS:
                continue
            if EXCLUDED_TERMS.search(value) or re.search(r"\d{4,}", value):
                continue
            letters = [character for character in value if character.isalpha()]
            uppercase_ratio = sum(character.isupper() for character in letters) / max(1, len(letters))
            institution = bool(INSTITUTION_TERMS.search(value))
            short_brand = bool(re.fullmatch(r"[A-Z][A-Z0-9&.-]{1,9}", value))
            nearby = " ".join(header[max(0, index - 3):index + 4])
            support = bool(SUPPORT_TERMS.search(nearby))
            repeated = sum(value.casefold() == other.casefold() for other in lines) > 1
            if not institution and not (short_brand and (support or repeated or index < 2)):
                continue
            score = 0.0
            score += max(0.0, 3.0 - index * 0.15)
            score += 4.0 if institution else 2.0
            score += 1.5 if uppercase_ratio >= 0.7 else 0.0
            score += 1.5 if support else 0.0
            score += 1.0 if repeated else 0.0
            score -= 1.0 if len(value) > 70 else 0.0
            evidence = []
            if index < 3:
                evidence.append("top header position")
            if institution:
                evidence.append("institutional term")
            if uppercase_ratio >= 0.7:
                evidence.append("uppercase/prominent text")
            if support:
                evidence.append("near branch or IFSC metadata")
            if repeated:
                evidence.append("repeated institutional heading")
            candidates.append((score, page_number, index, value, evidence))
    if not candidates:
        return {
            "bank_name": None,
            "bank_name_raw": None,
            "bank_name_source_page": None,
            "bank_name_source_region": "top_30_percent",
            "bank_name_confidence": 0.0,
            "bank_name_source": source,
            "bank_name_evidence": [],
        }
    score, page, _, value, evidence = max(candidates, key=lambda item: (item[0], -item[1], -item[2]))
    confidence = min(0.99, round(0.35 + score / 14.0, 2))
    return {
        "bank_name": value,
        "bank_name_raw": value,
        "bank_name_raw_text": value,
        "bank_name_source_page": page,
        "bank_name_source_region": "top_30_percent",
        "bank_name_confidence": confidence,
        "bank_name_source": source,
        "bank_name_evidence": evidence,
    }
