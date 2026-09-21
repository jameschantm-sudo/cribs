"""
Stage 4: fit the hedonic regression - the "objective fair value" model.

Trains on 80% of the data, tests on the other 20% it never saw - the
project brief's required held-out test set. On top of that, 5-fold
cross-validation is run too: that repeats the train/test split five
different ways and shows the *range* of results, not just one number.

Why bother with both: a single 80/20 split can land lucky or unlucky by
chance (small test sets are noisy). The first version of this script
reported a test R^2 of 0.839 from one split - looked great, but cross-
validation showed scores ranging from 0.58 to 0.84 depending on which rows
happened to land in the test set. 0.839 wasn't wrong, it just wasn't the
honest picture on its own - report the range, not just the best-looking
number.
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
# "estate" is categorical (3 estates) - encoded as 2 dummy columns, with
# city_one_shatin as the baseline (both dummies 0). Still 5 features total
# for ~1,663 rows, well inside the project's max-5-features rule.
BASE_FEATURES = ["saleable_area_sqft", "floor", "age_at_sale"]
ESTATE_DUMMY_COLUMNS = ["is_taikoo_shing", "is_mei_foo_sun_chuen"]
FEATURES = BASE_FEATURES + ESTATE_DUMMY_COLUMNS
TARGET = "adjusted_price_hkd"


def add_estate_dummies(df):
    df = df.copy()
    df["is_taikoo_shing"] = (df["estate"] == "taikoo_shing").astype(int)
    df["is_mei_foo_sun_chuen"] = (df["estate"] == "mei_foo_sun_chuen").astype(int)
    return df

# LinearRegression.predict() can trigger a spurious "divide by zero" /
# "overflow" RuntimeWarning on some Macs (Apple Accelerate BLAS false
# positive) even when the output is fully correct. Verified this directly:
# sklearn's predictions matched a manual `X @ coef_ + intercept_` computation
# exactly (0.0 max difference, no NaN/Inf) before deciding this was safe to
# silence rather than a real problem.
warnings.filterwarnings("ignore", message=".*encountered in matmul.*", category=RuntimeWarning)


def report(label, y_true, y_pred):
    print(f"{label}:")
    print(f"  MAE:  HK${mean_absolute_error(y_true, y_pred):,.0f}")
    print(f"  MAPE: {mean_absolute_percentage_error(y_true, y_pred):.1%}")
    print(f"  R^2:  {r2_score(y_true, y_pred):.3f}")


def train():
    df = pd.read_csv(DATA_CSV)
    df = add_estate_dummies(df)
    # Explicit float64 avoids a harmless but noisy numpy/Accelerate BLAS
    # warning on some Macs when sklearn is fed pandas' default int64 columns.
    X = df[FEATURES].to_numpy(dtype="float64")
    y = df[TARGET].to_numpy(dtype="float64")

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = LinearRegression()
    model.fit(X_train, y_train)

    print(f"Trained on {len(X_train)} rows, held out {len(X_test)} rows for testing\n")
    report("Training set (comparison only, NOT the accuracy claim)", y_train, model.predict(X_train))
    print()
    report("Held-out test set (one 80/20 split)", y_test, model.predict(X_test))

    print("\n5-fold cross-validation (5 different 80/20 splits, shows the honest range):")
    kf = KFold(n_splits=5, shuffle=True, random_state=42)
    cv_r2 = cross_val_score(LinearRegression(), X, y, cv=kf, scoring="r2")
    cv_mae = -cross_val_score(LinearRegression(), X, y, cv=kf, scoring="neg_mean_absolute_error")
    print(f"  R^2 per fold:  {np.round(cv_r2, 3)}")
    print(f"  R^2 mean:      {cv_r2.mean():.3f}  (std: {cv_r2.std():.3f})")
    print(f"  MAE mean:      HK${cv_mae.mean():,.0f}  (std: HK${cv_mae.std():,.0f})")

    print("\nWhat the model learned (fit on the full 80% training split above):")
    print(f"  Base value (intercept): HK${model.intercept_:,.0f}")
    for feature, coef in zip(FEATURES, model.coef_):
        print(f"  {feature}: {coef:+,.0f} HK$ per unit")

    with open(MODEL_PATH, "wb") as f:
        pickle.dump({"model": model, "features": FEATURES}, f)
    print(f"\nModel saved to {MODEL_PATH}")

    return model


if __name__ == "__main__":
    train()
