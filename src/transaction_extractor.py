import re
import pandas as pd
from .data_cleaner import clean_transactions

DATE = r"\d{1,2}[/-]\d{1,2}[/-](?:\d{4}|\d{2})|\d{1,2}[-/][A-Za-z]{3,9}[-/](?:\d{4}|\d{2})"
AMOUNT = r"(?:₹|\$)?\s*\(?-?[\d,]+(?:[.,]\d{1,2})?\)?\s*(?:Dr|Cr)?"


def _header_index(row):
    labels = {
        "date": ("date", "txn date", "transaction date", "value date", "posting date"),
        "description": ("description", "transaction details", "narration", "particulars", "remarks"),
        "debit": ("debit", "withdrawal", "withdrawal amount", "dr", "amount debited"),
        "credit": ("credit", "deposit", "deposit amount", "cr", "amount credited"),
        "direction": ("cr/dr", "dr/cr", "credit/debit", "debit/credit"),
        "amount": ("transaction amount", "amount", "transaction value"),
        "balance": ("balance", "closing balance", "available balance", "running balance"),
    }
    normalized = [re.sub(r"[^a-z]", "", str(value or "").lower()) for value in row]
    result = {}
    for field, names in labels.items():
        for index, value in enumerate(normalized):
            aliases = [re.sub(r"[^a-z]", "", name) for name in names]
            if any(value == alias or value.startswith(alias) or alias in value for alias in aliases):
                result[field] = index
                break
    return result


def _table_rows(tables):
    for table in tables:
        if not table:
            continue
        header_at = next((index for index, row in enumerate(table[:5]) if len(_header_index(row)) >= 3), None)
        if header_at is None:
            continue
        indexes = _header_index(table[header_at])
        for row in table[header_at + 1:]:
            values = [
                re.sub(r"\b[A-Z]\b", "", str(value or "").replace("\n", " ")).strip()
                for value in row
            ]
            values = [re.sub(r"^-\s+(?=\d)", "", value) for value in values]
            values = [re.sub(r"(?<=\d)\s+(?=\d)", "", value) for value in values]
            lowered = " ".join(values).lower()
            if not values or re.search(r"\b(opening|closing|total|summary|brought forward|carried forward)\b", lowered):
                continue
            date = values[indexes["date"]] if "date" in indexes and indexes["date"] < len(values) else ""
            description = values[indexes["description"]] if "description" in indexes and indexes["description"] < len(values) else ""
            if not re.fullmatch(DATE, date):
                continue
            debit = values[indexes["debit"]] if "debit" in indexes and indexes["debit"] < len(values) else ""
            credit = values[indexes["credit"]] if "credit" in indexes and indexes["credit"] < len(values) else ""
            if "amount" in indexes and indexes["amount"] < len(values):
                amount = values[indexes["amount"]]
                direction = values[indexes["direction"]].strip().casefold() if "direction" in indexes and indexes["direction"] < len(values) else ""
                debit = amount if direction in {"dr", "debit"} else ""
                credit = amount if direction in {"cr", "credit"} else ""
            yield {
                "date": date,
                "description": description,
                "debit": debit,
                "credit": credit,
                "balance": values[indexes["balance"]] if "balance" in indexes and indexes["balance"] < len(values) else "",
            }


def _line_row(line):
    line = re.sub(r"(?<!\w)a(?!\w)", "-", line, flags=re.I)
    if "|" in line:
        parts = [part.strip() for part in line.split("|")]
        if len(parts) >= 5 and re.fullmatch(DATE, parts[0]):
            return {"date": parts[0], "description": parts[1], "debit": parts[2], "credit": parts[3], "balance": parts[4]}
    dates = list(re.finditer(DATE, line, re.I))
    direction = re.search(r"\b(CR|DR)\b", line, re.I)
    if dates and direction and direction.start() > dates[0].end():
        amounts = re.findall(AMOUNT, line[direction.end():], re.I)
        if len(amounts) >= 2:
            description_end = direction.start()
            description_start = dates[1].end() if len(dates) > 1 else dates[0].end()
            description = line[description_start:description_end]
            description = re.sub(r"^[\s|:-]+|[\s|:-]+$", "", description)
            description = re.sub(r"^\d{1,2}:\d{2}:\d{2}\s*(?:AM|PM)?\s*", "", description, flags=re.I)
            return {
                "date": dates[0].group(0),
                "description": description,
                "debit": amounts[0] if direction.group(1).upper() == "DR" else "",
                "credit": amounts[0] if direction.group(1).upper() == "CR" else "",
                "balance": amounts[-1],
            }
    match = re.match(rf"^\s*({DATE})\s+(.+?)\s+({AMOUNT}|—|-)\s+({AMOUNT}|—|-)\s+({AMOUNT}|—|-)\s*$", line, re.I)
    if match:
        date, description, debit, credit, balance = match.groups()
        return {"date": date, "description": description, "debit": debit, "credit": credit, "balance": balance}
    return None


