from pathlib import Path
import pandas as pd
from src.pdf_detector import detect_pdf_type
from src.data_cleaner import normalize_amount, normalize_date
from src.transaction_extractor import extract_transactions
from src.rule_classifier import classify_rule
from src.duplicate_detector import find_duplicates
from src.balance_reconciler import validate_balances
from src.csv_exporter import export_csv
from src.excel_exporter import export_excel
from src.transaction_output import prepare_transaction_output, OUTPUT_COLUMNS
from openpyxl import load_workbook
from io import BytesIO


def test_normalizers():
    assert normalize_amount("₹1,234.50") == 1234.5
    assert normalize_date("31/01/2024") == "2024-01-31"


def test_transaction_extraction():
    frame = extract_transactions("Date|Description|Debit|Credit|Balance\n01/01/2024|UPI SWIGGY|450||9550")
    assert len(frame) == 1 and frame.iloc[0]["debit"] == 450


def test_rule_classifier():
    assert classify_rule("UPI/SWIGGY/123")[0] == "Food & Dining"


def test_validation_helpers():
    frame = pd.DataFrame([{"date": "2024-01-01", "description": "x", "debit": 10, "credit": None, "balance": 90}])
    assert find_duplicates(pd.concat([frame, frame])).is_duplicate.all()
    assert not validate_balances(frame, 100).balance_discrepancy.iloc[0]


def test_exports():
    frame = pd.DataFrame([{"date": "2024-01-01", "description": "x", "debit": 1, "credit": None, "balance": 9}])
    csv = export_csv(frame).decode("utf-8-sig")
    assert csv.splitlines()[0].split(",") == OUTPUT_COLUMNS
    workbook = load_workbook(BytesIO(export_excel(frame, {"bank_name": "Test"})))
    assert workbook.sheetnames == ["Transactions"]
    assert [cell.value for cell in workbook["Transactions"][1]] == OUTPUT_COLUMNS


def test_transaction_output_is_public_fields_only():
    frame = pd.DataFrame([{
        "date": "02/01/2024",
        "transaction_id": "S80703650",
        "description": "IMPS HEALTHCARE",
        "counterparty_name": "Healthcare Products Ltd",
        "payment_rail": "IMPS",
        "debit": 0,
        "credit": 101795.99,
        "balance": 905250.75,
        "category": "Healthcare",
        "classification_method": "rule",
        "confidence_score": 0.99,
        "is_duplicate": False,
        "validation_warning": "",
        "balance_discrepancy": False,
    }])
    output = prepare_transaction_output(frame)
    assert list(output.columns) == OUTPUT_COLUMNS
    assert output.iloc[0]["Transaction Date"] == "02-01-2024"
    assert output.iloc[0]["Counterparty"] == "Healthcare Products Ltd"
    assert output.iloc[0]["Payment Rail"] == "IMPS"
    assert output.iloc[0]["Debit"] == 0
    assert output.iloc[0]["Credit"] == 101795.99


def test_transaction_output_normalizes_payment_rails_and_excludes_internal_fields():
    frame = pd.DataFrame([
        {
            "date": "2024-01-03",
            "description": "ATM WDL-123",
            "debit": 3000,
            "credit": 0,
            "balance": 5000,
            "category": "ATM Withdrawal",
            "classification_method": "rule",
            "confidence_score": 0.99,
            "matched_rule": "atm",
            "counterparty_industry": "cash",
            "counterparty_confidence": 0.9,
            "is_duplicate": False,
            "validation_warning": "",
            "balance_discrepancy": False,
        },
        {
            "date": "04/01/2024",
            "description": "CHQ PAID-ABC",
            "debit": 100,
            "credit": 0,
            "balance": 4900,
            "category": "Other / Unclassified",
        },
    ])
    output = prepare_transaction_output(frame)
    assert output["Payment Rail"].tolist() == ["ATM", "CHEQUE"]
    assert not any("confidence" in column.lower() or "warning" in column.lower() for column in output.columns)


def test_excel_formats_date_and_amounts():
    frame = pd.DataFrame([{
        "date": "02/01/2024",
        "description": "UPI ORDER",
        "debit": 10,
        "credit": 0,
        "balance": 90,
        "category": "Shopping",
    }])
    worksheet = load_workbook(BytesIO(export_excel(frame)))["Transactions"]
    assert worksheet["A2"].number_format == "DD-MM-YYYY"
    assert worksheet["F2"].number_format == "#,##0.00"
    assert worksheet.freeze_panes == "A2"
    assert worksheet.auto_filter.ref == "A1:I2"


def test_pdf_detection(tmp_path):
    from reportlab.pdfgen.canvas import Canvas
    path = tmp_path / "statement.pdf"
    canvas = Canvas(str(path)); canvas.drawString(20, 800, "A sufficiently long bank statement text"); canvas.save()
    assert detect_pdf_type(path)["type"] == "text-based"
