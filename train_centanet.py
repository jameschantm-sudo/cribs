"""Compare per-estate models trained on 28hse, Centanet, and both combined.

Reads the privately collected Centanet extracts (git-ignored) through
centanet_clean.py, index-adjusts them exactly like clean_and_adjust.py does, and
evaluates three training sets on the SAME held-out test set: the most recent 20% of
each estate's Centanet sales, which no variant trains on.

  A  28hse only, as shipped (no outlier filtering)
  A2 28hse only, after the same outlier rule as Centanet
  B  Centanet only
  C  both cleaned, de-duplicated on (date, floor, area, price)

Also prints 5-fold cross-validation for B and C, the same way train_model.py does for A.
Writes nothing unless --save is passed, which saves the C models to model_centanet.pkl
(git-ignored; the deployed app keeps using model.pkl).
"""
import pickle
import sys

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import KFold, cross_val_score

from centanet_clean import clean, load_all
from estate_info import ESTATES
from index_adjust import adjust_price, load_index

FEATURES = ["saleable_area_sqft", "floor", "age_at_sale"]
TARGET = "adjusted_price_hkd"
TEST_FRACTION = 0.2
KEY = ["sale_date", "floor", "saleable_area_sqft", "price_hkd"]

# Centanet's nine Taikoo Shing "terrace" groups are the 28hse phases (checked: tower counts
# per terrace equal the number of named buildings per 28hse phase). Keys are the order the
# terraces were saved in data/centanet_raw/taikoo_shing_sold.csv.
TAIKOO_TERRACE_TO_PHASE = {
    0: 5,  # Harbour View Gardens (East)
    1: 5,  # Harbour View Gardens (West)
    2: 4,  # Horizon Gardens
    3: 2,  # Kam Din Terrace
    4: 6,  # Kao Shan Terrace
    5: 8,  # Kwun Hoi Terrace
    6: 1,  # On Shing Terrace
    7: 3,  # Sing Fai Terrace
    8: 7,  # Tsui Woo Terrace
}


def phase_of(estate, building):
    if estate == "city_one_shatin":
        return int(building.split("-")[0])  # site number == 28hse phase
    if estate == "taikoo_shing":
        return TAIKOO_TERRACE_TO_PHASE[int(building.split("-")[0])]
    if estate == "mei_foo_sun_chuen":
        return int(building)
    return 1  # dynasty_court: single phase


def centanet_modeling_frame():
    kept, _ = clean(load_all())
    out = []
    too_recent = 0
    for estate, group in kept.groupby("estate"):
        config = ESTATES[estate]
        index = load_index(column=config["index_column"])
        last_month = index.dropna().index.max()
        group = group.copy()
        group["sale_date"] = group["date"].dt.strftime("%Y-%m-%d")
        recent = group["date"].dt.to_period("M").dt.to_timestamp() > last_month
        too_recent += int(recent.sum())
        group = group[~recent]
        phases = [phase_of(estate, b) for b in group["building"]]
        group["age_at_sale"] = group["date"].dt.year - pd.Series(phases, index=group.index).map(config["phase_completion_year"])
        group[TARGET] = [round(adjust_price(p, d, index)) for p, d in zip(group["price"], group["sale_date"])]
        group = group.rename(columns={"area": "saleable_area_sqft", "price": "price_hkd"})
        group["floor"] = group["floor_num"].astype(int)
        group["estate"] = estate
        out.append(group[["estate", "sale_date", "floor", "saleable_area_sqft", "age_at_sale", "price_hkd", TARGET]])
    print(f"Centanet rows not index-adjustable (after {last_month:%Y-%m}): {too_recent}\n")
    return pd.concat(out, ignore_index=True)


def clean_28hse(hse):
    """Run the Centanet outlier rule on the 28hse rows so the two sources are comparable."""
    frame = pd.DataFrame({
        "estate": hse["estate"], "date": pd.to_datetime(hse["sale_date"]),
        "building": hse["block"].astype(str), "floor": hse["floor"].astype(str),
        "floor_num": hse["floor"], "price": hse["price_hkd"].astype(float),
        "area": hse["saleable_area_sqft"].astype(float), "source": "28hse",
    })
    frame["psf"] = frame["price"] / frame["area"]
    kept, _ = clean(frame)
    return hse.loc[kept.index]


