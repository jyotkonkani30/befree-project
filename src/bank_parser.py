import re


def parse_statement(text: str, tables=None, text_source="combined"):
    from .account_extractor import extract_account_details_with_metadata
    from .transaction_extractor import extract_transactions_with_diagnostics
    metadata = extract_account_details_with_metadata(text, text_source=text_source)
    account = metadata["account"]
    transactions, diagnostics = extract_transactions_with_diagnostics(text, tables or [])
    balance_validation = {"method": "not_available", "warning": None}
    if account["opening_balance"] and len(transactions) and not transactions.empty:
        calculated = float(account["opening_balance"]) - transactions["debit"].sum() + transactions["credit"].sum()
        if account["closing_balance"]:
            balance_validation = {"method": "extracted_and_reconciled", "calculated": round(calculated, 2), "warning": None if abs(calculated - float(account["closing_balance"])) <= 0.01 else "Extracted closing balance does not reconcile"}
        else:
            account["closing_balance"] = f"{calculated:.2f}"
            metadata["methods"]["closing_balance"] = "calculated"
            metadata["validation"]["closing_balance"] = "calculated"
            balance_validation = {"method": "calculated", "calculated": round(calculated, 2), "warning": None}
    return {"bank": account["bank_name"] or "Not Available", "account": account, "account_metadata": metadata, "transactions": transactions, "diagnostics": diagnostics, "balance_validation": balance_validation}
