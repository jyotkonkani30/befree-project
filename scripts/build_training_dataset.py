import json
import sys
from pathlib import Path
import pandas as pd
from datasets import get_dataset_config_names, load_dataset
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.text_normalizer import normalize_description

TAXONOMY = {
    "Salary", "Food & Dining", "Groceries", "Transportation", "Utilities", "Shopping",
    "ATM Withdrawal", "Healthcare", "Fuel", "Entertainment", "Rent", "Education",
    "EMI & Loan Payments", "Insurance", "Investments", "Bank Charges", "Money Transfer",
    "Refunds", "Travel", "Other / Unclassified",
}
EXTRACTED_CSV = Path("data/bank_statement_extracted_transactions.csv")
ENTITY_CANDIDATES = Path("data/td/bank_statement_entity_aware_training_candidates.csv")

HF_MAPPING = {
    "Restaurants": "Food & Dining", "Groceries": "Groceries", "Transportation": "Transportation",
    "Utilities": "Utilities", "Shopping": "Shopping", "Healthcare": "Healthcare",
    "Entertainment": "Entertainment", "Rent": "Rent", "Education": "Education",
    "Insurance": "Insurance", "Travel": "Travel", "Mortgage": "EMI & Loan Payments",
}


def _standardize_local(path):
    source = "data/test.csv" if Path(path).name == "test.csv" else "data/testing.csv"
    frame = pd.read_csv(path)
    columns = {str(column).strip().lower(): column for column in frame.columns}
    description = columns.get("description")
    category = columns.get("category")
    direction = columns.get("debit_credit")
    if not description or not category:
        return pd.DataFrame(), {"source": source, "original_rows": len(frame), "usable_rows": 0, "rejected_rows": len(frame), "duplicate_rows": 0}
    result = pd.DataFrame({
        "transaction_id": frame[columns.get("transaction_id", description)].astype(str),
        "description": frame[description].fillna("").astype(str).str.strip(),
        "normalized_description": frame[description].fillna("").map(normalize_description),
        "debit_credit": frame[direction].fillna("").astype(str) if direction else "",
        "category": frame[category].fillna("").astype(str).str.strip(),
        "original_category": frame[category].fillna("").astype(str).str.strip(),
        "dataset_source": source,
    })
    return result, _source_stats(result, source, set(result["category"]) & TAXONOMY)


def _source_stats(frame, source, valid_categories):
    duplicate_rows = int(frame.duplicated(["normalized_description", "category"]).sum())
    valid = frame["description"].ne("") & frame["normalized_description"].ne("") & frame["category"].isin(valid_categories)
    return {
        "source": source,
        "original_rows": len(frame),
        "usable_rows": int(valid.sum()),
        "rejected_rows": int((~valid).sum()),
        "duplicate_rows": duplicate_rows,
        "original_labels": sorted(frame["original_category"].unique().tolist()) if "original_category" in frame else [],
        "category_distribution": frame.loc[valid, "category"].value_counts().to_dict(),
    }


def build_extracted_review(
    input_path=EXTRACTED_CSV,
    output_path="data/transaction_labels_for_review.csv",
):
    frame = pd.read_csv(input_path)
    frame["description"] = frame["description"].fillna("").astype(str).str.strip()
    frame["normalized_description"] = frame["description"].map(normalize_description)
    frame["proposed_category"] = frame["provisional_category"].where(
        frame["label_status"].eq("weak_rule_label_review_required"),
        "Other / Unclassified",
    )
    frame["label_source"] = frame["label_status"].map({
        "weak_rule_label_review_required": "weak_supervision",
        "unlabelled_review_required": "unclassified",
    }).fillna("unknown")
    frame["rule_id"] = frame["provisional_category"].where(
        frame["label_status"].eq("weak_rule_label_review_required"), ""
    )
    frame["label_confidence"] = frame["label_status"].map({
        "weak_rule_label_review_required": 0.5,
        "unlabelled_review_required": 0.0,
    }).fillna(0.0)
    frame["review_status"] = "manual_review_required"
    frame.loc[frame["label_status"].eq("unlabelled_review_required"), "proposed_category"] = "Other / Unclassified"
    frame = frame.drop_duplicates(["normalized_description", "direction", "amount", "balance"])
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output_path, index=False)
    return frame


