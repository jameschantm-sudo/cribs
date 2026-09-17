# Methodology

## The problem

Hong Kong flat listings show an asking price, but not what that flat is actually *worth*.
Two identical-looking flats in the same estate can be listed at very different prices, and
the difference is a mix of: real objective differences (higher floor, bigger, newer-feeling)
and subjective ones (a seller's renovation, staging, or just optimism). A buyer has no easy
way to tell how much of an asking price is "real" versus "premium."

This tool answers a narrow, deliberately limited question: **for one specific estate, given
a flat's size, floor, and the building's age, what would a typical sale of that flat be worth
today — and how does that compare to what's actually being asked?**

It explicitly does **not** attempt to predict where prices are going. That's a different,
much harder, and much less honest problem to claim to solve with 3 features and one estate's
data.

## Data

### Sold transactions

683 real sold transactions for **City One Shatin** (Sha Tin, New Territories) were collected
from 28hse.com's public per-block transaction history pages — 14 of the estate's 52 blocks
(2 sampled from each of its 7 construction phases), spanning 2018–2026.

**Why City One Shatin**: it's a large (10,642-unit), high-transaction-volume estate, which
matters for two reasons — enough data to fit a model at all, and (more importantly) a
single, relatively contained construction history (1981–1988) that keeps "objective
differences between flats" mostly reducible to size, floor, and age, without needing to
model location or neighbourhood effects that a multi-estate dataset would require.

**Collection method**: automated (a script fetching each block's public history page,
1.5 seconds apart, saving the raw HTML for every page as an audit trail before parsing
anything from it). This was a deliberate, explicit scope decision — see "Scope decisions"
below — not silent scraping-by-default. No login-gated or ToS-explicit-forbidding source was
used or worked around.

**What's real vs. reference-only**: every row includes the site's displayed per-sqft rate
alongside the total price, used only to cross-check that the two numbers reconcile (they did,
on all 683 rows) — that rate is never used as a model input, since it's derived from price
and would leak the answer into the features.

**A genuine precision limit**: the source displays prices rounded (e.g. "$4.85M"), so
individual transaction prices may be off by up to roughly HK$10,000 from the exact
transacted figure. This is a limit of the public data, not something introduced by this
project.

### House price index

Hong Kong's Rating and Valuation Department publishes a real, free, monthly average price
series broken out by size class and region, from January 1999 onward
(`rvd.gov.hk/datagovhk/1.2M.csv`). City One Shatin's flats (284–853 sq ft in this sample)
mostly fall in RVD's "Class B" (40–69.9 m² / ~430–752 sq ft) — the **Class B, New
Territories** column is used as the adjustment index for every transaction, regardless of
whether an individual flat is slightly above or below that range, since the index is
stripping out market-wide movement over time, not adjusting for an individual flat's size
(size is already a separate model feature).

## Method

For each transaction, sold at price *P* on date *d*:

```
adjusted_price = P × index(today's month) / index(d)
```

This expresses every historical sale in "as if it sold this month" terms, so a 2019 sale and
a 2025 sale are directly comparable — before that adjustment, comparing them would just be
comparing different points in the market cycle, not the flats themselves.

A linear regression is then fit on the cleaned, adjusted data:

```
adjusted_price ~ saleable_area_sqft + floor + age_at_sale
```

- 3 features for 678 rows — deliberately conservative, to avoid overfitting.
- `age_at_sale` uses each transaction's own sale year minus its block's real construction-
  completion year (sourced from Wikipedia, cross-checked against the site's own
  block-to-phase grouping) — not today's age, since that's what the flat's age actually was
  at the moment it sold.
- Trained on 80% of the data, evaluated on the untouched other 20%, plus 5-fold
  cross-validation for a more stable accuracy estimate (see Results).

For a live listing, the same three features are fed into the fitted model to get a
fair-value estimate; `asking price − fair-value estimate` is reported as the premium.

## Results

| Metric | Value |
|---|---|
| R² (5-fold cross-validation) | ≈0.70 (range 0.58–0.84 across folds) |
| MAE (5-fold cross-validation) | ≈HK$450,000 |

**A single 80/20 test split initially reported R² = 0.839** — that number wasn't wrong, but
it wasn't the honest one to quote either: cross-validation (refitting the same model on 5
different 80/20 splits) showed results ranging from 0.58 to 0.84 depending purely on which
rows happened to land in the test set. The stable, honest estimate is the cross-validated
mean, ≈0.70, not the best-looking single split.

**What the model learned** (coefficients, fit on the training split):
- +HK$7,878 per additional sq ft of saleable area
- +HK$16,497 per additional floor
- −HK$33,694 per additional year of building age at the time of sale

All three signs match real-world intuition (bigger, higher, newer → pricier), which is
reassuring but not proof of correctness on its own.

**What R² ≈ 0.70 means here, specifically**: roughly 70% of the price variation among City
One Shatin sales is explained by size, floor, and age alone. The remaining ~30% is exactly
the space this tool is built to expose as a "premium" — but see the limitation below before
treating that number as a clean measurement of subjective premium.

## Limitations, stated plainly

- **Single estate only.** Nothing here generalizes to other Hong Kong estates or districts —
  different estates have different price dynamics that 3 features and one estate's data
  can't capture. (See Future work.)
- **The "premium" is not proof of overpricing.** It's whatever the asking price isn't
  explained by area/floor/age — which includes both real subjective premium (renovation,
  staging) *and* real objective factors the model simply doesn't see (view, orientation,
  exact unit condition, stack position). The residual conflates these; it's a prompt to
  look closer, not a verdict.
- **Individual transaction prices carry the source's own rounding.** 28hse displays prices
  like "$4.85M," which may be off by up to ~HK$10,000 from the exact transacted figure —
  a real limit of the public data, not something this project introduced.
- **The index used is a size-class average, not estate-specific.** Class B, New Territories
  is a reasonable proxy for City One Shatin's market movement, but it isn't a City One
  Shatin-specific index (no such free public series exists).
- **Only each unit's latest recorded sale was collected**, not full historical resale chains
  per unit — sufficient for this project's purpose, but means the dataset isn't a complete
  transaction history of the estate.
- **The live app's fair-value estimate is expressed in whatever month the RVD index most
  recently covered** when the model was last trained (currently mid-2026), not literally
  "this instant" — a gap that would grow if the underlying data isn't refreshed periodically.

## Scope decisions worth being upfront about

This project was deliberately narrowed, twice, during the build:
1. From an originally-envisioned 15-month, multi-feature (mapping APIs, gradient boosting,
   computer vision) vision down to one estate, ≤5 features, linear regression only — to fit
   a real ~6-hours-a-week, one-semester budget.
2. Data collection was originally planned as fully manual (hand-copied transactions), and
   partway through was automated instead, after an explicit conversation about scope: the
   automation stayed bounded to this single estate (contained, ~100+ rows) rather than
   expanding to many districts, which would have been a materially different — and
   materially riskier — scraping footprint, and would have broken the ≤5-feature constraint
   this project deliberately keeps.

## Future work

A genuinely useful multi-district version of this idea is a real, separate future project,
not an extension bolted onto this one: it would need real location modeling (not a crude
per-district dummy variable), which is what richer methods (mapping/places data, gradient
boosting, or similar) are actually for — and a properly scoped data collection plan for many
estates, not just one.
