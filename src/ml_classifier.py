from pathlib import Path
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import FeatureUnion
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from .text_normalizer import normalize_description


def _metrics(expected, predicted):
    report = classification_report(expected, predicted, output_dict=True, zero_division=0)
    return {
        "accuracy": report["accuracy"],
        "macro_f1": report["macro avg"]["f1-score"],
        "weighted_f1": report["weighted avg"]["f1-score"],
        "classification_report": report,
        "confusion_matrix": confusion_matrix(expected, predicted).tolist(),
    }


def train_classifier(frame, model_dir="models", random_state=42):
    model_dir = Path(model_dir)
    model_dir.mkdir(exist_ok=True)
    descriptions = frame["description"].fillna("").map(normalize_description)
    x_train, x_holdout, y_train, y_holdout = train_test_split(
        descriptions, frame["category"], test_size=.2, random_state=random_state, stratify=frame["category"]
    )
    x_valid, x_test, y_valid, y_test = train_test_split(
        x_holdout, y_holdout, test_size=.5, random_state=random_state, stratify=y_holdout
    )
    vectorizer = FeatureUnion([
        ("word", TfidfVectorizer(ngram_range=(1, 2), lowercase=False, min_df=1, sublinear_tf=True)),
        ("char", TfidfVectorizer(analyzer="char", ngram_range=(3, 5), lowercase=False, min_df=1, sublinear_tf=True)),
    ])
    model = LogisticRegression(max_iter=1500, class_weight="balanced")
    model.fit(vectorizer.fit_transform(x_train), y_train)
    metrics = {
        "train_rows": len(x_train),
        "validation_rows": len(x_valid),
        "test_rows": len(x_test),
        "validation": _metrics(y_valid, model.predict(vectorizer.transform(x_valid))),
        "test": _metrics(y_test, model.predict(vectorizer.transform(x_test))),
    }
    joblib.dump(model, model_dir / "classifier.pkl")
    joblib.dump(vectorizer, model_dir / "vectorizer.pkl")
    joblib.dump({"model": model, "vectorizer": vectorizer}, model_dir / "transaction_classifier.joblib")
    return model, vectorizer, metrics


def load_classifier(model_dir="models"):
    path = Path(model_dir)
    bundle = path / "transaction_classifier.joblib"
    if bundle.exists():
        trained = joblib.load(bundle)
        return trained["model"], trained["vectorizer"]
    return joblib.load(path / "classifier.pkl"), joblib.load(path / "vectorizer.pkl")
