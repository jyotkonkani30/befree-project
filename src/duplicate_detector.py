import pandas as pd


def find_duplicates(frame: pd.DataFrame) -> pd.DataFrame:
    keys = [c for c in ["date", "description", "debit", "credit", "balance"] if c in frame]
    return frame.assign(is_duplicate=frame.duplicated(keys, keep=False))
