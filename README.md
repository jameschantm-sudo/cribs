# cribs — HK Property Valuation Tool

**Live app: [o2nbv4t8xtvmj23gt7fvth.streamlit.app](https://o2nbv4t8xtvmj23gt7fvth.streamlit.app)**

Tells you whether a City One Shatin flat is fairly priced *today*, and by how much, by
separating its objective worth (size, floor, building age) from the subjective "premium" a
seller is asking on top of that (renovation, staging, "modernness", etc.).

**What this does not do:** predict where prices are going. It only answers "is this fair
today, for what it is?" — never "will prices rise?"

## How it works, briefly

1. Collected 683 real sold transactions for City One Shatin (Sha Tin, Hong Kong) from public
   listing data, 2018–2026.
2. Converted every sold price into "today's market terms" using Hong Kong's official house
   price index (Rating and Valuation Department), so a 2019 sale and a 2025 sale become
   directly comparable.
3. Fit a linear regression on 678 cleaned transactions: `saleable area, floor, building age`
   → index-adjusted price.
4. For a live listing, `asking price − the model's fair-value estimate` = the premium,
   shown in HK$ and %.

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
collect_data.py         Stage 2 — scrapes raw transactions from 28hse
clean_and_adjust.py      Stage 3 — cleans data, applies the price-index adjustment
train_model.py           Stage 4 — fits and evaluates the regression, saves model.pkl
estate_info.py           Shared reference data (phase completion years, block list)
index_adjust.py          Stage 1 — RVD price-index lookup and adjustment math
app.py                   Stage 5 — the Streamlit app itself
data/                    Raw and cleaned datasets, plus saved HTML snapshots for audit
model.pkl                The trained, saved regression model
```

## Status

All 8 build stages complete (data collection → cleaning → modeling → deployed app →
documentation). Built by an IB student as a genuine skill-building / portfolio project —
see `METHODOLOGY.md` for what it does and doesn't do well, honestly.