def evaluate(train, test):
    model = LinearRegression().fit(train[FEATURES].astype(float), train[TARGET].astype(float))
    pred = model.predict(test[FEATURES].astype(float))
    return mean_absolute_error(test[TARGET], pred), r2_score(test[TARGET], pred)


def cv(frame):
    n = len(frame)
    kf = KFold(n_splits=min(5, n // 5), shuffle=True, random_state=42)
    X, y = frame[FEATURES].to_numpy(float), frame[TARGET].to_numpy(float)
    r2 = cross_val_score(LinearRegression(), X, y, cv=kf, scoring="r2").mean()
    mae = -cross_val_score(LinearRegression(), X, y, cv=kf, scoring="neg_mean_absolute_error").mean()
    return mae, r2


def main(save=False):
    centanet = centanet_modeling_frame()
    hse_raw = pd.read_csv("data/all_estates_modeling_ready.csv")
    hse_raw = hse_raw[hse_raw["estate"].isin(centanet["estate"].unique())]
    hse = clean_28hse(hse_raw)
    print(f"28hse rows: {len(hse_raw)} raw -> {len(hse)} after the outlier rule\n")
    models = {}
    rows = []
    for estate in ["city_one_shatin", "taikoo_shing", "mei_foo_sun_chuen", "dynasty_court"]:
        cen = centanet[centanet["estate"] == estate].sort_values("sale_date")
        old = hse[hse["estate"] == estate]
        old_raw = hse_raw[hse_raw["estate"] == estate]
        cutoff = cen["sale_date"].iloc[int(len(cen) * (1 - TEST_FRACTION))]
        test = cen[cen["sale_date"] >= cutoff]
        test_keys = set(map(tuple, test[KEY].to_numpy()))

        cen_train = cen[cen["sale_date"] < cutoff]
        def before(frame):
            return frame[(frame["sale_date"] < cutoff) & ~frame[KEY].apply(tuple, axis=1).isin(test_keys)]
        raw_train, hse_train = before(old_raw), before(old)
        both_train = pd.concat([hse_train, cen_train]).drop_duplicates(subset=KEY)

        a0, a, b, c = evaluate(raw_train, test), evaluate(hse_train, test), evaluate(cen_train, test), evaluate(both_train, test)
        rows.append((estate, len(test), cutoff, (len(raw_train), a0), (len(hse_train), a), (len(cen_train), b), (len(both_train), c)))

        all_both = pd.concat([old, cen]).drop_duplicates(subset=KEY)
        print(f"{estate}: 28hse {len(old)} + Centanet {len(cen)} -> {len(all_both)} after de-duplication; "
              f"{len(old) + len(cen) - len(all_both)} overlapping")
        cva = cv(old)
        cvb, cvc = cv(cen), cv(all_both)
        print(f"   5-fold CV  28hse cleaned: MAE HK${cva[0]:,.0f}  R2 {cva[1]:.2f}   |   Centanet only: MAE HK${cvb[0]:,.0f}  R2 {cvb[1]:.2f}"
              f"   |   combined: MAE HK${cvc[0]:,.0f}  R2 {cvc[1]:.2f}\n")
        models[estate] = LinearRegression().fit(all_both[FEATURES].astype(float), all_both[TARGET].astype(float))

    print(f"Held-out test = latest {TEST_FRACTION:.0%} of each estate's Centanet sales (never trained on)")
    print("MAE in HK$ millions / R2, with training rows in brackets\n")
    print(f"{'estate':19s} {'test n':>6s} | {'A 28hse as shipped':>22s} | {'A2 28hse cleaned':>22s} | {'B Centanet':>22s} | {'C combined':>22s}")
    for estate, n, cutoff, *variants in rows:
        cells = [f"{m[0] / 1e6:5.2f} / {m[1]:4.2f}  ({size})" for size, m in variants]
        print(f"{estate:19s} {n:6d} | " + " | ".join(f"{c:>22s}" for c in cells))

    if save:
        with open("model_centanet.pkl", "wb") as f:
            pickle.dump({"models": models, "features": FEATURES}, f)
        print("\nSaved combined (C) models to model_centanet.pkl")


if __name__ == "__main__":
    main(save="--save" in sys.argv)
