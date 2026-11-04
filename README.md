# Bank Statement Processing & Classification System

This focused Streamlit prototype extracts text from text, scanned, and mixed PDFs, parses account and transaction fields, validates records, and classifies transactions with deterministic rules followed by a traditional TF-IDF/LogisticRegression model. No LLM is used for classification.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Install the Tesseract binary and Poppler separately for OCR (macOS: `brew install tesseract poppler`).

## Run

```bash
python scripts/generate_synthetic_data.py
python scripts/generate_synthetic_pdfs.py
python scripts/build_training_dataset.py
python scripts/train_classifier.py
streamlit run app.py
pytest -v
```

Synthetic PDFs are simulated bank layouts for demonstration and testing, not official bank templates. The application preserves uncertain rows and emits validation flags rather than silently changing financial values.