def _load_huggingface(cap_per_category=1200):
    name = "DoDataThings/us-bank-transaction-categories-v2"
    configs = get_dataset_config_names(name)
    dataset = load_dataset(name)
    rows = []
    for split_name, split in dataset.items():
        frame = split.to_pandas()
        for _, row in frame.iterrows():
            original = str(row["category"]).strip()
            mapped = HF_MAPPING.get(original)
            rows.append({
                "transaction_id": f"hf-{split_name}-{len(rows):08d}",
                "description": str(row["description"]).strip(),
                "normalized_description": normalize_description(row["description"]),
                "debit_credit": "",
                "category": mapped or "",
                "original_category": original,
                "dataset_source": f"huggingface:{name}:{split_name}",
            })
    result = pd.DataFrame(rows)
    valid = result["category"].isin(TAXONOMY) & result["description"].ne("") & result["normalized_description"].ne("")
    result = result[valid].copy()
    result = result.groupby("category", group_keys=False).head(cap_per_category)
    stats = _source_stats(pd.DataFrame(rows), f"huggingface:{name}", set(HF_MAPPING.values()))
    stats["configs"] = configs
    stats["splits"] = {split: len(values) for split, values in dataset.items()}
    stats["mapped_labels"] = sorted(set(HF_MAPPING).intersection(set(pd.DataFrame(rows)["original_category"])))
    stats["retained_after_cap"] = len(result)
    return result, stats


def build(output="data/combined_transaction_training_data.csv", report_path="data/dataset_integration_report.json"):
    review = build_extracted_review()
    local_path = Path("data/test.csv") if Path("data/test.csv").exists() else Path("data/testing.csv")
    local, local_stats = _standardize_local(local_path)
    synthetic = pd.read_csv("data/synthetic_transactions.csv")
    synthetic["normalized_description"] = synthetic["description"].map(normalize_description)
    synthetic["transaction_id"] = "synthetic-" + synthetic.index.astype(str)
    synthetic["debit_credit"] = synthetic.apply(lambda row: "Credit" if pd.notna(row["credit"]) else "Debit", axis=1)
    synthetic["original_category"] = synthetic["category"]
    synthetic["dataset_source"] = "synthetic:data/synthetic_transactions.csv"
    synthetic = synthetic[["transaction_id", "description", "normalized_description", "debit_credit", "category", "original_category", "dataset_source"]]
    hf, hf_stats = _load_huggingface()
    combined = pd.concat([local, synthetic, hf], ignore_index=True)
    if ENTITY_CANDIDATES.exists():
        entity = pd.read_csv(ENTITY_CANDIDATES)
        entity = entity[entity["human_verified"].fillna(False).eq(False)].copy()
        entity = entity[entity["label_confidence"].fillna(0).ge(0.9)]
        entity = pd.DataFrame({
            "transaction_id": entity["transaction_id"].astype(str),
            "description": entity["description_original"].fillna("").astype(str),
            "normalized_description": entity["description_normalized"].fillna("").astype(str),
            "debit_credit": entity["direction"].fillna("").astype(str),
            "category": entity["category"].astype(str),
            "original_category": entity["category"].astype(str),
            "dataset_source": "entity_aware_weak_supervision",
        })
        combined = pd.concat([combined, entity], ignore_index=True)
    combined = combined[combined["category"].isin(TAXONOMY) & combined["normalized_description"].ne("")]
    combined["duplicate_key"] = combined["normalized_description"] + "|" + combined["category"]
    combined = combined.drop_duplicates("duplicate_key").drop(columns="duplicate_key")
    conflicts = combined.groupby("normalized_description")["category"].nunique()
    conflict_count = int((conflicts > 1).sum())
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(output, index=False)
    report = {
        "statement_candidate_source": {
            "path": str(EXTRACTED_CSV),
            "rows": int(len(review)),
            "manually_verified_rows": int((review["label_source"] == "manual_verified").sum()),
            "weakly_labelled_rows": int((review["label_source"] == "weak_supervision").sum()),
            "requires_manual_review": int((review["review_status"] == "manual_review_required").sum()),
        },
        "sources": [local_stats, {"source": "synthetic:data/synthetic_transactions.csv", "original_rows": len(synthetic), "usable_rows": len(synthetic), "rejected_rows": 0, "duplicate_rows": 0, "category_distribution": synthetic["category"].value_counts().to_dict()}, hf_stats, {"source": str(ENTITY_CANDIDATES), "rows_used_as_weak_supervision": int(len(entity)) if ENTITY_CANDIDATES.exists() else 0}],
        "combined_rows": len(combined),
        "combined_category_distribution": combined["category"].value_counts().to_dict(),
        "conflicting_normalized_descriptions": conflict_count,
        "output": output,
    }
    Path(report_path).write_text(json.dumps(report, indent=2, default=str))
    print(json.dumps(report, indent=2, default=str))
    return combined


if __name__ == "__main__":
    build()
