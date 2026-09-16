"""
Stage 2 (automated): pull real City One Shatin sold transactions from 28hse's
public estate history pages.

What this does: fetches a fixed list of (phase, block) history pages
sequentially with pauses between requests (not hammering the site), saves the
raw HTML for each page (so results are auditable and re-parseable without
re-fetching), extracts one row per unit card, and writes a CSV.

What this does NOT do: guess or fill in any field. A row with a missing or
malformed floor/area/price/date is dropped, not estimated - see cardinal
rule #5 in the project brief (never present estimated data as real).
"""

import csv
import re
import time
import urllib.request
from pathlib import Path

ESTATE_SLUG = "city-one-shatin-4080"
BASE_URL = f"https://www.28hse.com/en/estate/detail/{ESTATE_SLUG}/history"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)
REQUEST_DELAY_SECONDS = 1.5

# Two blocks sampled from each of City One Shatin's 7 phases, so the data
# spans the estate rather than clustering in one corner of it.
PHASE_BLOCKS = [
    (1, 1), (1, 2),
    (2, 15), (2, 16),
    (3, 29), (3, 30),
    (4, 37), (4, 38),
    (5, 27), (5, 28),
    (6, 24), (6, 25),
    (7, 34), (7, 35),
]

RAW_HTML_DIR = Path("data/raw_28hse")
OUTPUT_CSV = Path("data/city_one_shatin_transactions.csv")

CARD_MARKER = 'class="ui card deal_trend_unit_card_mobile" unit-id="'
FLOOR_UNIT_RE = re.compile(r'unitRecordUrl"[^>]*>\s*([^<]+?)\s*</a>')
AREA_RE = re.compile(r'<div>(\d+)ft²</div>')
TOTAL_PRICE_RE = re.compile(r'<div>\$([\d,.]+)(M|K)?</div>')
RATE_DATE_RE = re.compile(
    r'Price:\s*@\$([\d,]+)</div><div>Date:\s*(\d{4}-\d{2}-\d{2})</div>'
)
FLOOR_RE = re.compile(r'^(\d+)/F\s*(.*)$')


def fetch_page(phase, block):
    url = f"{BASE_URL}/stateno-{phase}/blockno-{block}"
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=20) as response:
        html = response.read().decode("utf-8")
    RAW_HTML_DIR.mkdir(parents=True, exist_ok=True)
    (RAW_HTML_DIR / f"phase{phase}_block{block}.html").write_text(html, encoding="utf-8")
    return html, url


def parse_cards(html, phase, block, source_url):
    rows = []
    skipped = 0
    card_starts = [m.start() for m in re.finditer(re.escape(CARD_MARKER), html)]
    for i, start in enumerate(card_starts):
        end = card_starts[i + 1] if i + 1 < len(card_starts) else start + 3000
        chunk = html[start:end]

        floor_unit_match = FLOOR_UNIT_RE.search(chunk)
        area_match = AREA_RE.search(chunk)
        price_match = TOTAL_PRICE_RE.search(chunk)
        rate_date_match = RATE_DATE_RE.search(chunk)

        if not (floor_unit_match and area_match and price_match and rate_date_match):
            skipped += 1
            continue

        floor_match = FLOOR_RE.match(floor_unit_match.group(1).strip())
        if not floor_match:
            skipped += 1  # e.g. "G/F" or a floor range - don't guess, drop it
            continue
        floor = int(floor_match.group(1))
        unit = floor_match.group(2).strip()

        area_sqft = int(area_match.group(1))

        raw_price, suffix = price_match.groups()
        raw_price = float(raw_price.replace(",", ""))
        if suffix == "M":
            price_hkd = round(raw_price * 1_000_000)
        elif suffix == "K":
            price_hkd = round(raw_price * 1_000)
        else:
            price_hkd = round(raw_price)

        rate_per_sqft = int(rate_date_match.group(1).replace(",", ""))
        sale_date = rate_date_match.group(2)

        # Sanity check: total price should roughly equal area x rate.
        # This flags rows where the regex may have grabbed the wrong number.
        expected = area_sqft * rate_per_sqft
        pct_diff = abs(price_hkd - expected) / expected if expected else 1
        note = "" if pct_diff < 0.03 else "price/rate/area mismatch - verify"

        rows.append({
            "phase": phase,
            "block": block,
            "unit": unit,
            "floor": floor,
            "saleable_area_sqft": area_sqft,
            "price_hkd": price_hkd,
            "price_per_sqft_hkd_reference_only": rate_per_sqft,
            "sale_date": sale_date,
            "source_url": source_url,
            "notes": note,
        })
    return rows, skipped


def main():
    all_rows = []
    total_skipped = 0

    for phase, block in PHASE_BLOCKS:
        print(f"Fetching Phase {phase}, Block {block}...")
        html, url = fetch_page(phase, block)
        rows, skipped = parse_cards(html, phase, block, url)
        print(f"  -> {len(rows)} transactions parsed, {skipped} cards skipped (incomplete data)")
        all_rows.extend(rows)
        total_skipped += skipped
        time.sleep(REQUEST_DELAY_SECONDS)

    # De-duplicate in case the same unit ever appears on more than one page
    seen = set()
    deduped = []
    for row in all_rows:
        key = (row["phase"], row["block"], row["unit"], row["floor"], row["sale_date"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)

    for i, row in enumerate(deduped, start=1):
        row["transaction_id"] = i

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["transaction_id", "phase", "block", "unit", "floor",
                  "saleable_area_sqft", "price_hkd",
                  "price_per_sqft_hkd_reference_only", "sale_date",
                  "source_url", "notes"]
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(deduped)

    flagged = sum(1 for r in deduped if r["notes"])
    print(f"\nDone. {len(deduped)} unique transactions written to {OUTPUT_CSV}")
    print(f"Skipped {total_skipped} cards with incomplete data.")
    print(f"{flagged} rows flagged for a price/rate/area mismatch - worth a manual look.")


if __name__ == "__main__":
    main()
