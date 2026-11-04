# Befree

Befree is a Streamlit application for extracting, validating, classifying, and exporting bank statement transactions from text-based, scanned, and mixed PDFs.

## Features

- PDF text and OCR extraction
- Account and statement metadata detection
- Transaction parsing with balance validation
- Rule-based classification with TF-IDF and Logistic Regression fallback
- Counterparty and payment-rail extraction
- Duplicate and reconciliation checks
- CSV and Excel exports with clean, consistent columns
- Extraction diagnostics for rejected or uncertain records

The application preserves uncertain values and reports validation issues rather than fabricating financial data. Classification does not use an LLM or an external AI API.

## Output

Exports contain:

`Transaction Date`, `Transaction ID`, `Description`, `Counterparty`, `Payment Rail`, `Debit`, `Credit`, `Balance`, and `Category`.