def _amount_line(line):
    cleaned = re.sub(r"(?<!\w)a(?!\w)", "-", line, flags=re.I)
    values = re.findall(AMOUNT, cleaned, re.I)
    if not values or " ".join(values).strip() != cleaned.strip():
        return None
    if not any("," in value or "." in value or "₹" in value or "$" in value for value in values):
        return None
    return values


def _text_rows(text):
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines() if line.strip()]
    rows = []
    current = None
    in_transactions = False
    direct_rows = []
    for index, line in enumerate(lines):
        direct_row = _line_row(line)
        if direct_row:
            direct_rows.append(direct_row)
            continue
        if re.search(r"\bdate\b.*\bdescription\b", line, re.I) or (
            line.casefold() == "date" and index + 1 < len(lines) and lines[index + 1].casefold() == "description"
        ):
            in_transactions = True
            continue
        if re.search(r"opening\s+balance|total\s+debits?|total\s+credits?|closing\s+balance", line, re.I):
            continue
        if not in_transactions:
            continue
        date_match = re.match(rf"^({DATE})\s*(.*)$", line, re.I)
        if date_match:
            if " to " in line.casefold():
                continue
            if current:
                rows.append(current)
            current = {"date": date_match.group(1), "description": date_match.group(2).strip(), "amount_lines": []}
            continue
        if not in_transactions or current is None:
            continue
        if re.search(r"\bsummary\b", current["description"], re.I):
            continue
        amounts = _amount_line(line)
        if amounts and len(amounts) <= 3:
            current["amount_lines"].extend(amounts)
        elif not re.search(r"page\s+\d+|this is a computer|running balance", line, re.I):
            if re.search(r"\bsummary\b", current["description"], re.I) and re.search(r"\b(?:INR|total|opening|closing)\b", line, re.I):
                continue
            current["description"] = f"{current['description']} {line}".strip()
    if current:
        rows.append(current)
    normalized = list(direct_rows)
    for row in rows:
        amounts = row.pop("amount_lines")
        if len(amounts) >= 2:
            credit_hint = re.search(r"\b(?:CR|CREDIT|SALARY|REFUND|CASH\s+DEPOSIT|INTEREST|INT\.PD)\b|UPI/CR", row["description"], re.I)
            normalized.append({
                "date": row["date"],
                "description": row["description"],
                "debit": amounts[-3] if len(amounts) == 3 else ("" if credit_hint else amounts[-2]),
                "credit": amounts[-2] if len(amounts) == 3 else (amounts[-2] if credit_hint else ""),
                "balance": amounts[-1],
            })
        else:
            normalized.append({"date": row["date"], "description": row["description"], "debit": "", "credit": "", "balance": ""})
    return normalized


def extract_transactions_with_diagnostics(text: str, tables=None):
    rows = list(_table_rows(tables or []))
    rejected = []
    candidate_count = 0
    if not rows:
        rows = _text_rows(text)
        candidate_count = len(rows)
    if not rows:
        pending = None
        for raw in text.splitlines():
            line = re.sub(r"\s+", " ", raw).strip()
            if not line or re.search(r"date|description|opening balance|closing balance|total", line, re.I):
                continue
            if re.match(rf"^\s*({DATE})\b", line):
                candidate_count += 1
            parsed = _line_row(line)
            if parsed:
                if pending:
                    rows.append(pending)
                pending = parsed
            elif pending:
                pending["description"] += " " + line
            elif re.match(rf"^\s*({DATE})\b", line):
                rejected.append({"row": line, "reason": "date found but amount columns did not match"})
        if pending:
            rows.append(pending)
    result = clean_transactions(pd.DataFrame(rows, columns=["date", "description", "debit", "credit", "balance"]))
    for index in range(1, len(result)):
        previous_balance = float(result.iloc[index - 1]["balance"])
        current_balance = float(result.iloc[index]["balance"])
        debit = float(result.iloc[index]["debit"])
        credit = float(result.iloc[index]["credit"])
        delta = round(current_balance - previous_balance, 2)
        if debit > 0 and credit == 0 and abs(delta - debit) < 0.01:
            result.at[index, "debit"] = 0.0
            result.at[index, "credit"] = debit
        elif credit > 0 and debit == 0 and abs(delta + credit) < 0.01:
            result.at[index, "credit"] = 0.0
            result.at[index, "debit"] = credit
    result.insert(0, "transaction_id", [f"TXN-{index:05d}" for index in range(1, len(result) + 1)])
    return result, {
        "detected_tables": len(tables or []),
        "table_rows": sum(len(table) for table in (tables or []) if table),
        "candidate_transaction_rows": candidate_count or len(rows),
        "successful_transactions": len(result),
        "rejected_rows": rejected,
    }


def extract_transactions(text: str, tables=None) -> pd.DataFrame:
    return extract_transactions_with_diagnostics(text, tables)[0]
