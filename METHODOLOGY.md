# Methodology

## The problem

Hong Kong flat listings show an asking price, but not what that flat is actually *worth*.
Two identical-looking flats in the same estate can be listed at very different prices, and
the difference is a mix of: real objective differences (higher floor, bigger, newer-feeling,
which building it's in) and subjective ones (a seller's renovation, staging, or just
optimism). A buyer has no easy way to tell how much of an asking price is "real" versus
"premium."

This tool answers a narrow, deliberately limited question: **for a flat in one of a small
set of specific estates, given its size, floor, building age, and which estate it's in, what
would a typical sale of that flat be worth today — and how does that compare to what's
actually being asked?**

It explicitly does **not** attempt to predict where prices are going. That's a different,
much harder, and much less honest problem to claim to solve with 5 features and three
estates' worth of data.

## Data

### Sold transactions

**1,683 real sold transactions** across three estates were collected from 28hse.com's public
per-block transaction history pages, 2018–2026:

| Estate | District | Rows | Price/sqft (median, adjusted) |
|---|---|---|---|
| City One Shatin | Sha Tin (New Territories) | 683 | ≈HK$13,406 |
| Taikoo Shing | Eastern (Hong Kong Island) | 745 | ≈HK$16,282 |
| Mei Foo Sun Chuen | Sham Shui Po (Kowloon) | 255 | ≈HK$11,031 |

That price ordering matches real published Hong Kong market figures for these three estates
closely — a strong independent sanity check that the collection and adjustment pipeline is
working correctly, not just producing plausible-looking numbers.

**Why these three**: each is large and high-transaction-volume (enough real data to fit a
model), and together they deliberately span very different real price tiers and all three
Hong Kong regions (Island / Kowloon / New Territories) — chosen specifically so "which
estate" would be a meaningful, learnable feature rather than three near-identical markets.

**Collection method**: automated (a script fetching each sampled block's public history page,
1.5 seconds apart, saving the raw HTML for every page as an audit trail before parsing
anything from it) — 14–16 blocks sampled per estate (2 per construction phase), spread across
the estate rather than clustered. This was a deliberate, explicit scope decision at each
stage of the project (see "Scope decisions" below), not silent scraping-by-default. No
login-gated or ToS-explicit-forbidding source was used or worked around.

**What's real vs. reference-only**: every row includes the site's displayed per-sqft rate
alongside the total price, used only to cross-check that the two numbers reconcile (they did,
on all 1,683 rows across all three estates) — that rate is never used as a model input, since
it's derived from price and would leak the answer into the features.

**A genuine precision limit**: the source displays prices rounded (e.g. "$4.85M"), so
individual transaction prices may be off by up to roughly HK$10,000 from the exact
transacted figure. This is a limit of the public data, not something introduced by this
project.

### House price index

Hong Kong's Rating and Valuation Department publishes a real, free, monthly average price
series broken out by size class **and region**, from January 1999 onward
(`rvd.gov.hk/datagovhk/1.2M.csv`). Each estate is adjusted against its own correct region —
using the wrong region's index (e.g. adjusting a Hong Kong Island estate against the New
Territories market) would silently mis-price it:

| Estate | Index column used |
|---|---|
| City One Shatin | Class B, New Territories |
| Taikoo Shing | Class B, Hong Kong |
| Mei Foo Sun Chuen | Class B, Kowloon |

All three estates' flats predominantly fall in RVD's "Class B" (40–69.9 m² / ~430–752 sq ft)
range in this sample. As in Phase 1, one consistent column is used per estate regardless of
an individual flat's exact size, since the index strips out market-wide movement over time,
not size (size is already a separate model feature).

### Geocoding — address lookup

Typing an address into the live app uses Hong Kong government's free **Address Lookup
Service** (`als.gov.hk`) — no API key, no cost, no paid mapping service required. It resolves
a free-text address to a district and (when applicable) a named estate. The app only ever
auto-selects one of the three covered estates if ALS's returned estate name actually matches
one of them; for any other address, it reports the resolved district honestly and says
plainly that there's no data for it yet, rather than guessing based on district alone (a
different building in the same district is not the same market).

## Method

For each transaction, sold at price *P* on date *d*, using its own estate's index:

```
adjusted_price = P × index(today's month) / index(d)
```

This expresses every historical sale in "as if it sold this month" terms, so sales from
different years — and now, different estates and regions — are directly comparable.

A linear regression is fit on the cleaned, adjusted data:

```
adjusted_price ~ saleable_area_sqft + floor + age_at_sale + is_taikoo_shing + is_mei_foo_sun_chuen
```

- 5 features for 1,663 rows — "which estate" is encoded as 2 dummy variables (City One
  Shatin is the baseline, both 0), keeping the model linear and still well inside a
  conservative feature-to-row ratio.
- `age_at_sale` uses each transaction's own sale year minus its own estate's block's real
  construction-completion year (sourced from Wikipedia and 28hse's own per-phase estate
  pages, cross-checked against each other) — not today's age.
- Trained on 80% of the data, evaluated on the untouched other 20%, plus 5-fold
  cross-validation for a more stable accuracy estimate (see Results).

