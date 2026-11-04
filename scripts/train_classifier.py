import json
import sys
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.ml_classifier import train_classifier
from scripts.build_training_dataset import build


if __name__ == "__main__":
    frame = build()
    frame = frame[["description", "category"]]
    _, _, metrics = train_classifier(frame)
    Path("models/metrics.json").write_text(json.dumps(metrics, indent=2, default=float))
    print(f"test_accuracy={metrics['test']['accuracy']:.3f} test_macro_f1={metrics['test']['macro_f1']:.3f}")
