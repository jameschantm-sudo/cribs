import json
import pickle
import urllib.parse
import urllib.request
from datetime import date

import streamlit as st

from estate_info import ESTATES, OBSERVED_RANGES, block_label, blocks_for, completion_year

MODEL_PATH = "model.pkl"
ALS_URL = "https://www.als.gov.hk/lookup"

# Each estate has its own model with its own real accuracy - from Phase 2's
# per-estate cross-validation (see LEARNING_LOG.md). Reported per estate,
# not as one shared number, since they genuinely differ a lot.
MODEL_MAE_HKD = {
    "city_one_shatin": 454_501,
    "taikoo_shing": 1_167_952,
    "mei_foo_sun_chuen": 698_679,
    "dynasty_court": 8_189_785,
}


@st.cache_resource
def load_models():
    with open(MODEL_PATH, "rb") as f:
        saved = pickle.load(f)
    return saved["models"], saved["features"]


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


def match_estate(als_estate_name, covered_keys):
    """Match ALS's estate name text to one of our covered, shippable
    estates, if any - never an estate we collected data for but excluded
    (e.g. Repulse Bay Garden - too few transactions to model reliably)."""
    if not als_estate_name:
        return None
    for key in covered_keys:
        name = ESTATES[key]["name"]
        if name.upper() in als_estate_name.upper() or als_estate_name.upper() in name.upper():
            return key
    return None


st.title("cribs — HK Property Valuation Benchmark")
st.write(
    "Tells you whether a listing looks fairly priced **today**, for what it objectively "
    "is — not where prices are headed."
)

models, features = load_models()
covered_keys = list(models.keys())
estate_names = {key: ESTATES[key]["name"] for key in covered_keys}

st.subheader("Find your estate")
address = st.text_input("Type an address (optional)", placeholder="e.g. 18 Taikoo Shing Road")
matched_key = None
if address:
    with st.spinner("Looking up address..."):
        als_estate, district = geocode(address)
    matched_key = match_estate(als_estate, covered_keys)
    if matched_key:
        st.success(f"Recognized: **{estate_names[matched_key]}** ({district or ESTATES[matched_key]['district']}) — we have data for this estate.")
    elif district:
        st.warning(
            f"That address is in **{district}**, but we don't have a reliable model there yet. "
            f"Currently covering: {', '.join(estate_names.values())}."
        )
    else:
        st.warning("Couldn't resolve that address. Try a more specific one, or pick an estate below.")

default_index = covered_keys.index(matched_key) if matched_key else 0
estate_key = st.selectbox(
    "Or choose an estate directly",
    options=covered_keys,
    format_func=lambda k: estate_names[k],
    index=default_index,
)

st.subheader("Listing details")
col1, col2 = st.columns(2)
with col1:
    area = st.number_input("Saleable area (sq ft)", min_value=200, max_value=6000, value=500, step=1)
    floor = st.number_input("Floor", min_value=1, max_value=70, value=15, step=1)
with col2:
    block_options = blocks_for(estate_key)
    block = st.selectbox("Block", block_options, format_func=lambda b: f"{b} ({block_label(estate_key, b)})")
    asking_price = st.number_input("Asking price (HK$)", min_value=1_000_000, max_value=500_000_000, value=6_000_000, step=50_000)

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
    model = models[estate_key]
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

    mae = MODEL_MAE_HKD[estate_key]
    st.caption(
        f"This model (fit only on {estate_names[estate_key]}'s own data) is typically off by "
        f"about HK${mae:,.0f} on a flat it hasn't seen, so treat small premiums (roughly "
        "within that range) as noise, not a real signal."
    )
    st.warning(
        "This premium is **not proof of overpricing**. It's whatever asking price isn't "
        "explained by area, floor, and building age — which also includes real things the "
        "model doesn't see, like renovation, view, or exact unit condition. Use it as a "
        "prompt to look closer, not a verdict."
    )

st.divider()
with st.expander("How this works, and its limits"):
    st.write(
        """
        Each estate has its **own independent** regression, trained only on that estate's
        own real sold transactions - not one shared formula across estates. An earlier
        version tried one shared model with "which estate" as an extra input; it badly
        over-predicted smaller estates in order to also fit Dynasty Court's much higher
        prices (one flat came out with a *negative* predicted price). Separate models fixed
        that, and also mean each one only needs 3 simple inputs: size, floor, and building
        age.

        Every transaction was converted into current-market terms using the government's
        official house price index for its own region and size class, before the model ever
        saw the price - so market-wide ups and downs are already stripped out.

        Accuracy genuinely differs by estate (see the note under each result) - some
        estates have more data and tighter, more reliable estimates than others. One estate
        we collected real data for, Repulse Bay Garden, was excluded entirely: with only 40
        transactions available, its model had essentially no real predictive power (R² near
        zero) - shown here honestly rather than shipped with false confidence. See
        `LEARNING_LOG.md` and `METHODOLOGY.md` in the project repo for the full build
        process and honest limitations.
        """
    )
