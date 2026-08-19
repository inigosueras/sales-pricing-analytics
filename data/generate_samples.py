"""
Generates 3 synthetic sample datasets (retail, pharma, manufacturing) that
all conform to the required schema, to demonstrate the tool works across
industries without modification. Run once: `python data/generate_samples.py`
"""

import numpy as np
import pandas as pd

RNG = np.random.default_rng(42)


def generate_dataset(
    filename: str,
    products: dict,          # {product_name: (category, base_price, base_cost)}
    countries: list[str],
    segments: list[str],
    n_rows: int,
    start_date: str,
    end_date: str,
):
    dates = pd.date_range(start_date, end_date, freq="D")
    product_names = list(products.keys())

    rows = []
    for _ in range(n_rows):
        product = RNG.choice(product_names)
        category, base_price, base_cost = products[product]
        date = RNG.choice(dates)
        country = RNG.choice(countries)
        segment = RNG.choice(segments)

        quantity = max(1, int(RNG.gamma(shape=3, scale=8)))
        # Small price variance to simulate discounts/regional pricing
        price = base_price * RNG.uniform(0.85, 1.1)
        cost = base_cost * RNG.uniform(0.95, 1.05)

        revenue = round(price * quantity, 2)
        cost_total = round(cost * quantity, 2)

        rows.append({
            "Date": pd.Timestamp(date).strftime("%Y-%m-%d"),
            "Product": product,
            "Category": category,
            "Country": country,
            "Revenue": revenue,
            "Quantity": quantity,
            "Cost": cost_total,
            "Customer_Segment": segment,
        })

    df = pd.DataFrame(rows).sort_values("Date").reset_index(drop=True)
    out_path = f"data/samples/{filename}"
    df.to_csv(out_path, index=False)
    print(f"Wrote {len(df)} rows -> {out_path}")


if __name__ == "__main__":
    # --- RETAIL ---
    retail_products = {
        "Running Shoes Pro":     ("Footwear", 89, 42),
        "Trail Sneakers":        ("Footwear", 74, 35),
        "Cotton T-Shirt":        ("Apparel", 22, 8),
        "Denim Jacket":          ("Apparel", 95, 48),
        "Wireless Earbuds":      ("Electronics", 129, 60),
        "Smartwatch Lite":       ("Electronics", 159, 75),
        "Yoga Mat":              ("Fitness", 35, 14),
        "Adjustable Dumbbells":  ("Fitness", 210, 110),
    }
    generate_dataset(
        "retail_sales.csv", retail_products,
        countries=["Spain", "France", "Germany", "Italy", "Portugal", "Netherlands"],
        segments=["Online", "In-Store", "Wholesale"],
        n_rows=6000, start_date="2023-01-01", end_date="2024-12-31",
    )

    # --- PHARMA ---
    pharma_products = {
        "Ibuprofen 400mg (30ct)":     ("Pain Relief", 6.5, 2.1),
        "Amoxicillin 500mg (20ct)":   ("Antibiotics", 14.2, 5.8),
        "Loratadine 10mg (14ct)":     ("Allergy", 9.8, 3.4),
        "Omeprazole 20mg (28ct)":     ("Gastro", 12.5, 4.9),
        "Insulin Glargine Pen":       ("Diabetes Care", 68.0, 31.0),
        "Atorvastatin 20mg (30ct)":   ("Cardiovascular", 18.9, 7.2),
        "Multivitamin Complex":       ("Supplements", 15.0, 5.5),
        "Salbutamol Inhaler":         ("Respiratory", 22.4, 9.1),
    }
    generate_dataset(
        "pharma_sales.csv", pharma_products,
        countries=["USA", "Germany", "UK", "Brazil", "India", "Japan"],
        segments=["Hospital", "Retail Pharmacy", "Government Tender"],
        n_rows=7000, start_date="2023-01-01", end_date="2024-12-31",
    )

    # --- MANUFACTURING ---
    manufacturing_products = {
        "Steel Bearing 6205":        ("Components", 4.2, 1.9),
        "Hydraulic Cylinder HC-40":  ("Hydraulics", 320.0, 175.0),
        "Industrial Motor 5HP":      ("Motors", 610.0, 340.0),
        "Conveyor Belt Roller":      ("Components", 28.0, 12.5),
        "PLC Controller Unit":       ("Automation", 890.0, 470.0),
        "Pneumatic Valve V-200":     ("Hydraulics", 145.0, 68.0),
        "Safety Sensor Array":       ("Automation", 210.0, 95.0),
        "Gearbox Assembly GB-12":    ("Motors", 1250.0, 690.0),
    }
    generate_dataset(
        "manufacturing_sales.csv", manufacturing_products,
        countries=["USA", "China", "Germany", "Mexico", "South Korea", "Poland"],
        segments=["OEM", "Distributor", "Direct Industrial"],
        n_rows=5000, start_date="2023-01-01", end_date="2024-12-31",
    )
