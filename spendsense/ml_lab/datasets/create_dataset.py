
from pathlib import Path
import pandas as pd

# Folder containing this script
BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "raw"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

data = [
    ("Bought biryani at university cafeteria", "Food"),
    ("Ordered pizza for dinner", "Food"),
    ("Had breakfast at hostel canteen", "Food"),
    ("Purchased lunch from campus cafe", "Food"),
    ("Bought a burger and fries", "Food"),

    ("Paid bus fare to university", "Transport"),
    ("Booked a Careem ride", "Transport"),
    ("Paid for rickshaw ride", "Transport"),
    ("Bought petrol for motorcycle", "Transport"),
    ("Paid train ticket fare", "Transport"),

    ("Purchased a programming textbook", "Education"),
    ("Paid semester tuition fee", "Education"),
    ("Bought notebooks for class", "Education"),
    ("Paid online course fee", "Education"),
    ("Purchased exam preparation materials", "Education"),

    ("Paid monthly electricity bill", "Bills"),
    ("Recharged mobile internet package", "Bills"),
    ("Paid hostel room rent", "Bills"),
    ("Paid water utility bill", "Bills"),
    ("Paid monthly WiFi subscription", "Bills"),

    ("Bought new headphones", "Shopping"),
    ("Purchased a hoodie online", "Shopping"),
    ("Bought a pair of shoes", "Shopping"),
    ("Purchased a phone cover", "Shopping"),
    ("Bought a new backpack", "Shopping"),

    ("Purchased vegetables from market", "Groceries"),
    ("Bought milk and eggs", "Groceries"),
    ("Purchased rice and cooking oil", "Groceries"),
    ("Bought fruits for the week", "Groceries"),
    ("Purchased household groceries", "Groceries"),

    ("Bought medicine from pharmacy", "Health"),
    ("Paid doctor consultation fee", "Health"),
    ("Purchased vitamins", "Health"),
    ("Paid for medical tests", "Health"),
    ("Bought first aid supplies", "Health"),

    ("Purchased cinema tickets", "Entertainment"),
    ("Paid for a gaming subscription", "Entertainment"),
    ("Bought tickets for a concert", "Entertainment"),
    ("Paid for bowling with friends", "Entertainment"),
    ("Purchased a movie streaming subscription", "Entertainment"),
]

df = pd.DataFrame(data, columns=["description", "category"])

output_path = OUTPUT_DIR / "expenses_starter.csv"
df.to_csv(output_path, index=False, encoding="utf-8")

print("Dataset created successfully!")
print(f"Total transactions: {len(df)}")
print(f"Categories: {df['category'].nunique()}")
print(f"Saved to: {output_path}")
print("\nCategory distribution:")
print(df["category"].value_counts().to_string())
