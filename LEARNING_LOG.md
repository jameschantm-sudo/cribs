# Learning Log

Each entry: what we built, why, the code that actually matters, what would break it, and a
checkpoint question you should be able to answer yourself before moving on.

---

## Stage 0 — Environment scaffold (2026-09-15)

**What we built**
- A project folder (`cribs/`) with its own **virtual environment** (`.venv/`) — an isolated
  copy of Python just for this project, so its package versions can't clash with anything
  else on your laptop.
- A git repo (`git init`), so every change from here on is tracked and reversible.
- `app.py` — the smallest possible Streamlit app: it just proves the tool that will host the
  real app (Streamlit) actually works on this machine.
- `requirements.txt` — the exact list of packages the project needs (`streamlit`, `pandas`,
  `scikit-learn`). This is what Streamlit Community Cloud reads to rebuild your environment
  when you deploy — without it, the live app has no idea what to install.
- `.gitignore` — tells git to never track `.venv/` (it's huge and machine-specific; anyone
  cloning the repo rebuilds their own from `requirements.txt`) or Python's cached bytecode.

**The lines that actually matter**

```python
import streamlit as st

st.title("cribs — HK Property Valuation Tool")
st.write("Scaffold is running. Nothing computed yet — this is Stage 0.")
```

- `import streamlit as st` — pulls in the library. Everything Streamlit does on the page is a
  method on `st`.
- `st.title(...)` / `st.write(...)` — each call to `st.something` draws one element on the
  page, top to bottom, in the order you call them. There's no separate "HTML file" — the
  Python script *is* the page layout.

**What would break it**
- Running `python app.py` directly instead of `streamlit run app.py` — Streamlit apps are not
  run like normal scripts; the `streamlit run` command starts a local web server and re-runs
  your script top-to-bottom on every interaction.
- Deleting or mis-naming `requirements.txt` before deploying — the cloud deploy would fail
  because it wouldn't know to install Streamlit.
- Being inside the wrong Python environment (forgetting to `source .venv/bin/activate`) — you'd
  get a `ModuleNotFoundError: No module named 'streamlit'` even though it's installed, because
  it's installed *inside* `.venv`, not system-wide.

**Checkpoint question**
If you ran `streamlit run app.py` on a totally fresh laptop that had Python but had never seen
this project before, what two things would you need to do first, and why, before it would work?
(Hint: think about what `.venv` and `requirements.txt` are each for.)

---

## Stage 1 — Index adjustment (2026-09-16)

**What we built**
- `data/rvd_avg_price_by_class_monthly.csv` — a real snapshot of the Rating and Valuation
  Department's official average private-domestic price data, broken out by size class and
  region, monthly from Jan 1999 to Jul 2026. Downloaded once and saved into the repo so our
  results stay reproducible even after RVD updates the live file.
- `index_adjust.py` — turns an old sold price into "what that flat would be worth if it sold
  today," using the "Class B, New Territories" column (City One Shatin's flats mostly run
  430–752 sq ft, which is RVD's Class B).

**Correction from earlier**: I'd originally pointed you at a different RVD file (`1.5M.csv`)
and called its column "Class B, New Territories" — that file actually bundles Classes A, B
and C together into one column, it doesn't split them out. `1.2M.csv` (used here) does split
them, so it's the more precise source. Worth knowing this happened — always worth checking
a data file's actual columns rather than trusting a title.

**The lines that actually matter**

```python
def adjust_price(price, sale_date, index_series, base_date=None):
    if base_date is None:
        base_date = index_series.index.max()
    base_index = index_at(index_series, base_date)
    sale_index = index_at(index_series, sale_date)
    return price * base_index / sale_index
```

- This is the whole method from the project brief in one line: `price × base_index ÷
  sale_index`. If the market went *up* between the sale and today, `base_index >
  sale_index`, so the old price gets scaled *up* to match — and vice versa.
- `base_date` defaults to the newest month in the file, so every adjusted price ends up in
  "as if it sold this month" terms — directly comparable to a live asking price later.
- We never look at the actual units ($/sqft? $/sqm?) of the RVD series — because we only
  ever take a *ratio* between two dates, the units cancel out. Only the up/down movement
  between two points in time matters.

**What would break it**
- A `sale_date` outside 1999-01–2026-07 (whatever the file currently covers) — raises a
  clear error rather than silently returning a wrong number. Good: silent wrong numbers are
  the dangerous kind.
- Mixing up `sale_date` and `base_date` order — the formula isn't symmetric, so swapping
  them would scale prices the wrong direction.
- If RVD ever renames "Class B New Territories", `INDEX_COLUMN` in the script needs updating
  to match — it's a hardcoded string, not something that auto-detects.

**Checkpoint question**
Two flats sell for the exact same price, one in 2019 and one in 2024. After running both
through `adjust_price`, will their adjusted values be the same, higher, or lower than the
raw price — and why might they end up *different from each other* even though the raw price
was identical?
