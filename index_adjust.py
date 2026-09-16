"""
Stage 1: look up the RVD Class B (New Territories) price index for a given
month, and use it to convert an old sold price into "today's money."

Why: a flat that sold in 2019 and a flat that sold in 2024 aren't directly
comparable — the whole market moved between those dates. This strips that
market-wide movement out, so what's left in the sold-price data reflects the
flat's own qualities, not when it happened to sell.
"""

import pandas as pd

INDEX_CSV_PATH = "data/rvd_avg_price_by_class_monthly.csv"
INDEX_COLUMN = "Class B New Territories"


def load_index(csv_path=INDEX_CSV_PATH):
    """Load the RVD CSV into a DataFrame indexed by month (as a Timestamp)."""
    df = pd.read_csv(csv_path, skiprows=1)
    df["Month"] = pd.to_datetime(df["Month"], format="%m-%Y")
    return df.set_index("Month")[INDEX_COLUMN]


def index_at(index_series, date):
    """Return the index value for the month containing `date`.

    `date` can be a string like "2021-06-15" or "2021-06", or a
    datetime/Timestamp. Raises a clear error if that month isn't in the data
    (e.g. a typo, or a date before 1999 / after the latest available month).
    """
    month = pd.Timestamp(date).replace(day=1)
    if month not in index_series.index:
        earliest, latest = index_series.index.min(), index_series.index.max()
        raise ValueError(
            f"No RVD index value for {month.strftime('%Y-%m')}. "
            f"Data only covers {earliest:%Y-%m} to {latest:%Y-%m}."
        )
    return index_series.loc[month]


def adjust_price(price, sale_date, index_series, base_date=None):
    """Convert `price`, sold on `sale_date`, into base_date-equivalent money.

    base_date defaults to the most recent month in the index, so every
    adjusted price ends up expressed in "as if sold this month" terms —
    directly comparable to a current asking price.
    """
    if base_date is None:
        base_date = index_series.index.max()
    base_index = index_at(index_series, base_date)
    sale_index = index_at(index_series, sale_date)
    return price * base_index / sale_index


if __name__ == "__main__":
    index_series = load_index()
    example_price = 6_000_000
    example_date = "2019-06"
    adjusted = adjust_price(example_price, example_date, index_series)
    latest_month = index_series.index.max().strftime("%Y-%m")
    print(f"RVD Class B (NT) index loaded: {len(index_series)} months, "
          f"{index_series.index.min():%Y-%m} to {index_series.index.max():%Y-%m}")
    print(f"Example: HK${example_price:,} sold in {example_date} "
          f"is worth ~HK${adjusted:,.0f} in {latest_month} terms")
