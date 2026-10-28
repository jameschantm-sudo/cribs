"""
Affordability layer: how many years of a typical household's income does a
typical flat in each estate cost, and how does that compare with what
public-housing schemes assume?

Inputs (all public):
  - data/all_estates_modeling_ready.csv   our index-adjusted prices ("today's terms")
  - data/census_130-06806_household_income.json
        Census & Statistics Dept table 130-06806, median monthly household
        income by District Council district (General Household Survey)
  - PRH_INCOME_LIMITS, HOS_DISCOUNTS below, copied by hand from the Housing
    Authority (sources in comments)

Caveat: district median income describes everyone in the district, not buyers
of these particular estates. It is a rough yardstick, not a buyer profile.
"""
import json
import pandas as pd

CENSUS_YEAR = "2025"
INCOME_MEASURE = "MED_DH_INC"  # all domestic households; XEI = excluding economically inactive

# Housing Authority, effective 1 April 2026 (monthly, HK$), fetched 2026-10-07:
# https://www.housingauthority.gov.hk/en/flat-application/income-and-asset-limits/
PRH_INCOME_LIMITS = {1: 13230, 2: 20680, 3: 25870, 4: 32020, 5: 40150}

# Discount off assessed market value, HOS 2025 / Green Form (GSH) 2025:
# https://www.info.gov.hk/gia/general/202512/18/P2025121800574.htm
HOS_DISCOUNTS = {"HOS (White Form) 30%": 0.30, "GSH (Green Form) 40%": 0.40}

# estate_info.py districts -> Census DCDesc
DISTRICT_TO_CENSUS = {
    "SHA TIN DISTRICT": "Sha Tin",
    "EASTERN DISTRICT": "Eastern",
    "SHAM SHUI PO DISTRICT": "Sham Shui Po",
    "CENTRAL & WESTERN DISTRICT": "Central and Western",
}


def district_incomes():
    rows = json.load(open("data/census_130-06806_household_income.json"))["dataSet"]
    return {r["DCDesc"]: r["figure"] for r in rows
            if r["period"] == CENSUS_YEAR and r["sv"] == INCOME_MEASURE}


def build():
    from estate_info import ESTATES
    inc = district_incomes()
    df = pd.read_csv("data/all_estates_modeling_ready.csv")
    out = []
    for key, e in ESTATES.items():
        sub = df[df.estate == key]
        if key not in set(df.estate) or key == "repulse_bay_garden" or sub.empty:
            continue
        district_income = inc[DISTRICT_TO_CENSUS[e["district"]]]
        price = sub.adjusted_price_hkd.median()
        row = {
            "estate": e["name"],
            "n_sales": len(sub),
            "median_flat_hkd": round(price),
            "median_size_sqft": sub.saleable_area_sqft.median(),
            "district_median_income_pm": district_income,
            "price_to_income_years": round(price / (district_income * 12), 1),
            "years_at_PRH_4p_limit": round(price / (PRH_INCOME_LIMITS[4] * 12), 1),
        }
        for label, d in HOS_DISCOUNTS.items():
            row[f"price_after_{int(d*100)}pct_discount"] = round(price * (1 - d))
            row[f"years_after_{int(d*100)}pct_discount"] = round(
                price * (1 - d) / (district_income * 12), 1)
        out.append(row)
    return pd.DataFrame(out)


HOS_FILES = ["ssfs_018", "ssfs_019", "ssfs_020", "ssfs_022", "ssfs_023", "ssfs_024"]
SQM_TO_SQFT = 10.7639


def build_hos():
    """Per-court first-sale prices from the Housing Authority HOS datasets
    (data/ha_raw/ssfs_*.json, from data.housingauthority.gov.hk/psi/rest/export).

    These are discounted first sales, not market prices, and courts carry no
    district in the source, so years-of-income uses the territory-wide median
    ("Total") household income rather than a district one.
    """
    rows = []
    for f in HOS_FILES:
        for r in json.load(open(f"data/ha_raw/{f}.json"))["data"]:
            rows.append({
                "round": r["scheme_name"][:60] if "Society" not in r["scheme_name"] else "HOS 2022 + HS SSF",
                "scheme_type": r["scheme_type"],
                "court": r.get("court_estate_name") or r.get("court_name"),
                "signed": r["asp_sign_date"],
                "area_sqm": float(r["saleable_area"]),
                "price": float(r["sale_price"]),
            })
    df = pd.DataFrame(rows)
    df["area_sqft"] = df.area_sqm * SQM_TO_SQFT
    df["price_psf"] = df.price / df.area_sqft
    income_total = district_incomes()["Total"]
    g = df.groupby(["round", "scheme_type", "court"]).agg(
        n_flats=("price", "size"),
        median_price_hkd=("price", "median"),
        median_area_sqft=("area_sqft", "median"),
        median_price_psf=("price_psf", "median"),
    ).reset_index()
    # 2022+ rounds also sell flats in old public-rental ESTATEs at ~HK$0.3-0.7M;
    # keep them apart from newly built COURTs, which sell at ~HK$2.5-4M.
    g["kind"] = g.court.str.contains("ESTATE", case=False).map({True: "rental estate flats", False: "new court"})
    g["years_of_hk_median_income"] = (g.median_price_hkd / (income_total * 12)).round(1)
    return g.round({"median_price_hkd": 0, "median_area_sqft": 0, "median_price_psf": 0})


if __name__ == "__main__":
    h = build_hos()
    h.to_csv("data/hos_affordability_table.csv", index=False)
    print(h.groupby(["round", "kind"]).agg(courts=("court", "size"), flats=("n_flats", "sum"),
          median_psf=("median_price_psf", "median"), years=("years_of_hk_median_income", "median")))
    t = build()
    pd.set_option("display.width", 220, "display.max_columns", None)
    print(t.T)
    t.to_csv("data/affordability_table.csv", index=False)
