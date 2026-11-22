
from pathlib import Path
import json
import numpy as np
import pandas as pd
import joblib

from sentence_transformers import SentenceTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)

SEED = 42
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "datasets" / "processed"
MODEL_DIR = ROOT / "models" / "expense_classifier"
EVAL_DIR = ROOT / "evaluation"

MODEL_DIR.mkdir(parents=True, exist_ok=True)
EVAL_DIR.mkdir(parents=True, exist_ok=True)

print("Loading SpendSense datasets...", flush=True)

train = pd.read_csv(DATA_DIR / "train.csv")
validation = pd.read_csv(DATA_DIR / "validation.csv")
test = pd.read_csv(DATA_DIR / "test.csv")

for name, df in [
    ("train", train),
    ("validation", validation),
    ("test", test),
]:
    if df[["description", "category"]].isna().any().any():
        raise ValueError(f"Missing text or labels in {name}")

    print(f"{name}: {len(df):,} records", flush=True)

# Use only expense descriptions to classify transactions.
# Do not include the actual category, user ID or amount.
all_data = pd.concat(
    [train, validation, test],
    ignore_index=True
)

# There are only 1,240 unique descriptions.
# Encode each distinct sentence once to save processing time.
unique_texts = all_data["description"].unique().tolist()

print(
    f"\nLoading sentence encoder: {MODEL_NAME}",
    flush=True
)

encoder = SentenceTransformer(MODEL_NAME)

print(
    f"Encoding {len(unique_texts):,} unique descriptions...",
    flush=True
)

unique_vectors = encoder.encode(
    unique_texts,
    batch_size=32,
    show_progress_bar=True,
    convert_to_numpy=True,
    normalize_embeddings=True,
)

vector_lookup = {
    text: vector
    for text, vector in zip(unique_texts, unique_vectors)
}

def make_features(df):
    return np.stack([
        vector_lookup[text]
        for text in df["description"]
    ])

X_train = make_features(train)
X_val = make_features(validation)
X_test = make_features(test)

label_encoder = LabelEncoder()
y_train = label_encoder.fit_transform(train["category"])
y_val = label_encoder.transform(validation["category"])
y_test = label_encoder.transform(test["category"])

print("\nEmbedding shape:", X_train.shape)
print("Categories:", label_encoder.classes_.tolist())

# Tune regularization using validation data only.
c_values = [0.01, 0.1, 1.0, 10.0]

best_model = None
best_c = None
best_score = -1.0

results = []

print("\nTraining Logistic Regression...", flush=True)

for c in c_values:
    model = LogisticRegression(
        C=c,
        max_iter=1000,
        solver="lbfgs",
        random_state=SEED,
    )

    model.fit(X_train, y_train)

    predictions = model.predict(X_val)

    score = f1_score(
        y_val,
        predictions,
        average="macro",
        zero_division=0
    )

    results.append({
        "C": c,
        "validation_macro_f1": float(score)
    })

    print(
        f"C={c}: Validation Macro F1={score:.4f}",
        flush=True
    )

    if score > best_score:
        best_score = score
        best_model = model
        best_c = c

print(f"\nBest C: {best_c}")

# Evaluate the selected model on the held-out test data.
# We do not tune parameters using the test results.
test_predictions = best_model.predict(X_test)

accuracy = accuracy_score(
    y_test,
    test_predictions
)

macro_f1 = f1_score(
    y_test,
    test_predictions,
    average="macro",
    zero_division=0
)

report = classification_report(
    y_test,
    test_predictions,
    target_names=label_encoder.classes_,
    output_dict=True,
    zero_division=0
)

matrix = confusion_matrix(
    y_test,
    test_predictions,
    labels=np.arange(len(label_encoder.classes_))
)

print("\n===== TEST RESULTS =====")
print(f"Accuracy: {accuracy:.4f}")
print(f"Macro F1: {macro_f1:.4f}")

print(
    classification_report(
        y_test,
        test_predictions,
        target_names=label_encoder.classes_,
        zero_division=0
    )
)

# Save classifier and label mapping.
joblib.dump(
    best_model,
    MODEL_DIR / "logistic_regression.joblib"
)

joblib.dump(
    label_encoder,
    MODEL_DIR / "label_encoder.joblib"
)

# Save the exact encoder weights used for inference.
encoder.save(str(MODEL_DIR / "sentence_encoder"))

metadata = {
    "encoder": MODEL_NAME,
    "classifier": "LogisticRegression",
    "best_C": best_c,
    "embedding_dimensions": int(X_train.shape[1]),
    "classes": label_encoder.classes_.tolist(),
    "validation_results": results,
    "test_accuracy": float(accuracy),
    "test_macro_f1": float(macro_f1),
    "dataset_type": "synthetic",
    "evaluation_note": (
        "Held-out starter phrases; not independent real-world data"
    )
}

with open(
    MODEL_DIR / "metadata.json",
    "w",
    encoding="utf-8"
) as f:
    json.dump(metadata, f, indent=2)

with open(
    EVAL_DIR / "classifier_report.json",
    "w",
    encoding="utf-8"
) as f:
    json.dump(report, f, indent=2)

pd.DataFrame(
    matrix,
    index=label_encoder.classes_,
    columns=label_encoder.classes_
).to_csv(
    EVAL_DIR / "classifier_confusion_matrix.csv"
)

print("\nModel saved successfully!")
print("Model folder:", MODEL_DIR)
print("Evaluation folder:", EVAL_DIR)
