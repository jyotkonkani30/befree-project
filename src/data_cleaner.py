import re
from dateutil import parser
import pandas as pd


def normalize_amount(value):
    if value is None or (isinstance(value, float) and pd.isna(value)) or str(value).strip() in {"", "-", "—", "–"}:
        return 0.0
    text = str(value).replace("₹", "").replace("$", "").strip()
    if re.fullmatch(r"-?\d+,\d{2}", text):
        text = text.replace(",", ".")
    else:
        text = text.replace(",", "")
    text = re.sub(r"(?i)\s*(dr|cr)$", "", text)
    try:
        return float(text.replace("(", "-").replace(")", ""))
    except ValueError:
        return None


def normalize_date(value):
    if not value:
        return None
    try:
        return parser.parse(str(value), dayfirst=True, fuzzy=False).date().isoformat()
    except (ValueError, TypeError, OverflowError):
        return None


def clean_transactions(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    for column in ["debit", "credit", "balance"]:
        result[column] = result.get(column, pd.Series(index=result.index)).map(normalize_amount)
    result["date"] = result.get("date", pd.Series(index=result.index)).map(normalize_date)
    result["description"] = result.get("description", pd.Series(index=result.index)).fillna("").astype(str).str.replace(r"\s+", " ", regex=True).str.strip()
    return result
