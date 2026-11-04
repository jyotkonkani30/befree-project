import pandas as pd


OUTPUT_COLUMNS = [
    "Transaction Date",
    "Transaction ID",
    "Description",
    "Counterparty",
    "Payment Rail",
    "Debit",
    "Credit",
    "Balance",
    "Category",
]


def _column(frame, *names):
    for name in names:
        if name in frame.columns:
            return frame[name]
    return pd.Series("", index=frame.index)


def prepare_transaction_output(frame: pd.DataFrame) -> pd.DataFrame:
    result = pd.DataFrame(index=frame.index)
    dates = pd.to_datetime(_column(frame, "date", "transaction_date", "Transaction Date"), errors="coerce", dayfirst=True)
    result["Transaction Date"] = dates.dt.strftime("%d-%m-%Y").fillna("")
    result["Transaction ID"] = _column(frame, "transaction_id", "Transaction ID").fillna("").astype(str).replace("nan", "")
    result["Description"] = _column(frame, "description", "description_original", "Description").fillna("").astype(str)
    descriptions = result["Description"].str.upper()
    counterparties = _column(frame, "counterparty_name", "Counterparty").fillna("").astype(str).replace("nan", "")
    result["Counterparty"] = counterparties
    rails = _column(frame, "payment_rail", "Payment Rail").fillna("").astype(str).str.upper().str.strip()
    rail_patterns = (
        ("UPI", r"\bUPI\b"),
        ("NEFT", r"\bNEFT\b"),
        ("IMPS", r"\bIMPS\b"),
        ("RTGS", r"\bRTGS\b"),
        ("ATM", r"\bATM\b"),
        ("CASH", r"\bCASH\s+(?:WITHDRAWAL|DEPOSIT)\b"),
        ("CHEQUE", r"\b(?:CHQ|CHEQUE)\b"),
    )
    for rail, pattern in rail_patterns:
        rails = rails.mask(rails.eq("") & descriptions.str.contains(pattern, regex=True, na=False), rail)
    result["Payment Rail"] = rails.replace("", "UNKNOWN")
    debit = pd.to_numeric(_column(frame, "debit", "Debit"), errors="coerce").fillna(0.0)
    credit = pd.to_numeric(_column(frame, "credit", "Credit"), errors="coerce").fillna(0.0)
    result["Debit"] = debit.round(2)
    result["Credit"] = credit.round(2)
    result["Balance"] = pd.to_numeric(_column(frame, "balance", "Balance"), errors="coerce").round(2)
    result["Category"] = _column(frame, "category", "Category").fillna("Other / Unclassified").astype(str)
    return result[OUTPUT_COLUMNS].reset_index(drop=True)
