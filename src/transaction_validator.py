import pandas as pd


def validate_transactions(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    result["validation_warning"] = ""
    both = result["debit"].fillna(0).ne(0) & result["credit"].fillna(0).ne(0)
    result.loc[both, "validation_warning"] = "Both debit and credit populated"
    missing = result["date"].isna() | result["description"].eq("")
    result.loc[missing & ~both, "validation_warning"] = "Missing date or description"
    result.loc[missing & both, "validation_warning"] = "Both debit and credit populated; missing date or description"
    return result
