
from pathlib import Path
from datetime import date, timedelta
import numpy as np
import pandas as pd

SEED = 42
N_CUSTOMERS = 200
END_DATE = date(2026, 11, 22)

BASE = Path(__file__).resolve().parent
RAW = BASE / "raw"
RAW.mkdir(parents=True, exist_ok=True)
SOURCE = RAW / "expenses_starter.csv"

CATEGORIES = [
    "Food", "Transport", "Education", "Bills",
    "Shopping", "Groceries", "Health", "Entertainment"
]

AMOUNT_RANGES = {
    "Food": (100, 1400),
    "Transport": (70, 1800),
    "Education": (150, 7000),
    "Bills": (400, 8500),
    "Shopping": (250, 9500),
    "Groceries": (250, 5000),
    "Health": (150, 5500),
    "Entertainment": (200, 4000),
}

BEHAVIORS = {
    "food_focused": {"Food": 5, "Groceries": 2},
    "travel_focused": {"Transport": 6, "Food": 2},
    "study_focused": {"Education": 6, "Food": 2},
    "shopping_focused": {"Shopping": 6, "Entertainment": 2},
    "home_focused": {"Groceries": 5, "Bills": 4},
    "social_focused": {"Entertainment": 5, "Food": 4},
    "balanced": {},
    "health_focused": {"Health": 5, "Groceries": 3},
}

CONTEXTS = [
    "before my afternoon class",
    "while heading back to the hostel",
    "during the weekend",
    "after finishing my assignments",
    "on my way to campus",
    "for this week",
    "with my friends",
    "after a long day at university",
    "near the university",
    "earlier today",
]

PREFIXES = [
    "{base}.",
    "{base} {context}.",
    "Expense note: {base} {context}.",
    "My spending record says: {base} {context}.",
]


def load_examples():
    if not SOURCE.exists():
        raise FileNotFoundError(
            f"Missing starter dataset: {SOURCE}\n"
            "Create expenses_starter.csv first."
        )

    df = pd.read_csv(SOURCE)

    if not {"description", "category"}.issubset(df.columns):
        raise ValueError(
            "Starter CSV needs description and category columns."
        )

    df = df.dropna(
        subset=["description", "category"]
    ).copy()

    df["description"] = (
        df["description"]
        .astype(str)
        .str.strip()
        .str.rstrip(".! ")
    )

    df["category"] = (
        df["category"]
        .astype(str)
        .str.strip()
    )

    df = df[
        (df["description"] != "")
        & df["category"].isin(CATEGORIES)
    ]

    missing = set(CATEGORIES) - set(df["category"])

    if missing:
        raise ValueError(
            f"Starter CSV lacks these categories: {sorted(missing)}"
        )

    return {
        category: df.loc[
            df["category"] == category, "description"
        ].tolist()
        for category in CATEGORIES
    }


def sentence(base, rng):
    context = str(rng.choice(CONTEXTS))
    template = str(rng.choice(PREFIXES))

    result = template.format(
        base=base,
        context=context
    )

    return result[0].upper() + result[1:]


def main():
    rng = np.random.default_rng(SEED)

    examples = load_examples()
    rows = []
    customers = []
    behavior_names = list(BEHAVIORS)

    for index in range(1, N_CUSTOMERS + 1):
        user_id = f"U{index:04d}"

        behavior = behavior_names[
            (index - 1) % len(behavior_names)
        ]

        history_days = int(
            rng.integers(7, 366)
        )

        start_date = END_DATE - timedelta(
            days=history_days - 1
        )

        transaction_count = max(
            5,
            int(rng.poisson(history_days * 1.1))
        )

        weights = np.array(
            [
                BEHAVIORS[behavior].get(cat, 1.0)
                for cat in CATEGORIES
            ],
            dtype=float
        )

        weights *= rng.lognormal(
            mean=0.0,
            sigma=0.25,
            size=len(CATEGORIES)
        )

        probabilities = weights / weights.sum()

        amount_multiplier = float(
            rng.lognormal(
                mean=0,
                sigma=0.35
            )
        )

        customers.append({
            "user_id": user_id,
            "synthetic_behavior": behavior,
            "history_days": history_days,
            "start_date": start_date.isoformat(),
            "end_date": END_DATE.isoformat(),
            "transaction_count": transaction_count,
        })

        offsets = rng.integers(
            0,
            history_days,
            size=transaction_count
        )

        selected_categories = rng.choice(
            CATEGORIES,
            size=transaction_count,
            p=probabilities
        )

        for offset, category in zip(
            offsets,
            selected_categories
        ):
            category = str(category)
            base = str(
                rng.choice(examples[category])
            )

            low, high = AMOUNT_RANGES[category]

            amount = float(
                np.exp(
                    rng.uniform(
                        np.log(low),
                        np.log(high)
                    )
                )
            ) * amount_multiplier

            amount = int(
                max(20, round(amount / 10) * 10)
            )

            transaction_date = (
                start_date
                + timedelta(days=int(offset))
            )

            rows.append({
                "user_id": user_id,
                "date": transaction_date.isoformat(),
                "description": sentence(base, rng),
                "amount_pkr": amount,
                "category": category,
            })

    transactions = pd.DataFrame(rows)

    transactions = transactions.sort_values(
        ["user_id", "date"]
    ).reset_index(drop=True)

    transactions.insert(
        0,
        "transaction_id",
        [
            f"T{i:07d}"
            for i in range(
                1,
                len(transactions) + 1
            )
        ]
    )

    customer_df = pd.DataFrame(customers)

    transactions.to_csv(
        RAW / "expenses_full.csv",
        index=False,
        encoding="utf-8"
    )

    customer_df.to_csv(
        RAW / "customers.csv",
        index=False,
        encoding="utf-8"
    )

    assert (
        transactions["user_id"].nunique()
        == N_CUSTOMERS
    )

    assert transactions[
        [
            "user_id",
            "date",
            "description",
            "amount_pkr",
            "category"
        ]
    ].notna().all().all()

    assert (
        set(transactions["category"])
        == set(CATEGORIES)
    )

    assert (
        transactions["amount_pkr"] > 0
    ).all()

    assert transactions["date"].between(
        str(END_DATE - timedelta(days=364)),
        str(END_DATE)
    ).all()

    assert customer_df[
        "history_days"
    ].between(7, 365).all()

    print(
        "Synthetic dataset generated successfully!"
    )

    print(f"Customers: {len(customer_df):,}")
    print(f"Transactions: {len(transactions):,}")
    print(
        f"Categories: {transactions['category'].nunique()}"
    )

    print(
        f"Date range: "
        f"{transactions['date'].min()} "
        f"to {transactions['date'].max()}"
    )

    print("Files:")
    print(RAW / "expenses_full.csv")
    print(RAW / "customers.csv")

    print("\nCategory distribution:")
    print(
        transactions["category"]
        .value_counts()
        .to_string()
    )

    print(
        "\nNOTE: Synthetic descriptions reuse starter phrases."
    )
    print(
        "Avoid random row splits when evaluating classification."
    )


if __name__ == "__main__":
    main()
