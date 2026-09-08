"""Find the claims a label makes, in the text that is not the ingredient list."""

from __future__ import annotations

import re

from says_on_the_tin.families import FAMILIES, UNVERIFIABLE
from says_on_the_tin.models import Claim

# Prefix used for claims that no ingredient list can settle, so a caller can
# tell them apart from a family key without a second lookup.
UNVERIFIABLE_PREFIX = "unverifiable:"

_FAMILY_RES: list[tuple[str, re.Pattern[str]]] = [
    (family.key, re.compile(pattern, re.I))
    for family in FAMILIES
    for pattern in family.claim_patterns
]

_UNVERIFIABLE_RES: list[tuple[str, re.Pattern[str]]] = [
    (UNVERIFIABLE_PREFIX + entry.key, re.compile(pattern, re.I))
    for entry in UNVERIFIABLE
    for pattern in entry.patterns
]


def find(text: str) -> list[Claim]:
    """Claims found in marketing text, one per family, in order of appearance.

    A pack that says "paraben free" in the headline and "free from parabens"
    in the body has made one claim twice, not two claims, so the first
    occurrence is kept and the rest are dropped. The offset is retained so a
    caller can point at where it was said.
    """
    found: dict[str, Claim] = {}
    for key, rx in (*_FAMILY_RES, *_UNVERIFIABLE_RES):
        match = rx.search(text)
        if match is None:
            continue
        existing = found.get(key)
        if existing is None or match.start() < existing.offset:
            found[key] = Claim(
                family=key,
                text=" ".join(match.group(0).split()),
                offset=match.start(),
            )
    return sorted(found.values(), key=lambda c: (c.offset, c.family))
