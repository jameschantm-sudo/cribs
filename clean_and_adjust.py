"""
Stage 3: turn the raw scraped transactions into a modeling-ready dataset.

Three things happen here:
1. Every sold price gets converted into "today's market terms" using the
   RVD index from Stage 1, so a 2019 sale and a 2025 sale become comparable.
2. Each transaction gets an age (how old the building was when it sold),
   using each phase's real construction-completion year.
3. A loose sanity check runs, dropping anything implausible (a parsing
   slip, not a real transaction) rather than trusting every row blindly.
"""

import pandas as pd

from index_adjust import load_index, adjust_price

RAW_CSV = "data/city_one_shatin_transactions.csv"
OUTPUT_CSV = "data/city_one_shatin_modeling_ready.csv"

# Real construction-completion years per phase, from Wikipedia
# (https://en.wikipedia.org/wiki/City_One) - cross-checked against 28hse's
# own block-to-phase grouping, which lines up with these exactly.
PHASE_COMPLETION_YEAR = {
    1: 1981,
    2: 1982,
    3: 1983,
    4: 1985,
    5: 1985,
    6: 1986,
    7: 1988,
}


def clean_and_adjust():
    df = pd.read_csv(RAW_CSV)
    index_series = load_index()
    before = len(df)

    df = df.drop_duplicates(subset=["phase", "block", "unit", "floor", "sale_date"])

    # A loose plausibility net, not a tight domain filter - real City One
    # Shatin data ranges ~284-853 sqft, $896K-$13M, floors 1-36. These
    # bounds are deliberately much wider, just to catch a parsing slip
    # (e.g. a stray digit), not to trim real variation out of the data.
    plausible = (
        df["saleable_area_sqft"].between(150, 2000)
        & df["price_hkd"].between(500_000, 50_000_000)
        & df["floor"].between(1, 70)
    )
    df = df[plausible]
    dropped = before - len(df)

    df["sale_year"] = pd.to_datetime(df["sale_date"]).dt.year
    df["age_at_sale"] = df["sale_year"] - df["phase"].map(PHASE_COMPLETION_YEAR)

    # A handful of sales are more recent than the RVD index's latest
    # published month - there's nothing to adjust those against yet, so
    # they're dropped rather than adjusted using a guessed/latest-available
    # index value.
    latest_indexed_month = index_series.index.max()
    too_recent = pd.to_datetime(df["sale_date"]).dt.to_period("M").dt.to_timestamp() > latest_indexed_month
    too_recent_count = int(too_recent.sum())
    df = df[~too_recent]

    df["adjusted_price_hkd"] = df.apply(
        lambda row: round(adjust_price(row["price_hkd"], row["sale_date"], index_series)),
        axis=1,
    )

    df = df.reset_index(drop=True)
    df["transaction_id"] = range(1, len(df) + 1)

    df = df[["transaction_id", "block", "floor", "saleable_area_sqft",
             "age_at_sale", "sale_date", "price_hkd", "adjusted_price_hkd"]]
    df.to_csv(OUTPUT_CSV, index=False)

    print(f"Started with {before} rows, dropped {dropped} as implausible, "
          f"dropped {too_recent_count} as more recent than the index can adjust, "
          f"{len(df)} rows written to {OUTPUT_CSV}")
    return df


if __name__ == "__main__":
    clean_and_adjust()
