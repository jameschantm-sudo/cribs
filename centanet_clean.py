"""Load the four privately collected Centanet extracts for comparison.

Raw files live in data/centanet_raw/ (git-ignored). The outlier rule itself lives in
outlier_rule.py and is shared with the shipped 28hse pipeline. Running this file only
reads and reports - it writes nothing, so no raw record is ever copied anywhere that could
be committed.
"""
import pandas as pd

from outlier_rule import clean  # noqa: F401  (re-exported for train_centanet.py)

RAW = "data/centanet_raw"


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
