"""
Stage 3 (Phase 2: multi-estate) - clean the combined raw transactions and
apply each estate's own index adjustment.

Same three things as the single-estate version, just per-estate now:
1. Every price is converted into "today's market terms" - using each
   estate's own correct RVD column (region matters: Hong Kong Island,
   Kowloon, and New Territories moved differently over this period).
2. Each transaction gets age_at_sale, from its own estate's real
   phase-completion years.
3. A loose sanity check drops anything implausible.
"""

import pandas as pd

from estate_info import ESTATES
from index_adjust import load_index, adjust_price

RAW_CSV = "data/all_estates_transactions.csv"
OUTPUT_CSV = "data/all_estates_modeling_ready.csv"


def clean_and_adjust():
    df = pd.read_csv(RAW_CSV)
    before = len(df)

    df = df.drop_duplicates(subset=["estate", "phase", "block", "unit", "floor", "sale_date"])

    plausible = (
        df["saleable_area_sqft"].between(150, 2000)
        & df["price_hkd"].between(500_000, 50_000_000)
        & df["floor"].between(1, 70)
    )
    df = df[plausible]
    dropped = before - len(df)

    df["sale_year"] = pd.to_datetime(df["sale_date"]).dt.year

    adjusted_rows = []
    too_recent_count = 0
    for estate_key, group in df.groupby("estate"):
        config = ESTATES[estate_key]
        index_series = load_index(column=config["index_column"])
        latest_indexed_month = index_series.index.max()

        group = group.copy()
        group["age_at_sale"] = group["sale_year"] - group["phase"].map(config["phase_completion_year"])

        too_recent = pd.to_datetime(group["sale_date"]).dt.to_period("M").dt.to_timestamp() > latest_indexed_month
        too_recent_count += int(too_recent.sum())
        group = group[~too_recent]

        group["adjusted_price_hkd"] = group.apply(
            lambda row: round(adjust_price(row["price_hkd"], row["sale_date"], index_series)),
            axis=1,
        )
        adjusted_rows.append(group)

    result = pd.concat(adjusted_rows, ignore_index=True)
    result["transaction_id"] = range(1, len(result) + 1)

    result = result[["transaction_id", "estate", "block", "floor", "saleable_area_sqft",
                      "age_at_sale", "sale_date", "price_hkd", "adjusted_price_hkd"]]
    result.to_csv(OUTPUT_CSV, index=False)

    print(f"Started with {before} rows, dropped {dropped} as implausible, "
          f"dropped {too_recent_count} as more recent than the index can adjust, "
          f"{len(result)} rows written to {OUTPUT_CSV}")
    print(result.estate.value_counts())
    return result


if __name__ == "__main__":
    clean_and_adjust()
