"""
Stage 2 (Phase 2: multi-estate) - pull real sold transactions from 28hse's
public estate history pages, for every estate configured in estate_info.py.

Same method as the original single-estate version: fetch each sampled
(phase, block) page sequentially with pauses between requests, save the raw
HTML as an audit trail, extract one row per unit card, and never guess a
missing field - drop the row instead.
"""

import csv
import re
import time
import urllib.request
from pathlib import Path

from estate_info import ESTATES

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)
REQUEST_DELAY_SECONDS = 1.5

RAW_HTML_DIR = Path("data/raw_28hse")
OUTPUT_CSV = Path("data/all_estates_transactions.csv")

CARD_MARKER = 'class="ui card deal_trend_unit_card_mobile" unit-id="'
FLOOR_UNIT_RE = re.compile(r'unitRecordUrl"[^>]*>\s*([^<]+?)\s*</a>')
AREA_RE = re.compile(r'<div>(\d+)ft²</div>')
TOTAL_PRICE_RE = re.compile(r'<div>\$([\d,.]+)(M|K)?</div>')
RATE_DATE_RE = re.compile(
    r'Price:\s*@\$([\d,]+)</div><div>Date:\s*(\d{4}-\d{2}-\d{2})</div>'
)
FLOOR_RE = re.compile(r'^(\d+)/F\s*(.*)$')


def fetch_page(slug, phase, block):
    url = f"https://www.28hse.com/en/estate/detail/{slug}/history/stateno-{phase}/blockno-{block}"
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=20) as response:
        html = response.read().decode("utf-8")
    RAW_HTML_DIR.mkdir(parents=True, exist_ok=True)
    (RAW_HTML_DIR / f"{slug}_phase{phase}_block{block}.html").write_text(html, encoding="utf-8")
    return html, url


def parse_cards(html, estate_key, phase, block, source_url):
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
            skipped += 1
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

        expected = area_sqft * rate_per_sqft
        pct_diff = abs(price_hkd - expected) / expected if expected else 1
        note = "" if pct_diff < 0.03 else "price/rate/area mismatch - verify"

        rows.append({
            "estate": estate_key,
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


def collect_estate(estate_key):
    config = ESTATES[estate_key]
    all_rows = []
    total_skipped = 0
    for phase, block in config["sample_phase_blocks"]:
        print(f"  Fetching {config['name']} Phase {phase}, Block {block}...")
        html, url = fetch_page(config["slug"], phase, block)
        rows, skipped = parse_cards(html, estate_key, phase, block, url)
        print(f"    -> {len(rows)} transactions parsed, {skipped} cards skipped")
        all_rows.extend(rows)
        total_skipped += skipped
        time.sleep(REQUEST_DELAY_SECONDS)
    return all_rows, total_skipped


def main(estate_keys=None):
    estate_keys = estate_keys or list(ESTATES.keys())
    all_rows = []
    total_skipped = 0

    for estate_key in estate_keys:
        print(f"Collecting {ESTATES[estate_key]['name']}...")
        rows, skipped = collect_estate(estate_key)
        all_rows.extend(rows)
        total_skipped += skipped

    seen = set()
    deduped = []
    for row in all_rows:
        key = (row["estate"], row["phase"], row["block"], row["unit"], row["floor"], row["sale_date"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)

    for i, row in enumerate(deduped, start=1):
        row["transaction_id"] = i

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["transaction_id", "estate", "phase", "block", "unit", "floor",
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
