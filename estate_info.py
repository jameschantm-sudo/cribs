"""
Shared facts about City One Shatin that both the data-cleaning script and
the Streamlit app need - kept in one place so they can't drift apart.

Source: Wikipedia (https://en.wikipedia.org/wiki/City_One), cross-checked
against 28hse's own block-to-phase grouping (they agree exactly).
"""

PHASE_COMPLETION_YEAR = {
    1: 1981,
    2: 1982,
    3: 1983,
    4: 1985,
    5: 1985,
    6: 1986,
    7: 1988,
}

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
