
from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parent
df = pd.read_csv(BASE / "raw" / "expenses_full.csv")
customers = pd.read_csv(BASE / "raw" / "customers.csv")

print("\n===== SPENDSENSE DATASET REPORT =====")

print("\nDataset shape:", df.shape)
print("Unique customers:", df["user_id"].nunique())
print("Unique descriptions:", df["description"].nunique())
print("Categories:", df["category"].nunique())

print("\nMissing values:")
print(df.isnull().sum())

print("\nDuplicate transaction IDs:")
print(df["transaction_id"].duplicated().sum())

print("\nDate range:")
print(df["date"].min(), "to", df["date"].max())

print("\nAmount statistics (PKR):")
print(df["amount_pkr"].describe().round(2))

print("\nCategory distribution:")
print(df["category"].value_counts())

print("\nCustomer behavior distribution:")
print(customers["synthetic_behavior"].value_counts())

print("\nSample transactions:")
print(
    df.sample(10, random_state=42)
    .to_string(index=False)
)

print("\nDataset inspection completed!")
