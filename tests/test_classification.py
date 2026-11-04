import pandas as pd
from src.hybrid_classifier import classify_transactions
from src.rule_classifier import classify_rule


CASES = {
    "TEA TRAIL CAFE VADODARA": "Food & Dining",
    "DOMINOS PIZZA": "Food & Dining",
    "VISHAL MEGA MART": "Groceries",
    "RAPIDO MOBILITY RIDE": "Transportation",
    "ADANI ELECTRICITY BILL": "Utilities",
    "AIRTEL BROADBAND": "Utilities",
    "INDIAN OIL FUEL STATION": "Fuel",
    "GUJARAT UNIVERSITY FEE": "Education",
    "SPOTIFY PREMIUM": "Entertainment",
    "MYNTRA FASHION ORDER": "Shopping",
    "BAJAJ FINANCE EMI": "EMI & Loan Payments",
    "UNKNOWN MERCHANT TXN": "Other / Unclassified",
    "UPI REFUND AMAZON ORDER": "Refunds",
    "SALARY CREDIT ACME": "Salary",
    "ATM CASH WITHDRAWAL": "ATM Withdrawal",
    "CASH DEPOSIT BRANCH": "Other / Unclassified",
}


def test_merchant_rules():
    for description, expected in CASES.items():
        predicted, _ = classify_rule(description)
        if expected == "Other / Unclassified":
            assert predicted is None
        else:
            assert predicted == expected


def test_hybrid_classifies_every_case():
    frame = classify_transactions(pd.DataFrame({"description": list(CASES)}))
    assert len(frame) == len(CASES)
    assert frame["category"].notna().all()
    assert frame["classification_method"].notna().all()


def test_generic_transfer_requires_evidence():
    predicted, _ = classify_rule("UNKNOWN TRANSFER")
    assert predicted is None


def test_tax_payment_stays_outside_financial_taxonomy():
    result = classify_transactions(pd.DataFrame({"description": ["NEFT-REF-GST PAYMENT"]}))
    assert result.iloc[0]["category"] == "Other / Unclassified"
    assert result.iloc[0]["needs_review"]
