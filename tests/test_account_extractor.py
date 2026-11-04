from src.account_extractor import extract_account_details, extract_account_details_with_metadata
import pandas as pd


def test_holder_and_ifsc_on_same_line():
    result = extract_account_details("Account Holder: Rohan Desai IFs$c: WCBK0000625")
    assert result["account_holder"] == "Rohan Desai"
    assert result["ifsc"] == "WCBK0000625"


def test_separate_metadata_lines_and_summary_sequence():
    text = """Customer Name
Anita Rao
Account No.
XXXXXX1234
IFSC Code
ABCD0001234
Opening Balance
Total Debits
Total Credits
Closing Balance
Rs. 63,800.00
Rs. 72,686.00
Rs. 84,120.00
Rs. 75,234.00"""
    result = extract_account_details(text)
    assert result["account_holder"] == "Anita Rao"
    assert result["account_number"] == "XXXXXX1234"
    assert result["opening_balance"] == "63800.00"
    assert result["closing_balance"] == "75234.00"


def test_ocr_currency_prefix_and_negative_amount():
    result = extract_account_details("Opening Balance: I92,500.00\nClosing Balance: -1,250.50")
    assert result["opening_balance"] == "92500.00"
    assert result["closing_balance"] == "-1250.50"


def test_bank_heading_reference_matches_available_pdf_headings():
    references = pd.read_csv("data/bank_name_heading_reference.csv")
    for heading in references["expected_bank_heading"].dropna().unique():
        text = f"{heading}\nAccount Statement\nAccount Holder\nAarav Mehta"
        assert extract_account_details(text)["bank_name"] == heading


def test_bank_heading_does_not_use_account_holder():
    result = extract_account_details("Account Statement\nAarav Mehta\nAccount Holder\nAarav Mehta")
    assert result["bank_name"] is None


def test_ocr_bank_heading_is_normalized_and_has_evidence():
    result = extract_account_details_with_metadata("‘SBI\nAccount Statement\nIFSC: SBIN0004567", text_source="OCR")
    assert result["account"]["bank_name"] == "SBI"
    assert result["account"]["bank_name_source"] == "OCR"
    assert result["account"]["bank_name_page"] == 1
    assert result["account"]["bank_name_evidence"]
