"""Run real asking prices through the shipped models and summarise the premiums.

Usage:
    python check_listings.py drafts/listings_check.csv
    python check_listings.py --blocks taikoo_shing        # list valid block names/numbers

CSV columns: estate, block, area, floor, asking_price
  estate        city_one_shatin | taikoo_shing | mei_foo_sun_chuen | dynasty_court
  block         the block number or name as the app's Block dropdown shows it
                (e.g. 15, "Block 15", "Kin On")
  area          saleable area in sq ft
  floor         floor number
  asking_price  asking price in HK$ (e.g. 6500000)
Lines starting with # are ignored.

Uses the same model, age calculation and "no reliable estimate" rule as app.py. Asking prices
usually sit above what flats actually sell for, so expect the median premium to be positive;
what matters is whether it is steady across estates and whether the spread looks sensible
next to each model's typical error (MODEL_MAE_HKD), not whether it is zero.
"""
import pickle
import sys
import warnings
from datetime import date

import pandas as pd

from estate_info import BLOCK_LOOKUP, ESTATES, MODEL_MAE_HKD, OBSERVED_RANGES, completion_year

warnings.filterwarnings("ignore", message="X does not have valid feature names")


def resolve_block(estate, text):
    """Block number from '15', 'Block 15' or a building name like 'Kin On'."""
    text = str(text).strip()
    lookup = BLOCK_LOOKUP[estate]
    if text.isdigit() and int(text) in lookup:
        return int(text)
    for number, (_, label) in lookup.items():
        if text.lower() in (label.lower(), label.lower().replace("block ", "")):
            return number
    raise ValueError(f"unknown block {text!r} for {estate}; run --blocks {estate}")


def evaluate(models, row):
    estate = row["estate"]
    block = resolve_block(estate, row["block"])
    area, floor, asking = float(row["area"]), int(row["floor"]), float(row["asking_price"])
    age = date.today().year - completion_year(estate, block)
    model = models[estate]
    fair = model.predict([[area, floor, age]])[0]
    area_range, floor_range = OBSERVED_RANGES[estate]["area"], OBSERVED_RANGES[estate]["floor"]
    corners = [[a, f, age] for a in area_range for f in floor_range]
    reliable = fair > 0 and fair >= 0.5 * min(model.predict(corners))
    in_range = area_range[0] <= area <= area_range[1] and floor_range[0] <= floor <= floor_range[1]
    mae = MODEL_MAE_HKD[estate]
    return {
        "estate": estate, "block": block, "area": area, "floor": floor, "asking": asking,
        "fair": fair if reliable else float("nan"),
        "premium": asking - fair if reliable else float("nan"),
        "premium_pct": (asking - fair) / fair * 100 if reliable else float("nan"),
        "within_error": abs(asking - fair) <= mae if reliable else None,
        "note": "" if reliable and in_range else ("no reliable estimate" if not reliable else "outside observed range"),
    }


def main(path):
    models = pickle.load(open("model.pkl", "rb"))["models"]
    raw = pd.read_csv(path, comment="#", skipinitialspace=True)
    results = pd.DataFrame([evaluate(models, row) for _, row in raw.iterrows()])

    show = results.copy()
    for col in ["asking", "fair", "premium"]:
        show[col] = show[col].map(lambda v: f"{v / 1e6:.2f}M" if pd.notna(v) else "-")
    show["premium_pct"] = show["premium_pct"].map(lambda v: f"{v:+.1f}%" if pd.notna(v) else "-")
    print(show.drop(columns="within_error").to_string(index=False))

    ok = results.dropna(subset=["premium_pct"])
    print(f"\n{len(results)} listings, {len(ok)} with a reliable estimate "
          f"({len(results) - len(ok)} refused, {int((results['note'] == 'outside observed range').sum())} outside observed range)")
    if len(ok):
        print(f"premium vs fair value: median {ok['premium_pct'].median():+.1f}%, "
              f"mean {ok['premium_pct'].mean():+.1f}%, middle half {ok['premium_pct'].quantile(.25):+.1f}% to "
              f"{ok['premium_pct'].quantile(.75):+.1f}%")
        print(f"asking above fair value: {(ok['premium'] > 0).mean():.0%}; "
              f"within the model's typical error: {ok['within_error'].astype(bool).mean():.0%}")
        by = ok.groupby("estate")["premium_pct"].agg(["count", "median"]).round(1)
        print("\nby estate (median premium %):\n" + by.to_string())


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--blocks":
        for number, (phase, label) in sorted(BLOCK_LOOKUP[sys.argv[2]].items()):
            print(f"{number:4d}  {label}  (phase {phase}, completed {ESTATES[sys.argv[2]]['phase_completion_year'][phase]})")
    elif len(sys.argv) == 2:
        main(sys.argv[1])
    else:
        print(__doc__)
