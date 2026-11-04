import pandas as pd


def validate_balances(frame: pd.DataFrame, opening_balance):
    previous = opening_balance
    flags = []
    for _, row in frame.iterrows():
        if previous is None or row.get("balance") is None:
            flags.append(False)
            if row.get("balance") is not None:
                previous = row["balance"]
            continue
        expected = previous - (row.get("debit") or 0) + (row.get("credit") or 0)
        actual = row["balance"]
        flags.append(abs(expected - actual) > 0.01)
        previous = actual
    return frame.assign(balance_discrepancy=flags)
