# Methodology

## The problem

Hong Kong flat listings show an asking price, but not what that flat is actually *worth*.
Two identical-looking flats in the same estate can be listed at very different prices, and
the difference is a mix of: real objective differences (higher floor, bigger, newer-feeling)
and subjective ones (a seller's renovation, staging, or just optimism). A buyer has no easy
way to tell how much of an asking price is "real" versus "premium."

This tool answers a narrow, deliberately limited question: **for a flat in one of a small
set of specific estates, given its size, floor, and the building's age, what would a typical
sale of that flat be worth today — and how does that compare to what's actually being
asked?**

It explicitly does **not** attempt to predict where prices are going. That's a different,
much harder, and much less honest problem to claim to solve with 3 features and a handful of
estates' worth of data.

## Data

### Sold transactions

**1,912 real sold transactions** across five estates were collected from 28hse.com's public
per-block transaction history pages, 2018–2026 — spanning very different real price tiers,
from mass-market to ultra-luxury:

| Estate | District | Rows | Price/sqft (median, adjusted) | Shipped in app? |
|---|---|---|---|---|
| Mei Foo Sun Chuen | Sham Shui Po (Kowloon) | 255 | ≈HK$11,031 | Yes |
| City One Shatin | Sha Tin (New Territories) | 683 | ≈HK$13,406 | Yes |
| Taikoo Shing | Eastern (Hong Kong Island) | 745 | ≈HK$16,282 | Yes |
| Repulse Bay Garden | Southern (Hong Kong Island) | 40 | ≈HK$26,334 | **No — see below** |
| Dynasty Court | Central & Western (Hong Kong Island) | 189 | ≈HK$41,595 | Yes |

That price ordering matches real published Hong Kong market figures for these estates
closely — a strong independent sanity check that the collection and adjustment pipeline is
working correctly, not just producing plausible-looking numbers.

**Why these five**: each is large enough to have real transaction history, and together they
deliberately span all three Hong Kong regions and a huge price range (mass-market to
luxury) — chosen specifically to make "which estate matters a lot" a real, demonstrable
finding rather than an assumption.

**Repulse Bay Garden was excluded from the shipped app.** It only has 240 units total, so
only 40 real transactions exist for the entire 2018–2026 window — too few to fit a reliable
model (see Results). Its data was still collected and kept in the repo, honestly, rather
than hidden; it's just not one of the estates the live app offers.

**Collection method**: automated (a script fetching each sampled block's public history page,
1.5 seconds apart, saving the raw HTML for every page as an audit trail before parsing
anything from it). Large estates were sampled (2 blocks per construction phase); the two
much smaller luxury estates (Dynasty Court: 5 towers, Repulse Bay Garden: 12 blocks) had
every block scraped, since there weren't many to begin with. This was a deliberate, explicit
scope decision at each stage of the project (see "Scope decisions" below), not silent
scraping-by-default. No login-gated or ToS-explicit-forbidding source was used or worked
around.

**What's real vs. reference-only**: every row includes the site's displayed per-sqft rate
alongside the total price, used only to cross-check that the two numbers reconcile (they did,
on all 1,912 rows) — that rate is never used as a model input, since it's derived from price
and would leak the answer into the features.

**A genuine precision limit**: the source displays prices rounded (e.g. "$4.85M"), so
individual transaction prices may be off by up to roughly HK$10,000 from the exact
transacted figure. This is a limit of the public data, not something introduced by this
project.

### House price index

Hong Kong's Rating and Valuation Department publishes a real, free, monthly average price
series broken out by size class **and region**, from January 1999 onward
(`rvd.gov.hk/datagovhk/1.2M.csv`). Each estate is adjusted against its own correct region and
size class — using the wrong one would silently mis-price it:

| Estate | Index column used |
|---|---|
| City One Shatin | Class B, New Territories |
| Taikoo Shing | Class B, Hong Kong |
| Mei Foo Sun Chuen | Class B, Kowloon |
| Dynasty Court | Class D, Hong Kong |
| Repulse Bay Garden | Class E, Hong Kong |

The two luxury estates needed larger size classes (D and E) — checked against their real
collected area data, not assumed in advance. One consistent column is used per estate
regardless of an individual flat's exact size, since the index strips out market-wide
movement over time, not size (size is already a separate model feature).

**A real gap in this data, handled explicitly**: rare, large size classes sometimes have too
few sales in a given month for RVD to report a number at all (a literal "-" in the source
file). The pipeline coerces this to a proper missing value and raises a clear error for any
transaction that happens to fall in such a month, rather than silently treating "-" as zero
or guessing a number.

### Geocoding — address lookup

Typing an address into the live app uses Hong Kong government's free **Address Lookup
Service** (`als.gov.hk`) — no API key, no cost, no paid mapping service required. It resolves
a free-text address to a district and (when applicable) a named estate. The app only ever
auto-selects one of the *shipped* estates if ALS's returned estate name actually matches one
of them; for any other address — including Repulse Bay Garden's own real address, or a
district we've never collected data for — it reports the resolved district honestly and says
plainly that there's no reliable model for it yet, rather than guessing based on district
alone (a different building in the same district is not the same market).

## Method

For each transaction, sold at price *P* on date *d*, using its own estate's index:

```
adjusted_price = P × index(today's month) / index(d)
```

This expresses every historical sale in "as if it sold this month" terms, so sales from
different years, estates, and regions are all directly comparable.

**Each estate gets its own independent linear regression**, trained only on that estate's
own data:

```
adjusted_price ~ saleable_area_sqft + floor + age_at_sale
```

This wasn't the first design tried — see "A shared model that failed" below for why a single
model across all estates doesn't work, and why separate models is the better design, not
just a workaround.

- 3 features per model — the original max-5-features guideline, cleanly satisfied, for every
  estate.
- `age_at_sale` uses each transaction's own sale year minus its own estate's real
  construction-completion year (sourced from Wikipedia and 28hse's own per-phase estate
  pages, cross-checked against each other) — not today's age.
- Each estate's model is evaluated with a held-out test split plus cross-validation (fold
  count adapted to how much data that estate actually has - see Results), then a final
  version is fit on all of that estate's data for the app to actually use.

