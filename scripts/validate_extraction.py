import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pandas as pd
from src.bank_parser import parse_statement
from src.duplicate_detector import find_duplicates
from src.text_extractor import extract_pages
from src.transaction_validator import validate_transactions
from src.hybrid_classifier import classify_transactions


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf")
    parser.add_argument("--expected", required=True)
    parser.add_argument("--output", default="data/extraction_report.json")
    args = parser.parse_args()
    expected = json.loads(Path(args.expected).read_text())
    extracted = extract_pages(Path(args.pdf).read_bytes())
    parsed = parse_statement(extracted["text"], extracted.get("tables"))
    transactions = validate_transactions(find_duplicates(classify_transactions(parsed["transactions"])))
    expected_rows = pd.DataFrame(expected.get("transactions", []))
    actual_rows = transactions.to_dict("records")
    report = {
        "pdf_type": extracted["pdf_type"],
        "page_count": extracted["page_count"],
        "expected_transaction_count": len(expected_rows),
        "actual_transaction_count": len(transactions),
        "account": parsed["account"],
        "account_matches": {key: parsed["account"].get(key) == value for key, value in expected.get("account", {}).items()},
        "duplicate_transaction_count": int(transactions["is_duplicate"].sum()) if "is_duplicate" in transactions else 0,
        "classification_results": transactions[["transaction_id", "category", "classification_method", "confidence_score"]].to_dict("records"),
        "transactions": actual_rows,
    }
    if not expected_rows.empty and len(expected_rows) == len(transactions):
        comparable = ["date", "description", "debit", "credit", "balance"]
        report["field_accuracy"] = {
            field: float((expected_rows[field].fillna("").astype(str).str.strip().values == transactions[field].fillna("").astype(str).str.strip().values).mean())
            for field in comparable if field in expected_rows and field in transactions
        }
    else:
        report["field_accuracy"] = {}
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(report, indent=2, default=str))
    print(json.dumps({key: report[key] for key in ("expected_transaction_count", "actual_transaction_count", "field_accuracy")}, indent=2))


if __name__ == "__main__":
    main()
