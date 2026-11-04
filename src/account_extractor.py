import re
from typing import Dict, Optional
from .bank_heading import extract_bank_heading


AMOUNT_PATTERN = r"(?:₹|Rs\.?|INR|I)\s*[\(\-]?\s*[\d,]+(?:\.\d{1,2})?\s*\)?|[\(\-]?\s*[\d,]+(?:\.\d{1,2})?\s*\)?"
IFSC_PATTERN = r"\b([A-Z]{4}0[A-Z0-9]{6})\b"
METADATA_LABELS = r"(?:IFSC|IFS.?C|LFS.?C|Account\s*(?:Number|No)|A/C|Branch|Customer\s*ID|Account\s*Type|Statement\s*Period)"


def _lines(text):
    return [re.sub(r"\s+", " ", line).strip() for line in str(text).splitlines() if line.strip()]


def _clean(value):
    return re.sub(r"\s+", " ", value or "").strip(" :|")


def _amount(value):
    if not value:
        return None
    value = re.sub(r"(?i)^(?:₹|rs\.?|inr|i)\s*", "", value.strip())
    value = value.replace(",", "").replace("(", "-").replace(")", "")
    value = re.sub(r"(?i)\s*(dr|cr)$", "", value).strip()
    try:
        return f"{float(value):.2f}"
    except ValueError:
        return None


def _value_after_label(lines, patterns):
    label = re.compile("|".join(patterns), re.I)
    for index, line in enumerate(lines):
        match = label.search(line)
        if not match:
            continue
        value = line[match.end():].lstrip(" :|")
        if value and re.search(r"[A-Za-z0-9]", value):
            return _clean(value), "same_line"
        if index + 1 < len(lines):
            return _clean(lines[index + 1]), "next_line"
    return None, None


def _extract_ifsc(text):
    match = re.search(IFSC_PATTERN, text.upper())
    return match.group(1) if match else None


def _extract_holder(lines):
    patterns = [
        r"account\s*holder\s*name(?!\s*(?:details|information))",
        r"account\s*holder(?!\s*(?:details|information))",
        r"customer\s*name",
        r"name\s*of\s*customer",
        r"(?<!account\s)customer(?!\s*id)",
    ]
    label = re.compile("|".join(patterns), re.I)
    stop = re.compile(METADATA_LABELS, re.I)
    for index, line in enumerate(lines):
        match = label.search(line)
        if not match:
            continue
        value = line[match.end():].lstrip(" :-|")
        if not value and index + 1 < len(lines):
            value = lines[index + 1]
        value = stop.split(value)[0]
        value = re.sub(r"(?i)\b(?:ifsc|ifs.?c|lfs.?c)\b.*$", "", value)
        value = re.sub(r"(?i)\b(?:account\s*(?:number|no)|a/c|branch|customer\s*id|account\s*type)\b.*$", "", value)
        value = _clean(value)
        if value and not re.fullmatch(r"details|information|[.]+", value, re.I):
            return value, "label_parser"
    return None, None


def _extract_bank(lines):
    value, method = _value_after_label(lines, [r"bank\s*name", r"name\s*of\s*bank"])
    if value:
        return value, method
    for line in lines:
        match = re.fullmatch(r"[A-Za-z][A-Za-z &.'-]+Bank(?:\s+(?:Ltd|Limited)\.?)?(?:\s*\([^)\n]+\))?", line, re.I)
        if match:
            return match.group(0), "header_parser"
        if re.search(r"\bbank\b", line, re.I) and len(re.findall(r"[A-Za-z]", line)) >= 8:
            return _clean(line), "header_parser"
    return None, None


