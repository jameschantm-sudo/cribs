"""Load the four privately collected Centanet extracts and apply the outlier rule.

Raw files live in data/centanet_raw/ (git-ignored). This script only reads them and
reports what it keeps and drops - it writes nothing, so no raw record is ever copied
anywhere that could be committed. Each dropped row gets exactly one reason, counted in
the summary, so the rule is auditable rather than a silent filter.

Rule, applied in this order per estate:
  1. no exact floor      - Centaline-sourced rows only give Lower/Middle/Upper, and the
                           model needs a number
  2. exact duplicate     - same date, building, floor, price and area
  3. bulk same-day batch - 8+ deals on one day in one building, or 15+ in one estate
                           (an investor block purchase, not independent market sales;
                           Taikoo Shing had 27 on 2025-05-27, no other estate-day passes 8)
  4. price-per-sq-ft outlier - psf under 0.5x or over 2.5x the median psf of the same
                           estate within +/-120 days. Catches partial-share and
                           family transfers (e.g. HK$1.65M for a 760 sq ft flat). The
                           high bound is deliberately loose: the errors in this data are
                           all low-side, and real top-floor units (Dynasty Court Tower 3,
                           HK$145M) sit well above their estate's median.
"""
import pandas as pd

RAW = "data/centanet_raw"
BULK_MIN_DEALS = 8
BULK_MIN_DEALS_ESTATE_DAY = 15
PSF_LOW, PSF_HIGH = 0.5, 2.5
WINDOW_DAYS = 120
MIN_NEIGHBOURS = 10


def _floor(value):
    """Exact floor as an int, or None for L/M/U bands (and G/LG, which the model can't use)."""
    value = str(value)
    if value.isdigit():
        return int(value)
    return None


def load_all():
    frames = []

    city = pd.read_csv(f"{RAW}/city_one_shatin_sold.csv", dtype=str)
    band = {"Lower Floor": "L", "Middle Floor": "M", "Upper Floor": "U"}
    frames.append(pd.DataFrame({
        "estate": "city_one_shatin",
        "date": city["date"],
        "building": city["site"] + "-" + city["block"],
        "floor": city["floor"].map(lambda f: band.get(f, f.replace("/F", ""))),
        "price": city["price_hkd"], "area": city["area_sqft"], "source": city["source"],
    }))

    taikoo = pd.read_csv(f"{RAW}/taikoo_shing_sold.csv", dtype=str)
    frames.append(pd.DataFrame({
        "estate": "taikoo_shing", "date": taikoo["date"],
        "building": taikoo["phase"] + "-" + taikoo["tower"],
        "floor": taikoo["floor"], "price": taikoo["price_hkd"],
        "area": taikoo["area_sqft"], "source": taikoo["source"],
    }))

    meifoo = pd.read_csv(f"{RAW}/mei_foo_sun_chuen_sold.csv", dtype=str)
    frames.append(pd.DataFrame({
        "estate": "mei_foo_sun_chuen", "date": meifoo["date"],
        "building": meifoo["phase"],
        "floor": meifoo["floor"], "price": meifoo["price_hkd"],
        "area": meifoo["area_sqft"], "source": meifoo["source"],
    }))

    dynasty = pd.read_csv(f"{RAW}/dynasty_court_sold.csv", dtype=str)
    frames.append(pd.DataFrame({
        "estate": "dynasty_court", "date": dynasty["date"],
        "building": dynasty["tower"],
        "floor": dynasty["floor"], "price": dynasty["price_hkd"],
        "area": dynasty["area_sqft"], "source": dynasty["source"],
    }))

    df = pd.concat(frames, ignore_index=True)
    df["date"] = pd.to_datetime(df["date"])
    df["price"] = df["price"].astype(float)
    df["area"] = df["area"].astype(float)
    df["floor_num"] = df["floor"].map(_floor)
    df["psf"] = df["price"] / df["area"]
    return df


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


if __name__ == "__main__":
    everything = load_all()
    kept, dropped = clean(everything)
    summary = everything.groupby("estate").size().rename("collected").to_frame()
    summary["kept"] = kept.groupby("estate").size()
    for reason in ["no exact floor", "exact duplicate", "bulk same-day batch", "psf outlier"]:
        summary[reason] = dropped[dropped["reason"] == reason].groupby("estate").size()
    print(summary.fillna(0).astype(int).to_string())
    print("\npsf outliers dropped (price, area, psf, date):")
    out = dropped[dropped["reason"] == "psf outlier"].sort_values(["estate", "psf"])
    print(out[["estate", "date", "price", "area", "psf"]].round(0).to_string(index=False))
