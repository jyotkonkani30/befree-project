import pandas as pd
from functools import lru_cache
from .rule_classifier import classify_rule
from .ml_classifier import load_classifier
from .text_normalizer import normalize_description
from .entity_extractor import extract_entity


@lru_cache(maxsize=4)
def _cached_classifier(model_dir):
    try:
        return load_classifier(model_dir)
    except FileNotFoundError:
        return None, None


def classify_transactions(frame: pd.DataFrame, model_dir="models", threshold=.45) -> pd.DataFrame:
    result = frame.copy()
    if result.empty:
        return result.assign(
            category=pd.Series(dtype="object"),
            classification_method=pd.Series(dtype="object"),
            confidence_score=pd.Series(dtype="float64"),
            matched_rule=pd.Series(dtype="object"),
            needs_review=pd.Series(dtype="bool"),
        )
    model, vectorizer = _cached_classifier(str(model_dir))
    categories, methods, confidence, matched_rules, needs_review = [], [], [], [], []
    entities = []
    for description in result["description"].fillna(""):
        entity = extract_entity(description)
        entities.append(entity)
        rule, score = classify_rule(description)
        if rule:
            categories.append(rule)
            methods.append("rule")
            confidence.append(score)
            matched_rules.append(rule)
            needs_review.append(False)
            continue
        if entity["counterparty_type"] == "GOVERNMENT / TAX":
            categories.append("Other / Unclassified")
            methods.append("entity-aware-unclassified")
            confidence.append(entity["counterparty_confidence"])
            matched_rules.append("government_tax_outside_taxonomy")
            needs_review.append(True)
            continue
        if entity["payment_rail"] and entity["counterparty_type"] in {"PERSON", "BUSINESS"}:
            categories.append("Money Transfer")
            methods.append("entity-aware-transfer")
            confidence.append(0.9 if entity["counterparty_type"] == "PERSON" else 0.82)
            matched_rules.append("payment_rail_plus_counterparty")
            needs_review.append(True)
            continue
        if model is not None:
            probabilities = model.predict_proba(vectorizer.transform([normalize_description(description)]))[0]
            index = probabilities.argmax()
            score = float(probabilities[index])
            category = model.classes_[index] if score >= threshold else "Other / Unclassified"
            categories.append(category)
            methods.append("ml" if score >= threshold else "ml-low-confidence")
            confidence.append(score)
            matched_rules.append("")
            needs_review.append(score < threshold)
        else:
            categories.append("Other / Unclassified")
            methods.append("unavailable")
            confidence.append(0.0)
            matched_rules.append("")
            needs_review.append(True)
    entity_frame = pd.DataFrame(entities, index=result.index)
    return result.assign(
        category=categories,
        classification_method=methods,
        confidence_score=confidence,
        matched_rule=matched_rules,
        needs_review=needs_review,
        counterparty_name=entity_frame["counterparty_name"],
        counterparty_type=entity_frame["counterparty_type"],
        counterparty_industry=entity_frame["counterparty_industry"],
        counterparty_confidence=entity_frame["counterparty_confidence"],
        payment_rail=entity_frame["payment_rail"],
    )