For a live listing, the selected estate's own model takes the three features and produces a
fair-value estimate; `asking price − fair-value estimate` is reported as the premium.

## A shared model that failed — and why the fix is simpler, not more complex

An earlier version fit **one** regression across all estates, with "which estate" encoded as
extra 0/1 features (2 dummies for 3 estates, later 4 dummies once Dynasty Court and Repulse
Bay Garden were added). Its aggregate accuracy looked excellent — R² ≈ 0.9. But checking
individual predictions (not just the aggregate score) on City One Shatin, an estate already
known to behave well, found flats predicted at 2-3x their real value, and one flat predicted
at a **negative price**.

The cause: fitting Dynasty Court's ~HK$77M average price into the same formula as City One
Shatin's ~HK$5M average pulled the shared area/floor/age coefficients up to luxury-market
scale. Applied back to a modest mass-market flat, those same coefficients wildly
overshoot. R² still looked good because the errors happened to cancel out on average across
the whole dataset — a textbook case of a summary statistic hiding a real, individual-level
failure.

**The fix**: stop sharing coefficients across estates at all. A separate model per estate is
not a more complicated design than dummy variables — it's simpler (3 features, not 5-7), and
it's the statistically correct response to the actual finding, which is that luxury and
mass-market Hong Kong property genuinely don't follow the same price-per-sqft relationship.
Forcing one shared slope across an 8x price range was the error, not the estate count.

## Results

Accuracy is reported **per estate** — they genuinely differ, and averaging them into one
number would hide that:

| Estate | Rows (after cleaning) | R² (cross-validated) | MAE (cross-validated) |
|---|---|---|---|
| City One Shatin | 662 | ≈0.88 (range 0.85–0.91) | ≈HK$336,000 |
| Taikoo Shing | 684 | ≈0.77 (range 0.69–0.85) | ≈HK$753,000 |
| Mei Foo Sun Chuen | 241 | ≈0.75 (range 0.68–0.82) | ≈HK$574,000 |
| Dynasty Court | 178 | ≈0.79 (range 0.76–0.82) | ≈HK$7,850,000 |
| ~~Repulse Bay Garden~~ | 40 | ≈0.08 (range **-0.39 to +0.61**) | ≈HK$14,800,000 — **excluded, see below** |

These figures are higher than the first version of this project reported (R² ≈ 0.42–0.80,
MAE ≈ HK$455,000 / 699,000 / 1,168,000 / 8,190,000 for City One Shatin / Mei Foo Sun Chuen /
Taikoo Shing / Dynasty Court). The difference is mostly **cleaning, and part of it flatters
the numbers**: removing non-market sales (next section) takes noisy rows out of the models'
training data *and out of the cross-validation test folds*, so the two sets of figures were
measured on different rows and are not a like-for-like improvement. Because the old and new
test rows differ, treat the cleaned figures as "accuracy on ordinary market sales," which is
what a normal asking price is compared against, not as proof the model got that much better.

MAE scales with each estate's own price level (Dynasty Court's absolute dollar error is
much larger than City One Shatin's, in *proportion* they're more comparable — roughly
6–11% of the estate's average price).