For a live listing, the same five features (with the correct estate's dummy variables set)
are fed into the fitted model to get a fair-value estimate; `asking price − fair-value
estimate` is reported as the premium.

## Results

| Metric | Value |
|---|---|
| R² (5-fold cross-validation) | ≈0.746 (range 0.678–0.855 across folds) |
| MAE (5-fold cross-validation) | ≈HK$896,000 |

The wider MAE compared to the single-estate version (≈HK$450,000) reflects the much larger
price range now being predicted across three estates, from City One Shatin to Taikoo Shing —
not the model getting worse at any individual estate.

**What the model learned** (coefficients, fit on the training split):
- +HK$10,035 per additional sq ft of saleable area
- +HK$20,790 per additional floor
- −HK$115,593 per additional year of building age at the time of sale
- +HK$3,113,215 baseline for Taikoo Shing vs. City One Shatin (same size/floor/age)
- +HK$884,723 baseline for Mei Foo Sun Chuen vs. City One Shatin (same size/floor/age)

**A coefficient that looked wrong, and the actual lesson**: read in isolation, the Mei Foo
Sun Chuen coefficient looks backwards — Mei Foo has the *lowest* real price per sq ft of the
three estates, yet its coefficient is positive. The catch: "which estate" and "building age"
are correlated in this data, because Mei Foo Sun Chuen is genuinely much older than the other
two (its real age range is 40–58 years; the other estates' is 29–50). A raw coefficient holds
every *other* feature artificially fixed, including at ages that don't exist for that estate
in reality. Testing the model with each estate's own *realistic* median age (not a shared
hypothetical one) reproduces the correct real-world ordering exactly. The individual
coefficients are not separately meaningful when features are correlated like this — only the
model's actual predictions, evaluated on realistic inputs, are trustworthy.

**What R² ≈ 0.746 means here, specifically**: roughly 75% of price variation across these
three estates' sales is explained by size, floor, age, and which estate. The remaining ~25%
is exactly the space this tool is built to expose as a "premium" — but see the limitations
below before treating that number as a clean measurement of subjective premium.

## Limitations, stated plainly

- **Only three estates.** The address lookup can recognize any real Hong Kong address, but
  the app only produces an honest estimate for these three — everywhere else, it says so
  plainly rather than guessing from district alone. (See Future work.)
- **The "premium" is not proof of overpricing.** It's whatever the asking price isn't
  explained by area/floor/age/estate — which includes both real subjective premium
  (renovation, staging) *and* real objective factors the model simply doesn't see (view,
  orientation, exact unit condition, stack position). The residual conflates these; it's a
  prompt to look closer, not a verdict.
- **Individual coefficients can mislead when features are correlated** — see the Mei Foo Sun
  Chuen example above. Don't read a single coefficient as "the effect of X"; the model's
  actual predictions on realistic inputs are what's trustworthy.
- **Individual transaction prices carry the source's own rounding.** 28hse displays prices
  like "$4.85M," which may be off by up to ~HK$10,000 from the exact transacted figure — a
  real limit of the public data, not something this project introduced.
- **The index used is a size-class-and-region average, not estate-specific.** Reasonable
  proxies for each estate's market movement, but not estate-specific indices (no free public
  series like that exists).
- **Only each unit's latest recorded sale was collected**, not full historical resale chains
  per unit — sufficient for this project's purpose, but means the dataset isn't a complete
  transaction history of any estate.
- **The live app's fair-value estimate is expressed in whatever month the RVD index most
  recently covered** when the model was last trained, not literally "this instant" — a gap
  that would grow if the underlying data isn't refreshed periodically.
- **The app inputs allow, but flag, values outside what was actually observed** for the
  chosen estate (e.g. an unusually large flat) — shown as a warning rather than blocked,
  since the estimate becomes an extrapolation beyond the real training data at that point.

## Scope decisions worth being upfront about

This project was deliberately narrowed and re-scoped several times during the build, and
each decision is recorded honestly here rather than smoothed over:

1. **Initial scope-down**: from an originally-envisioned 15-month, multi-feature (mapping
   APIs, gradient boosting, computer vision) vision to one estate, ≤5 features, linear
   regression only — to fit a real ~6-hours-a-week, one-semester budget.
2. **Phase 1 automation decision**: data collection was originally planned as fully manual
   (hand-copied transactions), and partway through was automated instead, after an explicit
   conversation about scope — kept bounded to a single estate (~100+ rows) rather than many
   districts, which would have been a materially riskier scraping footprint and would have
   broken the ≤5-feature constraint.
3. **Phase 2 scope fork**: after Phase 1 shipped, the goal of supporting "any address in Hong
   Kong" came up again — this time resolved not by rejecting it, but by finding a version
   that was actually achievable within the same constraints: free government geocoding
   (solving "any address" honestly) combined with a *small, deliberately chosen* set of
   estates (not every district) so the model could stay linear and the scraping footprint
   stayed contained. The harder version — generalizing to literally anywhere in Hong Kong
   with proper location modeling — remains explicitly out of scope (see Future work).

## Future work

A version that generalizes to *anywhere* in Hong Kong, not just three chosen estates, is a
real, separate future project, not an extension bolted onto this one: it would need real
location modeling (not a crude per-district dummy variable, and not hand-picking estates one
at a time), which is what richer methods (mapping/places data, gradient boosting, or similar)
are actually for — and a properly scoped data collection plan for many more estates.
