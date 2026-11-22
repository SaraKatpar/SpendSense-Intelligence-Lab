
from pathlib import Path
import numpy as np
import pandas as pd

SEED = 42

BASE = Path(__file__).resolve().parent
RAW = BASE / "raw"
PROCESSED = BASE / "processed"
PROCESSED.mkdir(parents=True, exist_ok=True)

expenses = pd.read_csv(RAW / "expenses_full.csv")
starter = pd.read_csv(RAW / "expenses_starter.csv")

required = {
    "transaction_id", "user_id", "date",
    "description", "amount_pkr", "category"
}

if not required.issubset(expenses.columns):
    raise ValueError("Missing columns in expenses_full.csv")

starter["description"] = (
    starter["description"]
    .astype(str)
    .str.strip()
    .str.rstrip(".! ")
)

starter["category"] = starter["category"].str.strip()

if starter.duplicated(
    ["description", "category"]
).any():
    raise ValueError("Duplicate starter phrases found")

rng = np.random.default_rng(SEED)

phrase_splits = {}

# Split original phrases separately within each category
for category, group in starter.groupby("category"):
    phrases = group["description"].tolist()
    rng.shuffle(phrases)

    if len(phrases) < 5:
        raise ValueError(
            f"{category} needs at least 5 starter phrases"
        )

    # Our starter dataset has 5 phrases per category
    train_phrases = phrases[:3]
    val_phrases = phrases[3:4]
    test_phrases = phrases[4:]

    for phrase in train_phrases:
        phrase_splits[(category, phrase)] = "train"

    for phrase in val_phrases:
        phrase_splits[(category, phrase)] = "validation"

    for phrase in test_phrases:
        phrase_splits[(category, phrase)] = "test"


def identify_source(row):
    category = row["category"]
    description = row["description"].lower()

    candidates = starter.loc[
        starter["category"] == category,
        "description"
    ].tolist()

    matches = [
        phrase
        for phrase in candidates
        if phrase.lower() in description
    ]

    if len(matches) != 1:
        raise ValueError(
            "Could not uniquely identify starter phrase: "
            + row["description"]
        )

    return matches[0]


expenses["source_phrase"] = expenses.apply(
    identify_source,
    axis=1
)

expenses["split"] = expenses.apply(
    lambda row: phrase_splits[
        (row["category"], row["source_phrase"])
    ],
    axis=1
)

# Ensure no original phrase appears in multiple splits
overlap = expenses.groupby(
    ["category", "source_phrase"]
)["split"].nunique()

assert (overlap == 1).all()

# Ensure no exact description appears in multiple splits
description_overlap = expenses.groupby(
    "description"
)["split"].nunique()

assert (description_overlap == 1).all()

for split in ["train", "validation", "test"]:
    subset = expenses[
        expenses["split"] == split
    ].copy()

    subset.to_csv(
        PROCESSED / f"{split}.csv",
        index=False
    )

    print(
        f"{split.upper()}: "
        f"{len(subset):,} transactions, "
        f"{subset['source_phrase'].nunique()} "
        "original phrases"
    )

print("\nCategory counts per split:")
print(
    pd.crosstab(
        expenses["category"],
        expenses["split"]
    )
)

print("\nNo starter phrase crosses split boundaries.")
print("Classification datasets prepared successfully!")