**Why Repulse Bay Garden isn't shipped**: with only 40 real transactions to learn from,
cross-validation R² ranges from clearly negative (worse than just guessing the average) to
weakly positive depending on the split — essentially no real, stable signal. Shipping it
anyway with a confident-looking number would misrepresent what the model actually knows.

**A coefficient that looked wrong on Dynasty Court, investigated rather than dismissed**:
its age coefficient came out positive (older → pricier), unlike every other estate. Dynasty
Court was built all at once (1991), so its real age range across all sales is narrow
(~27–35 years) — with limited genuine variation to learn from and only 178 rows, some
coefficient instability is plausible without meaning the whole model is broken; its overall
cross-validated accuracy (R² ≈ 0.79) remains genuinely good. Worth flagging, not worth
panicking over — the lesson from the Mei Foo Sun Chuen case in Phase 2, Stage 2 still
applies: individual coefficients can mislead even in a well-behaved model.

**What R² means here, specifically**: for each estate, that fraction of price variation
among its own real sales is explained by size, floor, and age alone. The unexplained
remainder is exactly the space this tool is built to expose as a "premium" — but see the
limitations below before treating that number as a clean measurement of subjective premium.

## Removing non-market sales

`outlier_rule.py` drops records that are not independent market sales, each with one logged
reason, before prices are index-adjusted and models fit:

1. **No exact floor** — the model needs a number.
2. **Exact duplicate** — same date, building, floor, price and area.
3. **Bulk same-day batch** — 8 or more deals in one building on one day, or 15 or more in
   one estate. These look like investor block purchases (Taikoo Shing: 24 flats on
   2025-05-27; Dynasty Court Tower 2: 11 flats on 2022-10-06), priced differently from
   ordinary resales.
4. **Price-per-sq-ft outlier** — under 0.5× or over 2.5× the median for the same estate
   within ±120 days. This catches partial-share and family transfers recorded at a fraction
   of value (for example HK$1.65M for a 760 sq ft flat). The upper bound is deliberately
   loose: the errors in this data are all on the low side, and real top-floor units sell
   far above their estate's median.

On the 1,872 rows of the four shipped estates it removed 88 (16 City One Shatin, 7 Mei Foo
Sun Chuen, 54 Taikoo Shing, 11 Dynasty Court). Limits: the rule is a heuristic, so it can
remove a genuine unusual sale and keep a subtle bad one; its thresholds were set by looking
at price-per-sq-ft patterns, including in a separate privately held sample that is not
used in training and is not part of this repository; and Repulse Bay Garden is excluded from
the rule because its 40 rows are too few for a local median.

## Affordability

`affordability.py` adds a yardstick next to the price check: how many years of household
income a flat costs.

- **Estates we model:** median index-adjusted price divided by the district's median monthly
  household income x 12 (Census & Statistics Dept table 130-06806, 2025, General Household
  Survey). Also shown after a 30% (Home Ownership Scheme) and 40% (Green Form) discount, and
  against the public rental housing income limit for 4 people. Output: `data/affordability_table.csv`.
- **Housing Authority first sales:** six Home Ownership Scheme rounds (2018-2024, about 43,000
  flats) from the Housing Authority's open data. Output: `data/hos_affordability_table.csv`,
  one row per court per round. Newly built courts come to about 7.5-8.6 years of income and
  about HK$6,900-7,500 per sq ft.

Limits, plainly:

- District median income describes everyone in the district, not buyers of a given estate. It
  is a rough yardstick, not a buyer profile. Dynasty Court (about 124 years) shows how far a
  luxury estate sits from any district median.
- HOS prices are discounted first-sale prices, not market prices, and HOS buyers face their
  own income limits, which are not modelled. They are not used to train the pricing models.
- The Housing Authority files carry no district per court, so their years-of-income figure uses
  the territory-wide median (HK$30,000 a month).
- The 2022 onwards files also include old public-rental-estate flats at about HK$0.3-0.7M.
  They are separated from new courts by the word "ESTATE" in the name, a heuristic that has
  not been checked court by court.
- Green Form (GSH) first-sale files were not found under the Housing Authority's export
  naming, so only HOS rounds are included. Home Ownership Scheme resale records are published
  as a search page with no bulk download, so they are not included either.

## Data source terms

