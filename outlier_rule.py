"""Outlier rule for flat-sale records, applied the same way to every source.

Each dropped row gets exactly one reason, so the rule is auditable rather than a silent
filter. Applied in this order per estate:
  1. no exact floor      - some records only give Lower/Middle/Upper, and the model needs
                           a number
  2. exact duplicate     - same date, building, floor, price and area
  3. bulk same-day batch - 8+ deals on one day in one building, or 15+ in one estate
                           (an investor block purchase, not independent market sales;
                           e.g. Taikoo Shing 2025-05-27, Dynasty Court Tower 2 2022-10-06)
  4. price-per-sq-ft outlier - psf under 0.5x or over 2.5x the median psf of the same
                           estate within +/-120 days. Catches partial-share and family
                           transfers (e.g. HK$1.65M for a 760 sq ft flat). The high bound
                           is deliberately loose: the errors in this data are all
                           low-side, and real top-floor units (Dynasty Court Tower 3,
                           HK$145M) sit well above their estate's median.

The thresholds were chosen while looking at privately collected Centanet records; the rule
itself uses no records, only these numbers, and is then checked against 28hse data.

Input frame columns: estate, date (datetime), building, floor, floor_num (int or NaN),
price, area, psf.
"""
import pandas as pd

BULK_MIN_DEALS = 8
BULK_MIN_DEALS_ESTATE_DAY = 15
PSF_LOW, PSF_HIGH = 0.5, 2.5
WINDOW_DAYS = 120
MIN_NEIGHBOURS = 10


def clean(df):
    """Returns (kept, dropped) where dropped has a 'reason' column."""
    df = df.copy()
    df["reason"] = None

    df.loc[df["floor_num"].isna(), "reason"] = "no exact floor"

    live = df["reason"].isna()
    dup = df[live].duplicated(subset=["estate", "date", "building", "floor", "price", "area"], keep="first")
    df.loc[dup[dup].index, "reason"] = "exact duplicate"

    live = df["reason"].isna()
    per_day = df[live].groupby(["estate", "date", "building"])["price"].transform("size")
    df.loc[per_day[per_day >= BULK_MIN_DEALS].index, "reason"] = "bulk same-day batch"
    per_estate_day = df.groupby(["estate", "date"])["price"].transform("size")
    batch_day = (per_estate_day >= BULK_MIN_DEALS_ESTATE_DAY) & df["reason"].isna()
    df.loc[batch_day, "reason"] = "bulk same-day batch"

    live = df["reason"].isna()
    for estate, group in df[live].groupby("estate"):
        estate_median = group["psf"].median()
        for idx, row in group.iterrows():
            near = group[(group["date"] - row["date"]).abs() <= pd.Timedelta(days=WINDOW_DAYS)].drop(index=idx)
            median = near["psf"].median() if len(near) >= MIN_NEIGHBOURS else estate_median
            ratio = row["psf"] / median
            if ratio < PSF_LOW or ratio > PSF_HIGH:
                df.loc[idx, "reason"] = "psf outlier"

    return df[df["reason"].isna()].drop(columns="reason"), df[df["reason"].notna()]
