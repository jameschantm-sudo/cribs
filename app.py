import json
import pickle
import urllib.parse
import urllib.request
from datetime import date

import streamlit as st

from estate_info import ESTATES, OBSERVED_RANGES, block_label, blocks_for, completion_year

MODEL_PATH = "model.pkl"
MODEL_MAE_HKD = 900_000  # from Phase 2's cross-validation - see LEARNING_LOG.md
ALS_URL = "https://www.als.gov.hk/lookup"


@st.cache_resource
def load_model():
    with open(MODEL_PATH, "rb") as f:
        saved = pickle.load(f)
    return saved["model"], saved["features"]


def geocode(address):
    """Look up an address with Hong Kong's free government Address Lookup
    Service. Returns (estate_name_from_als, district) or (None, None) if the
    address can't be resolved or the service is unreachable - never raises,
    since this is a convenience feature, not something the app depends on."""
    try:
        url = f"{ALS_URL}?{urllib.parse.urlencode({'q': address, 'n': 1})}"
        request = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(request, timeout=8) as response:
            data = json.loads(response.read().decode("utf-8"))
        premises = data["SuggestedAddress"][0]["Address"]["PremisesAddress"]["EngPremisesAddress"]
        estate_name = premises.get("EngEstate", {}).get("EstateName")
        district = premises.get("EngDistrict", {}).get("DcDistrict")
        return estate_name, district
    except Exception:
        return None, None


def match_estate(als_estate_name):
    """Match ALS's estate name text to one of our covered estates, if any."""
    if not als_estate_name:
        return None
    for key, config in ESTATES.items():
        if config["name"].upper() in als_estate_name.upper() or als_estate_name.upper() in config["name"].upper():
            return key
    return None


st.title("cribs — HK Property Valuation Benchmark")
st.write(
    "Tells you whether a listing looks fairly priced **today**, for what it objectively "
    "is — not where prices are headed."
)

model, features = load_model()

st.subheader("Find your estate")
address = st.text_input("Type an address (optional)", placeholder="e.g. 18 Taikoo Shing Road")
matched_key = None
if address:
    with st.spinner("Looking up address..."):
        als_estate, district = geocode(address)
    matched_key = match_estate(als_estate)
    if matched_key:
        st.success(f"Recognized: **{ESTATES[matched_key]['name']}** ({district or ESTATES[matched_key]['district']}) — we have data for this estate.")
    elif district:
        st.warning(
            f"That address is in **{district}**, but we don't have transaction data there yet. "
            f"Currently covering: {', '.join(c['name'] for c in ESTATES.values())}."
        )
    else:
        st.warning("Couldn't resolve that address. Try a more specific one, or pick an estate below.")

estate_names = {key: config["name"] for key, config in ESTATES.items()}
default_index = list(estate_names.keys()).index(matched_key) if matched_key else 0
estate_key = st.selectbox(
    "Or choose an estate directly",
    options=list(estate_names.keys()),
    format_func=lambda k: estate_names[k],
    index=default_index,
)

st.subheader("Listing details")
col1, col2 = st.columns(2)
with col1:
    area = st.number_input("Saleable area (sq ft)", min_value=200, max_value=2000, value=500, step=1)
    floor = st.number_input("Floor", min_value=1, max_value=70, value=15, step=1)
with col2:
    block_options = blocks_for(estate_key)
    block = st.selectbox("Block", block_options, format_func=lambda b: f"{b} ({block_label(estate_key, b)})")
    asking_price = st.number_input("Asking price (HK$)", min_value=1_000_000, max_value=100_000_000, value=6_000_000, step=50_000)

age = date.today().year - completion_year(estate_key, block)
st.caption(f"{block_label(estate_key, block)} was completed in {completion_year(estate_key, block)}, making it {age} years old today.")

area_range = OBSERVED_RANGES[estate_key]["area"]
floor_range = OBSERVED_RANGES[estate_key]["floor"]
out_of_range = area < area_range[0] or area > area_range[1] or floor < floor_range[0] or floor > floor_range[1]
if out_of_range:
    st.warning(
        f"This area or floor falls outside what we actually observed for {estate_names[estate_key]} "
        f"(area {area_range[0]}-{area_range[1]} sq ft, floor {floor_range[0]}-{floor_range[1]}) — "
        "the estimate below is an extrapolation beyond the real data and may be unreliable."
    )

if st.button("Check this listing"):
    is_taikoo_shing = 1 if estate_key == "taikoo_shing" else 0
    is_mei_foo_sun_chuen = 1 if estate_key == "mei_foo_sun_chuen" else 0
    X = [[area, floor, age, is_taikoo_shing, is_mei_foo_sun_chuen]]
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
        "explained by area, floor, building age, and which estate — which also includes "
        "real things the model doesn't see, like renovation, view, or exact unit condition. "
        "Use it as a prompt to look closer, not a verdict."
    )

st.divider()
with st.expander("How this works, and its limits"):
    st.write(
        """
        The fair-value estimate comes from a linear regression trained on 1,663 real sold
        transactions across three estates — City One Shatin, Taikoo Shing, and Mei Foo Sun
        Chuen — each converted into current-market terms using the government's official
        house price index for its own region, so market-wide ups and downs are already
        stripped out before the model ever sees the price.

        The model knows five things about a flat: its size, its floor, the building's age,
        and which of the three estates it's in. On held-out data it hasn't seen, it explains
        roughly 75% of price variation (R² ≈ 0.75) and is typically accurate to within about
        HK$900,000 — a wider margin than a single-estate model, since it now spans a much
        bigger price range (City One Shatin to Taikoo Shing). See `LEARNING_LOG.md` and
        `METHODOLOGY.md` in the project repo for the full build process and honest
        limitations, including why the address lookup only works for these three estates
        so far.
        """
    )
