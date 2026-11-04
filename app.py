import io
import hashlib
import time
import streamlit as st
import pandas as pd
from src.text_extractor import extract_pages
from src.bank_parser import parse_statement
from src.hybrid_classifier import classify_transactions
from src.duplicate_detector import find_duplicates
from src.transaction_validator import validate_transactions
from src.balance_reconciler import validate_balances
from src.csv_exporter import export_csv
from src.excel_exporter import export_excel
from src.transaction_output import prepare_transaction_output

st.set_page_config(page_title="Bank Statement Processing & Classification System", layout="wide")
st.title("Bank Statement Processing & Classification System")
st.caption("Upload your bank statement PDF to automatically extract, classify, and export transactions.")
uploaded = st.file_uploader("Upload bank statement PDF", type=["pdf"])
if uploaded:
    st.write(f"**File:** {uploaded.name} ({uploaded.size:,} bytes)")
    file_data = uploaded.getvalue()
    file_hash = hashlib.sha256(file_data).hexdigest()
    if st.session_state.get("processed_file_hash") != file_hash:
        st.session_state.pop("processed_result", None)
    if st.button("Process Bank Statement", type="primary") and st.session_state.get("processed_file_hash") != file_hash:
        try:
            started = time.perf_counter()
            with st.status("Processing statement..."):
                extracted = extract_pages(file_data)
                parsed = parse_statement(
                    extracted["text"],
                    extracted.get("tables"),
                    text_source={"text-based": "native_text", "image-based": "OCR", "mixed": "combined"}[extracted["pdf_type"]],
                )
                classification_started = time.perf_counter()
                transactions = classify_transactions(parsed["transactions"])
                transactions = validate_transactions(find_duplicates(transactions))
                opening = float(parsed["account"]["opening_balance"]) if parsed["account"]["opening_balance"] else None
                transactions = validate_balances(transactions, opening)
                discrepancy = transactions["balance_discrepancy"].fillna(False)
                transactions.loc[discrepancy & transactions["validation_warning"].eq(""), "validation_warning"] = "Running balance discrepancy"
                transactions.loc[discrepancy & transactions["validation_warning"].ne(""), "validation_warning"] += "; running balance discrepancy"
                extracted["processing_diagnostics"]["classification_seconds"] = round(time.perf_counter() - classification_started, 3)
                extracted["processing_diagnostics"]["total_seconds"] = round(time.perf_counter() - started, 3)
            st.session_state.processed_file_hash = file_hash
            st.session_state.processed_result = (extracted, parsed, transactions)
        except ValueError as error:
            st.error(str(error))
        except RuntimeError as error:
            st.error(str(error))
        except Exception as error:
            st.error(f"Could not process this PDF: {error}")
    if st.session_state.get("processed_file_hash") == file_hash and st.session_state.get("processed_result"):
        extracted, parsed, transactions = st.session_state.processed_result
        try:
            if transactions.empty:
                if extracted["pdf_type"] in {"image-based", "mixed"} and extracted["processing_diagnostics"]["ocr_pages"]:
                    st.error("OCR could not extract any transaction rows from the scanned pages.")
                else:
                    st.error("Account information was detected, but no transaction table was found.")
                st.caption("Review the extraction diagnostics for page, table, and rejected-row details.")
                st.stop()
            st.success(f"Processed {len(transactions)} transactions. PDF type: {extracted['pdf_type']} ({extracted['page_count']} pages).")
            with st.expander("Extraction diagnostics"):
                st.json({
                    "pages": extracted["page_diagnostics"],
                    "transactions": parsed["diagnostics"],
                    "account_fields": parsed["account_metadata"],
                    "balance_validation": parsed["balance_validation"],
                    "processing": extracted["processing_diagnostics"],
                })
            account = {key: value or "Not Available" for key, value in parsed["account"].items()}
            display_account = {
                key: account.get(key, "Not Available")
                for key in (
                    "bank_name",
                    "account_holder",
                    "account_number",
                    "ifsc",
                    "account_type",
                    "statement_period",
                    "opening_balance",
                    "closing_balance",
                )
            }
            if display_account.get("account_number"):
                value = str(display_account["account_number"]).replace(" ", "")
                display_account["account_number"] = "*" * max(0, len(value) - 4) + value[-4:]
            st.subheader("Extracted Account Information")
            st.dataframe(pd.DataFrame([display_account]), use_container_width=True, hide_index=True)
            st.subheader("Classified Transactions")
            display_transactions = prepare_transaction_output(transactions)
            st.dataframe(
                display_transactions,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Debit": st.column_config.NumberColumn(format="₹%.2f"),
                    "Credit": st.column_config.NumberColumn(format="₹%.2f"),
                    "Balance": st.column_config.NumberColumn(format="₹%.2f"),
                },
            )
            st.download_button("Download Classified Transactions (CSV)", export_csv(transactions), "classified_transactions.csv", "text/csv")
            st.download_button("Download Classified Transactions (Excel)", export_excel(transactions, display_account), "classified_transactions.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        except Exception as error:
            st.error(f"Could not process this PDF: {error}")
