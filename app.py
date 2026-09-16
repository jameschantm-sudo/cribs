import pickle
from datetime import date

import streamlit as st

from estate_info import ALL_BLOCKS, completion_year

MODEL_PATH = "model.pkl"
MODEL_MAE_HKD = 450_000  # from Stage 4's cross-validation - see LEARNING_LOG.md


@st.cache_resource
def load_model():
    with open(MODEL_PATH, "rb") as f:
        saved = pickle.load(f)
    return saved["model"], saved["features"]


st.title("cribs — City One Shatin Valuation Benchmark")
st.write(
    "Tells you whether a City One Shatin listing looks fairly priced **today**, "
    "for what it objectively is — not where prices are headed."
)

model, features = load_model()

st.subheader("Listing details")
col1, col2 = st.columns(2)
with col1:
    area = st.number_input("Saleable area (sq ft)", min_value=200, max_value=1200, value=451, step=1)
    floor = st.number_input("Floor", min_value=1, max_value=40, value=15, step=1)
with col2:
    block = st.selectbox("Block", ALL_BLOCKS, index=ALL_BLOCKS.index(1))
    asking_price = st.number_input("Asking price (HK$)", min_value=1_000_000, max_value=30_000_000, value=6_000_000, step=50_000)

age = date.today().year - completion_year(block)
st.caption(f"Block {block} was completed in {completion_year(block)}, making it {age} years old today.")

if st.button("Check this listing"):
    X = [[area, floor, age]]
    fair_value = model.predict(X)[0]
    premium_hkd = asking_price - fair_value
    premium_pct = premium_hkd / fair_value * 100

    st.subheader("Result")
    st.metric("Objective fair-value estimate", f"HK${fair_value:,.0f}")
    st.metric(
        "Premium over fair value",
        f"HK${premium_hkd:,.0f}",
        f"{premium_pct:+.1f}%",
        delta_color="inverse",
    )

    st.caption(
        f"This model is typically off by about HK${MODEL_MAE_HKD:,.0f} on a flat it "
        "hasn't seen, so treat small premiums (roughly within that range) as noise, "
        "not a real signal."
    )
    st.warning(
        "This premium is **not proof of overpricing**. It's whatever asking price isn't "
        "explained by area, floor, and building age — which also includes real things "
        "the model doesn't see, like renovation, view, or exact unit condition. Use it "
        "as a prompt to look closer, not a verdict."
    )

st.divider()
with st.expander("How this works, and its limits"):
    st.write(
        """
        The fair-value estimate comes from a linear regression trained on 678 real
        City One Shatin sold transactions (2018–2026), each converted into current-
        market terms using the government's official house price index — so market-wide
        ups and downs are already stripped out before the model ever sees the price.

        The model only knows three things about a flat: its size, its floor, and the
        building's age. On held-out data it hasn't seen, it explains roughly 70% of
        price variation (R² ≈ 0.70) and is typically accurate to within about
        HK$450,000. See `LEARNING_LOG.md` in the project repo for the full build process,
        including how that accuracy figure was checked.
        """
    )