The sold-transaction data was collected from 28hse.com with a scraper (`collect_data.py`)
before the site's Terms of Use had been read. Those terms restrict collecting, copying or
aggregating the site's information, including transaction information, by automated means,
and building an external database or tool from it. This is a real problem for the project,
not a footnote. What has been done about it: the raw saved pages and every sale-by-sale file
(raw and cleaned) were removed from this repository (they remain only on the author's own
machine), and no new data is being collected from 28hse. What has not been resolved: the
shipped models were still fitted on that data, and the removed files remain in the
repository's git history. Written permission from 28hse, or a licensed replacement source,
is the proper fix; until then the models should be read as a student portfolio prototype,
not a product. Because the data is not published, retraining from a fresh clone is not
possible; the saved models (`model.pkl`) and `data/estate_typical_flat.csv` (per-estate
medians, no individual sales) are what the app runs on.

## Limitations, stated plainly

- **Only four estates ship.** The address lookup can recognize any real Hong Kong address,
  but the app only produces an estimate for these four — everywhere else, including Repulse
  Bay Garden's own real address, it says so plainly rather than guessing. (See Future work.)
- **The "premium" is not proof of overpricing.** It's whatever the asking price isn't
  explained by area/floor/age — which includes both real subjective premium (renovation,
  staging) *and* real objective factors the model simply doesn't see (view, orientation,
  exact unit condition, stack position). The residual conflates these; it's a prompt to
  look closer, not a verdict.
- **Individual coefficients can mislead**, especially on smaller estates with narrow feature
  variation (see Dynasty Court above) — the model's actual predictions on realistic inputs
  are what's trustworthy, not any single coefficient read in isolation.
- **Accuracy varies a lot by estate** (R² from ≈0.75 to ≈0.88 among shipped estates) — Mei Foo
  Sun Chuen, with the fewest rows (241) and the widest spread of fold scores, is the least
  certain; more data and more homogeneous buildings help.
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
  chosen estate — shown as a warning rather than blocked, since the estimate becomes an
  extrapolation beyond the real training data at that point. The one exception: a
  straight-line model can extrapolate to zero or a negative price for a flat far smaller than
  any it was fit on (Dynasty Court at 500 sq ft did). If the estimate is non-positive, or under
  half the model's own estimate for the smallest, lowest flat it has seen, the app shows no
  fair value or premium and says why. The form also opens on each estate's median flat, not
  a fixed 500 sq ft.

## Scope decisions worth being upfront about

This project was deliberately narrowed and re-scoped several times during the build, and
each decision is recorded honestly here rather than smoothed over:

1. **Initial scope-down**: from an originally-envisioned 15-month, multi-feature (mapping
   APIs, gradient boosting, computer vision) vision to one estate, ≤5 features, linear
   regression only — to fit a real ~6-hours-a-week, one-semester budget.
2. **Phase 1 automation decision**: data collection was originally planned as fully manual
   (hand-copied transactions), and partway through was automated instead, after an explicit
   conversation about scope — kept bounded to a single estate rather than many districts,
   which would have been a materially riskier scraping footprint.
3. **Phase 2 scope fork**: after Phase 1 shipped, the goal of supporting "any address in Hong
   Kong" came up again — resolved not by rejecting it, but by finding a version that was
   actually achievable: free government geocoding (solving "any address" honestly) combined
   with a *small, deliberately chosen* set of estates, not every district. The harder version
   — generalizing to literally anywhere in Hong Kong with proper location modeling — remains
   explicitly out of scope (see Future work).
4. **A model-architecture correction, not a scope change**: the first attempt at combining
   estates (one shared model with estate dummy variables) was abandoned mid-build after it
   was found to badly mis-price real flats, in favor of independent per-estate models. Kept
   here as a record that not every design decision survives contact with the data — and that
   catching it mattered more than defending the original choice.
5. **Repulse Bay Garden collected but not shipped**: real data was gathered for it like any
   other estate, but its model failed the same honesty bar every other number in this project
   is held to (see Results) — excluded rather than shown with false confidence.

## Future work

A version that generalizes to *anywhere* in Hong Kong, not just a handful of chosen estates,
is a real, separate future project, not an extension bolted onto this one: it would need
real location modeling (not hand-picking estates one at a time), which is what richer
methods (mapping/places data, gradient boosting, or similar) are actually for — and a much
larger, properly scoped data collection effort. Getting Repulse Bay Garden (or any other
small estate) to a reliable sample size would also need a fundamentally different data
source, since 28hse's free history only goes back to 2018 and the estate itself only has 240
units — there may not be much more real data to collect at all, regardless of effort spent.

A larger source of transaction data would change what is possible. Centanet's public
transaction pages hold far more records than 28hse, but their terms of use have not been
confirmed and the data loads through JavaScript. An enquiry to Centaline's data bank asking
about non-commercial use was sent on 2026-10-28; until there is an answer, nothing collected from
Centanet is in this repository or in the deployed app. A private, local-only comparison
using records from Centanet's pages was run for evaluation; its raw files are git-ignored, and
the models trained on it are kept out of the app.
