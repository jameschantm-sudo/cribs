"""
Reference data for every estate this project covers. One entry per estate:
- slug: the estate's identifier in 28hse's URLs
- district: the real Hong Kong district (from the government Address Lookup
  Service), used to match a geocoded address to an estate we have data for
- phase_completion_year: {stateno on 28hse: real construction-completion year}
- sample_phase_blocks: (stateno, blockno) pairs sampled when scraping -
  2 per phase, spread across the estate rather than clustered in one part
  of it

Sources: Wikipedia and 28hse's own per-phase estate pages (both agree where
checked), same approach used for City One Shatin in Stage 3.
"""

ESTATES = {
    "city_one_shatin": {
        "name": "City One Shatin",
        "slug": "city-one-shatin-4080",
        "district": "SHA TIN DISTRICT",
        "index_column": "Class B New Territories",
        "phase_completion_year": {1: 1981, 2: 1982, 3: 1983, 4: 1985, 5: 1985, 6: 1986, 7: 1988},
        "sample_phase_blocks": [
            (1, 1), (1, 2), (2, 15), (2, 16), (3, 29), (3, 30), (4, 37), (4, 38),
            (5, 27), (5, 28), (6, 24), (6, 25), (7, 34), (7, 35),
        ],
    },
    "taikoo_shing": {
        "name": "Taikoo Shing",
        "slug": "taikoo-shing-1140",
        "district": "EASTERN DISTRICT",
        "index_column": "Class B Hong Kong",
        "phase_completion_year": {1: 1980, 2: 1980, 3: 1983, 4: 1989, 5: 1983, 6: 1977, 7: 1976, 8: 1985},
        "sample_phase_blocks": [
            (1, 18), (1, 31), (2, 1), (2, 7), (3, 3), (3, 11), (4, 14), (4, 16),
            (5, 12), (5, 13), (6, 2), (6, 6), (7, 4), (7, 23), (8, 5), (8, 9),
        ],
    },
    "mei_foo_sun_chuen": {
        "name": "Mei Foo Sun Chuen",
        "slug": "mei-foo-sun-chuen-2520",
        "district": "SHAM SHUI PO DISTRICT",
        "index_column": "Class B Kowloon",
        "phase_completion_year": {1: 1968, 2: 1971, 3: 1972, 4: 1973, 5: 1972, 6: 1974, 7: 1976, 8: 1978},
        "sample_phase_blocks": [
            (1, 1), (1, 2), (2, 28), (2, 29), (3, 56), (3, 57), (4, 92), (4, 93),
            (5, 116), (5, 117), (6, 139), (6, 140), (7, 164), (7, 165), (8, 176), (8, 177),
        ],
    },
}


# --- Backwards-compatible helpers for City One Shatin, used by app.py ---
# (Superseded once app.py is updated for multi-estate support in a later stage.)

PHASE_COMPLETION_YEAR = ESTATES["city_one_shatin"]["phase_completion_year"]

PHASE_BLOCK_RANGES = {
    1: range(1, 15),
    2: range(15, 24),
    3: range(29, 34),
    4: range(37, 46),
    5: list(range(27, 29)) + list(range(46, 53)),
    6: range(24, 27),
    7: range(34, 37),
}


def block_to_phase(block):
    for phase, blocks in PHASE_BLOCK_RANGES.items():
        if block in blocks:
            return phase
    raise ValueError(f"Block {block} isn't a real City One Shatin block (1-52).")


def completion_year(block):
    return PHASE_COMPLETION_YEAR[block_to_phase(block)]


ALL_BLOCKS = sorted(
    block
    for blocks in PHASE_BLOCK_RANGES.values()
    for block in blocks
)