def _extract_balances(lines):
    opening = closing = None
    opening_method = closing_method = None
    opening_patterns = [r"opening\s*balance", r"previous\s*balance", r"balance\s*b/?f", r"balance\s*brought\s*forward", r"beginning\s*balance"]
    closing_patterns = [r"closing\s*balance", r"available\s*closing\s*balance", r"ending\s*balance", r"balance\s*c/?f", r"balance\s*carried\s*forward"]
    opening_value, opening_method = _value_after_label(lines, opening_patterns)
    closing_value, closing_method = _value_after_label(lines, closing_patterns)
    opening = _amount(re.search(AMOUNT_PATTERN, opening_value or "", re.I).group(0)) if opening_value and re.search(AMOUNT_PATTERN, opening_value, re.I) else None
    closing = _amount(re.search(AMOUNT_PATTERN, closing_value or "", re.I).group(0)) if closing_value and re.search(AMOUNT_PATTERN, closing_value, re.I) else None
    opening_index = next((index for index, line in enumerate(lines) if re.search(r"opening(?:\s*balance)?|previous\s*balance|beginning\s*balance", line, re.I)), None)
    closing_index = next((index for index, line in enumerate(lines) if re.search(r"closing(?:\s*balance)?|ending\s*balance", line, re.I)), None)
    if opening_index is not None and closing_index is not None and closing_index > opening_index:
        amounts = []
        for line in lines[closing_index + 1:closing_index + 7]:
            amounts.extend(re.findall(AMOUNT_PATTERN, line, re.I))
        if len(amounts) >= 2:
            opening = _amount(amounts[0])
            closing = _amount(amounts[-1])
            opening_method = "summary_sequence"
            closing_method = "summary_sequence"
        elif len(amounts) == 1 and opening_index + 1 == closing_index:
            opening = opening or _amount(amounts[0])
            closing = closing or _amount(amounts[0])
        if opening and closing:
                opening_method = "summary_sequence"
                closing_method = "summary_sequence"
    for index, line in enumerate(lines):
        if re.search(r"opening", line, re.I) and re.search(r"closing", line, re.I):
            if index + 1 < len(lines):
                amounts = re.findall(AMOUNT_PATTERN, lines[index + 1], re.I)
                if len(amounts) >= 2:
                    opening = opening or _amount(amounts[0])
                    closing = closing or _amount(amounts[-1])
                    opening_method = opening_method or "summary_sequence"
                    closing_method = closing_method or "summary_sequence"
        elif re.search(r"opening", line, re.I) and re.search(r"closing", line, re.I) is None:
            pass
    return opening, closing, opening_method, closing_method


def extract_account_details_with_metadata(text: str, text_source: str = "combined") -> Dict:
    lines = _lines(text)
    heading = extract_bank_heading(text, source=text_source)
    bank_name = heading["bank_name"]
    bank_method = "heading_detector" if bank_name else None
    if not bank_name:
        bank_name, bank_method = _extract_bank(lines)
    holder, holder_method = _extract_holder(lines)
    if bank_name and holder and re.sub(r"\W", "", bank_name).casefold() == re.sub(r"\W", "", holder).casefold():
        bank_name, bank_method = _extract_bank(lines)
        if bank_name and re.sub(r"\W", "", bank_name).casefold() == re.sub(r"\W", "", holder).casefold():
            bank_name, bank_method = None, None
    account_number, account_method = _value_after_label(lines, [r"account\s*(?:number|no)", r"a/c\s*(?:number|no)"])
    if account_number:
        account_number = re.split(r"(?i)(?:IFSC|IFS.?C|LFS.?C|Account\s*Type|Branch|Statement\s*Period)", account_number)[0]
        account_number = re.sub(r"^[.]+|[.]+$", "", re.sub(r"\s+", "", account_number))
    ifsc = _extract_ifsc(text)
    account_type, type_method = _value_after_label(lines, [r"account\s*type", r"type\s*of\s*account"])
    period, period_method = _value_after_label(lines, [r"statement\s*period", r"period"])
    opening, closing, opening_method, closing_method = _extract_balances(lines)
    account = {
        "bank_name": bank_name,
        "bank_name_raw": heading.get("bank_name_raw"),
        "bank_name_confidence": heading.get("bank_name_confidence", 0.0),
        "bank_name_source": heading.get("bank_name_source"),
        "bank_name_page": heading.get("bank_name_source_page"),
        "bank_name_evidence": heading.get("bank_name_evidence", []),
        "account_holder": holder,
        "account_number": account_number,
        "ifsc": ifsc,
        "account_type": account_type,
        "statement_period": period,
        "opening_balance": opening,
        "closing_balance": closing,
    }
    methods = {
        "bank_name": bank_method, "account_holder": holder_method, "account_number": account_method,
        "ifsc": "pattern_validator" if ifsc else None, "account_type": type_method,
        "statement_period": period_method, "opening_balance": opening_method, "closing_balance": closing_method,
    }
    validation = {key: ("valid" if value is not None else "missing") for key, value in account.items()}
    return {"account": account, "methods": methods, "validation": validation, "bank_heading": heading}


def extract_account_details(text: str) -> Dict[str, Optional[str]]:
    return extract_account_details_with_metadata(text)["account"]
