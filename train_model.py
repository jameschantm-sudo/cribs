"""
Stage 4 (Phase 2, revised) - fit one independent regression PER ESTATE.

Earlier version of this script fit one shared regression across all 5
estates, with "which estate" as dummy features. That failed badly: to also
fit Dynasty Court's ~HK$77M average price, the shared area/floor/age
coefficients got pulled to luxury-market scale, which then wildly
over-predicted mass-market estates (one City One Shatin flat was predicted
at a NEGATIVE price). Luxury and mass-market property don't scale the same
way per sqft/floor - one shared formula across an ~8x price range doesn't
work.

Fix: each estate gets its own model, trained only on its own data. Each one
uses just 3 features (area, floor, age) - simpler than the shared-model
version, not more complex, and avoids the max-5-features question
entirely.
"""

import pickle
import warnings

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error, r2_score
from sklearn.model_selection import KFold, cross_val_score, train_test_split

DATA_CSV = "data/all_estates_modeling_ready.csv"
MODEL_PATH = "model.pkl"
FEATURES = ["saleable_area_sqft", "floor", "age_at_sale"]
TARGET = "adjusted_price_hkd"

warnings.filterwarnings("ignore", message=".*encountered in matmul.*", category=RuntimeWarning)


def report(label, y_true, y_pred):
    print(f"  {label}:")
    print(f"    MAE:  HK${mean_absolute_error(y_true, y_pred):,.0f}")
    print(f"    MAPE: {mean_absolute_percentage_error(y_true, y_pred):.1%}")
    print(f"    R^2:  {r2_score(y_true, y_pred):.3f}")


def train_one_estate(estate_key, group):
    X = group[FEATURES].to_numpy(dtype="float64")
    y = group[TARGET].to_numpy(dtype="float64")
    n = len(group)

    print(f"\n{estate_key} ({n} rows):")

    if n >= 10:
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        model = LinearRegression().fit(X_train, y_train)
        report("Held-out test set", y_test, model.predict(X_test))

        n_splits = min(5, n // 5) if n // 5 >= 2 else 2
        if n_splits >= 2:
            kf = KFold(n_splits=n_splits, shuffle=True, random_state=42)
            cv_r2 = cross_val_score(LinearRegression(), X, y, cv=kf, scoring="r2")
            cv_mae = -cross_val_score(LinearRegression(), X, y, cv=kf, scoring="neg_mean_absolute_error")
            print(f"  {n_splits}-fold cross-validation:")
            print(f"    R^2 per fold: {np.round(cv_r2, 3)}")
            print(f"    R^2 mean:     {cv_r2.mean():.3f} (std: {cv_r2.std():.3f})")
            print(f"    MAE mean:     HK${cv_mae.mean():,.0f} (std: HK${cv_mae.std():,.0f})")
    else:
        print(f"  Only {n} rows - too few for a meaningful train/test split.")

    # Final model used by the app: fit on ALL of this estate's data, since
    # the splits above are purely for honest evaluation, not the model itself.
    final_model = LinearRegression().fit(X, y)
    print(f"  Final model (fit on all {n} rows):")
    print(f"    Base value: HK${final_model.intercept_:,.0f}")
    for feature, coef in zip(FEATURES, final_model.coef_):
        print(f"    {feature}: {coef:+,.0f} HK$ per unit")

    return final_model


# Below this many rows, cross-validated R^2 has shown near-zero or negative
# scores (Repulse Bay Garden: 40 rows, R^2 mean 0.08, ranging -0.39 to
# +0.61) - not enough real signal to model reliably. Excluded from the
# shipped app rather than shown with false confidence.
MIN_ROWS_TO_SHIP = 100


def train():
    df = pd.read_csv(DATA_CSV)
    models = {}
    for estate_key, group in df.groupby("estate"):
        if len(group) < MIN_ROWS_TO_SHIP:
            print(f"\n{estate_key} ({len(group)} rows): SKIPPED - below the "
                  f"{MIN_ROWS_TO_SHIP}-row threshold for a reliable model.")
            continue
        models[estate_key] = train_one_estate(estate_key, group)

    with open(MODEL_PATH, "wb") as f:
        pickle.dump({"models": models, "features": FEATURES}, f)
    print(f"\nSaved {len(models)} per-estate models to {MODEL_PATH}")
    return models


if __name__ == "__main__":
    train()
