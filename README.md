# cribs — HK Property Valuation Tool

**Live app: [o2nbv4t8xtvmj23gt7fvth.streamlit.app](https://o2nbv4t8xtvmj23gt7fvth.streamlit.app)**

Tells you whether a Hong Kong flat is fairly priced *today*, and by how much, by separating
its objective worth (size, floor, building age, which estate) from the subjective "premium"
a seller is asking on top of that (renovation, staging, "modernness", etc.). Covers three
estates so far — **City One Shatin**, **Taikoo Shing**, and **Mei Foo Sun Chuen** — spanning
very different real price tiers, with a free-text address box that recognizes any of them.

**What this does not do:** predict where prices are going. It only answers "is this fair
today, for what it is?" — never "will prices rise?"

## How it works, briefly

1. Collected 1,683 real sold transactions across three estates from public listing data,
   2018–2026.
2. Converted every sold price into "today's market terms" using Hong Kong's official house
   price index (Rating and Valuation Department) — matched to each estate's own real region
   (Hong Kong Island / Kowloon / New Territories), so a 2019 sale and a 2025 sale, or a
   Hong Kong Island sale and a Kowloon sale, all become directly comparable.
3. Fit a linear regression on 1,663 cleaned transactions: `saleable area, floor, building
   age, which estate` → index-adjusted price.
4. For a live listing, `asking price − the model's fair-value estimate` = the premium,
   shown in HK$ and %. Type an address and Hong Kong's free government geocoding service
   figures out which covered estate it's in — or tells you plainly if it isn't one we cover
   yet, rather than guessing.

Full details, honest results, and limitations: see [`METHODOLOGY.md`](METHODOLOGY.md).
The stage-by-stage build process (what was built, why, and what would break it): see
[`LEARNING_LOG.md`](LEARNING_LOG.md).

## Running it locally

```
git clone https://github.com/jameschantm-sudo/cribs.git
cd cribs
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Project structure

```
collect_data.py         Scrapes raw transactions from 28hse, for any configured estate
clean_and_adjust.py      Cleans data, applies each estate's own price-index adjustment
train_model.py           Fits and evaluates the regression, saves model.pkl
estate_info.py           Reference data for every covered estate (blocks, ages, districts)
index_adjust.py          RVD price-index lookup and adjustment math
app.py                   The Streamlit app — address lookup, inputs, prediction
data/                    Raw and cleaned datasets, plus saved HTML snapshots for audit
model.pkl                The trained, saved regression model
```

## Status

**Phase 1** (single estate, City One Shatin): all 8 build stages complete. **Phase 2**
(multi-estate expansion — Taikoo Shing and Mei Foo Sun Chuen, plus free address-based
geocoding): data, model, and app all built and verified live in production. Built by an IB
student as a genuine skill-building / portfolio project, with AI-assisted implementation
(Claude Code) under direct, stage-by-stage human direction — see `METHODOLOGY.md` for the
full process, scope decisions, and honest limitations.
