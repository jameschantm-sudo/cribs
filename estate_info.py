"""
Reference data for every estate this project covers.

ESTATES holds what Stage 2 (data collection) and Stage 3 (cleaning) need per
estate: its 28hse slug, real district, the correct RVD index column for its
region, real per-phase completion years, and which (phase, block) pairs got
sampled for training data.

BLOCK_LOOKUP holds what the app needs to let someone pick *any* real block
in an estate (not just the ones we scraped) and get a correct age for it -
every block only needs to know its own phase, since age is derived from the
phase's completion year, not from having transaction data for that specific
block.

Sources: Wikipedia and 28hse's own per-phase estate pages (both agree where
checked).
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

# Real observed range in the training data (data/all_estates_modeling_ready.csv)
# - used only to warn when an app input falls outside what the model actually
# learned from for that estate, per the Phase 2 age-extrapolation lesson.
OBSERVED_RANGES = {
    "city_one_shatin": {"area": (284, 853), "floor": (1, 36)},
    "taikoo_shing": {"area": (440, 922), "floor": (1, 30)},
    "mei_foo_sun_chuen": {"area": (437, 927), "floor": (1, 20)},
}

# City One Shatin: 52 blocks, numbered contiguously by phase.
_CITY_ONE_RANGES = {
    1: range(1, 15), 2: range(15, 24), 3: range(29, 34), 4: range(37, 46),
    5: list(range(27, 29)) + list(range(46, 53)), 6: range(24, 27), 7: range(34, 37),
}

# Mei Foo Sun Chuen: 195 numbered blocks (28hse's own numbering - finer-
# grained than the "99 blocks" usually quoted for the estate, but each
# number is a real, individually addressable building), contiguous by phase.
_MEI_FOO_RANGES = {
    1: range(1, 28), 2: range(28, 56), 3: range(56, 92), 4: range(92, 116),
    5: range(116, 139), 6: range(139, 164), 7: range(164, 176), 8: range(176, 196),
}

# Taikoo Shing: 61 named buildings, NOT numbered contiguously - each one
# needs its own explicit (phase, name) entry.
_TAIKOO_SHING_BLOCKS = {
    18: (1, 'Kin On'), 31: (1, 'Ko On'), 43: (1, 'Shun On'), 44: (1, 'Ning On'),
    57: (1, 'Hing On'), 60: (1, 'Po On'),
    1: (2, 'Yuan Kung'), 7: (2, 'Ming Kung'), 25: (2, 'Tang Kung'), 26: (2, 'Hsia Kung'),
    41: (2, 'Tsui Kung'), 45: (2, 'Han Kung'), 52: (2, 'Chai Kung'), 55: (2, 'Yen Kung'),
    3: (3, 'Tien Sing'), 11: (3, 'Kam Sing'), 21: (3, 'Hang Sing'), 29: (3, 'Hoi Sing'),
    37: (3, 'Chi Sing'), 49: (3, 'Ngan Sing'), 53: (3, 'Wai Sing'), 61: (3, 'Yiu Sing'),
    14: (4, 'Kwun Tien'), 16: (4, 'Nam Tien'), 20: (4, 'Heng Tien'), 28: (4, 'Hoi Tien'),
    32: (4, 'Choi Tien'), 33: (4, 'Kai Tien'), 35: (4, 'Fu Tien'), 36: (4, 'King Tien'), 40: (4, 'Yat Tien'),
    12: (5, 'Maple'), 13: (5, 'Pine'), 22: (5, 'Primrose'), 24: (5, 'Marigold'),
    30: (5, 'Begonia'), 38: (5, 'Oak'), 46: (5, 'Wisteria'), 47: (5, 'Willow'),
    48: (5, 'Banyan'), 50: (5, 'Juniper'), 62: (5, 'Lotus'),
    2: (6, 'Tien Shan'), 6: (6, 'Yee Shan'), 8: (6, 'Tung Shan'), 10: (6, 'Kam Shan'),
    15: (6, 'Nan Shan'), 19: (6, 'Heng Shan'), 27: (6, 'Tai Shan'), 34: (6, 'Fu Shan'),
    39: (6, 'Wah Shan'), 51: (6, 'Foong Shan'), 56: (6, 'Lu Shan'), 58: (6, 'Loong Shan'), 59: (6, 'Po Shan'),
    4: (7, 'Tai Woo'), 23: (7, 'Tung Ting'), 54: (7, 'Poyang'),
    5: (8, 'Pak Hoi'), 9: (8, 'Tung Hoi'), 17: (8, 'Nam Hoi'),
}


def _build_block_lookup():
    """{estate_key: {block_no: (phase, display_name)}} for every real block."""
    lookup = {"taikoo_shing": _TAIKOO_SHING_BLOCKS}
    for estate_key, ranges in [("city_one_shatin", _CITY_ONE_RANGES), ("mei_foo_sun_chuen", _MEI_FOO_RANGES)]:
        lookup[estate_key] = {
            block: (phase, f"Block {block}")
            for phase, blocks in ranges.items()
            for block in blocks
        }
    return lookup


BLOCK_LOOKUP = _build_block_lookup()


def blocks_for(estate_key):
    """Sorted list of every real block number in an estate."""
    return sorted(BLOCK_LOOKUP[estate_key])


def block_label(estate_key, block):
    """Human-readable label for a block, e.g. 'Kin On' or 'Block 15'."""
    return BLOCK_LOOKUP[estate_key][block][1]


def completion_year(estate_key, block):
    phase = BLOCK_LOOKUP[estate_key][block][0]
    return ESTATES[estate_key]["phase_completion_year"][phase]
