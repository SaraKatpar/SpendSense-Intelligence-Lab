
from pathlib import Path
import joblib
import numpy as np
from sentence_transformers import SentenceTransformer

# ==========================================
# SPENDSENSE - EXPENSE CLASSIFIER INFERENCE
# ==========================================

ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "models" / "expense_classifier"

print("Loading trained SpendSense model...")

# Load our saved Sentence Transformer
encoder = SentenceTransformer(
    str(MODEL_DIR / "sentence_encoder"),
    device="cpu",
    local_files_only=True,
)

# Load our trained Logistic Regression model
classifier = joblib.load(
    MODEL_DIR / "logistic_regression.joblib"
)

# Load the category label encoder
label_encoder = joblib.load(
    MODEL_DIR / "label_encoder.joblib"
)

print("Model loaded successfully!\n")


# ==========================================
# PREDICTION FUNCTION
# ==========================================

def predict_expense(description):

    description = description.strip()

    if not description:
        raise ValueError(
            "Expense description cannot be empty."
        )

    # Step 1: Convert text into a 384-dimensional vector
    embedding = encoder.encode(
        [description],
        convert_to_numpy=True,
        normalize_embeddings=True
    )

    # Step 2: Predict probabilities
    probabilities = classifier.predict_proba(
        embedding
    )[0]

    # Step 3: Find the highest probability
    best_index = int(np.argmax(probabilities))

    # Step 4: Convert encoded label into category name
    predicted_label = label_encoder.inverse_transform(
        [classifier.classes_[best_index]]
    )[0]

    # Step 5: Get probabilities for all categories
    results = []

    for class_index, probability in zip(
        classifier.classes_,
        probabilities
    ):

        category = label_encoder.inverse_transform(
            [class_index]
        )[0]

        results.append(
            (category, float(probability))
        )

    # Step 6: Sort categories by probability
    results.sort(
        key=lambda item: item[1],
        reverse=True
    )

    return predicted_label, results, embedding[0]


# ==========================================
# INTERACTIVE TERMINAL
# ==========================================

if __name__ == "__main__":

    print("================================")
    print("   SPENDSENSE NLP CLASSIFIER")
    print("================================")

    print("\nType an expense description.")
    print("Type 'exit' to quit.")

    while True:

        try:
            description = input(
                "\nEnter an expense: "
            ).strip()

        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if description.lower() == "exit":
            print("\nGoodbye!")
            break

        try:

            # Run our trained ML model
            category, probabilities, vector = predict_expense(
                description
            )

            print("\n================================")
            print("       PREDICTION RESULT")
            print("================================")

            print("\nExpense:", description)

            print("\nPredicted Category:", category)

            print("\nCategory Probabilities:")

            for label, probability in probabilities:

                print(
                    f"  {label:<15} "
                    f"{probability * 100:6.2f}%"
                )

            print("\nEmbedding Information:")

            print(
                "Dimensions:",
                len(vector)
            )

            print(
                "First 10 values:",
                np.round(vector[:10], 4)
            )

            print("\n================================")

        except ValueError as error:
            print("Error:", error)
