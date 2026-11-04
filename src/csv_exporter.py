import pandas as pd
from .transaction_output import prepare_transaction_output


def export_csv(frame: pd.DataFrame) -> bytes:
    output = prepare_transaction_output(frame)
    for column in ("Debit", "Credit", "Balance"):
        output[column] = pd.to_numeric(output[column], errors="coerce").astype(float)
    return output.to_csv(index=False, float_format="%.2f").encode("utf-8-sig")
