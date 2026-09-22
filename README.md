# cribs — HK Property Valuation Tool

**Live app: [o2nbv4t8xtvmj23gt7fvth.streamlit.app](https://o2nbv4t8xtvmj23gt7fvth.streamlit.app)**

Tells you whether a Hong Kong flat is fairly priced *today*, and by how much, by separating
its objective worth (size, floor, building age, which estate) from the subjective "premium"
a seller is asking on top of that (renovation, staging, "modernness", etc.). Covers four
estates spanning mass-market to ultra-luxury — **City One Shatin**, **Taikoo Shing**,
**Mei Foo Sun Chuen**, and **Dynasty Court** — with a free-text address box that recognizes
any of them.

**What this does not do:** predict where prices are going. It only answers "is this fair
today, for what it is?" — never "will prices rise?"

## How it works, briefly

1. Collected 1,912 real sold transactions across five estates from public listing data,
   2018–2026 (one estate, Repulse Bay Garden, was excluded from the app itself — too few
   real transactions to model reliably; see `METHODOLOGY.md`).
2. Converted every sold price into "today's market terms" using Hong Kong's official house
   price index (Rating and Valuation Department) — matched to each estate's own real region
   and size class, so sales from different years, estates, and price tiers all become
   directly comparable.
3. Fit an **independent linear regression per estate** (`saleable area, floor, building age`
   → index-adjusted price) — not one shared model across estates, after an earlier shared
   version was found to badly mis-price flats (see `METHODOLOGY.md`, "A shared model that
   failed").
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
train_model.py           Fits and evaluates one independent model per estate, saves model.pkl
estate_info.py           Reference data for every estate (blocks, ages, districts, index columns)
index_adjust.py          RVD price-index lookup and adjustment math
app.py                   The Streamlit app — address lookup, inputs, prediction
data/                    Raw and cleaned datasets, plus saved HTML snapshots for audit
model.pkl                The trained, saved per-estate regression models
```

## Status

**Phase 1** (single estate, City One Shatin) and **Phase 2** (expansion to Taikoo Shing,
Mei Foo Sun Chuen, Dynasty Court, and Repulse Bay Garden, plus free address-based geocoding)
are both complete — data, models, and app built and verified live in production. Built by
an IB student as a genuine skill-building / portfolio project, with AI-assisted
implementation (Claude Code) under direct, stage-by-stage human direction — see
`METHODOLOGY.md` for the full process, scope decisions, and honest limitations, including a
real model-design failure that was caught and fixed rather than shipped.
