"""Find the claims a label makes.

A negation on a pack rarely governs one word. "Free from parabens, sulphates
and silicones" is a single negation and three claims, and "Paraben & sulfate
free" puts the negation at the end of the list rather than the start. An
earlier version of this module bound each negation to exactly one noun and
therefore found only one claim in each of those sentences -- reporting two
contradictions on a label that had four, which reads as a clean bill of
health on the two it never looked at. That is the failure this tool exists
to prevent, so the scanning works in both directions.
"""

from __future__ import annotations

import re

from says_on_the_tin.families import FAMILIES, UNVERIFIABLE
from says_on_the_tin.models import Claim

UNVERIFIABLE_PREFIX = "unverifiable:"

# How far a single negation is allowed to reach over a coordinated list.
# Long enough for "free from parabens, sulphates, silicones and mineral oil",
# short enough that it cannot span into an unrelated sentence.
_REACH = 140

# The negation words, in the languages that share a European pack. The
# optional colon is what "FREE FROM:" bullet panels use.
_NEGATION = re.compile(
    r"(?i)\b(?:"
    r"free[\s\-]*(?:from|of)|without|no|zero"          # English
    r"|sans"                                        # French
    r"|sin|libre[\s\-]+de"                              # Spanish
    r"|sem|livre[\s\-]+de"                              # Portuguese
    r"|senza"                                       # Italian
    r"|ohne"                                        # German
    r"|zonder"                                      # Dutch
    r"|uten"                                        # Norwegian
    r")\b[\s:\-]*"
)

# A trailing "free", as in "Paraben & sulfate free". Excludes "free from"
# and "free of", which are handled as forward negations above.
_TRAILING_FREE = re.compile(r"(?i)\b(?:free|frei|vrij|fri)\b(?!\s*(?:from|of)\b)")

# A qualifier between the negation and the noun narrows the claim to a
# subset, and reading it as absolute is wrong: "ohne rein synthetische
# Duftstoffe" is "no PURELY SYNTHETIC fragrance", and a product making
# that claim may legitimately contain a natural aroma. "No ADDED
# fragrance" is deliberately not in this set, because it does mean the
# finished product has none.
_QUALIFIER = re.compile(
    r"(?i)\b(?:synthetic|synthetische[rn]?|sintetic\w*|"
    r"synth[\u00e9e]tiques?|artificial|artificiels?|artificiale|"
    r"k[u\u00fc]nstlich\w*|purely|pure|rein)\b"
)

# Where a negation's reach stops. A full stop, a bullet, a new paragraph, or
# a word that starts a positive statement.
_STOP_AFTER = re.compile(
    r"(?i)[.!?;•]|\n\s*\n|\b(?:with|contains|enriched|made|plus|and\s+now)\b"
)
# Where a backward scan starts. Same idea, read right to left.
_STOP_BEFORE = re.compile(r"(?i)[.!?;:•]|\n\s*\n")

# Inside an ingredient panel a comma is an item separator, not a list
# conjunction, so a claim printed there governs only as far as the next one.
# Without this, "Shampooing sans silicone" followed by the panel let one
# negation reach into the ingredient list and report Ammonium Lauryl Sulfate
# as a broken silicone claim.
_STOP_AFTER_ITEM = re.compile(r"[,;.!?•\n]")
_STOP_BEFORE_ITEM = re.compile(r"[,;.!?:•\n]")

# Words that may sit between the nouns of a coordinated list without ending
# it: separators, conjunctions in the pack languages, and a few adjectives
# that do not narrow the claim.
_GAP = re.compile(
    r"(?i)(?:[\s,;/&·•+\-]|\b(?:and|or|nor|et|ni|y|e|und|of|from|"
    r"added|any|all|the|de|des|di|del)\b)+"
)

_TOKEN_RES: list[tuple[str, re.Pattern[str]]] = [
    (family.key, re.compile(r"(?i)\b(?:%s)" % "|".join(family.claim_tokens)))
    for family in FAMILIES
    if family.claim_tokens
]

# Compounded forms that carry their own negation: "Parabenfrei",
# "Parabeenvrij", "sulfate-free", "0% silicones".
_SUFFIX_RES: list[tuple[str, re.Pattern[str]]] = [
    (
        family.key,
        re.compile(
            r"(?i)\b(?:%s)[\s\-]?(?:free|frei|vrij|fri|libre)\b"
            r"|\b0\s*%%\s*(?:%s)\b"
            % ("|".join(family.claim_tokens), "|".join(family.claim_tokens))
        ),
    )
    for family in FAMILIES
    if family.claim_tokens
]

# Every family noun in one alternation, used to walk a coordinated list.
_ANY_TOKEN = re.compile(
    r"(?i)(?:%s)"
    % "|".join(
        token
        for family in FAMILIES
        for token in family.claim_tokens
    )
)


def _coordinated_prefix(span: str) -> str:
    """The leading run of `span` that is a list of family nouns.

    A negation attaches to a list, and the list ends at the first word that
    is neither one of the nouns nor something that joins them. Without this,
    "Lingettes sans rinçage parfum fruité" -- a rinse-free wipe that
    advertises a fruity scent -- read as a fragrance-free claim contradicted
    by its own Parfum, which is close to the opposite of what the pack says.
    """
    pos = 0
    while pos < len(span):
        gap = _GAP.match(span, pos)
        if gap is not None and gap.end() > pos:
            pos = gap.end()
            continue
        hit = _ANY_TOKEN.match(span, pos)
        if hit is not None and hit.end() > pos:
            pos = hit.end()
            continue
        break
    return span[:pos]


_STANDALONE_RES: list[tuple[str, re.Pattern[str]]] = [
    (family.key, re.compile(pattern, re.I))
    for family in FAMILIES
    for pattern in family.claim_patterns
]

_UNVERIFIABLE_RES: list[tuple[str, re.Pattern[str]]] = [
    (UNVERIFIABLE_PREFIX + entry.key, re.compile(pattern, re.I))
    for entry in UNVERIFIABLE
    for pattern in entry.patterns
]


def _forward_spans(
    text: str, stop_at_separator: bool
) -> list[tuple[int, int, str]]:
    """Text governed by each forward negation.

    Returns (negation start, span start, span) so a caller can quote the
    claim exactly rather than a fixed number of characters after it.
    """
    # Forward scanning does not need the comma rule: _coordinated_prefix
    # already stops at the first word that is not one of the nouns or a
    # joiner, which is more precise. Stopping at the comma cut
    # "without mineral oil, paraffin, petrolatum" after its first noun and
    # left the other two to be read as ingredients.
    del stop_at_separator
    spans = []
    for match in _NEGATION.finditer(text):
        rest = text[match.end() : match.end() + _REACH]
        stop = _STOP_AFTER.search(rest)
        span = rest[: stop.start()] if stop else rest
        spans.append((match.start(), match.end(), _coordinated_prefix(span)))
    return spans


def _backward_spans(
    text: str, stop_at_separator: bool
) -> list[tuple[int, int, str]]:
    """Text governed by each trailing "free"."""
    stopper = _STOP_BEFORE_ITEM if stop_at_separator else _STOP_BEFORE
    spans = []
    for match in _TRAILING_FREE.finditer(text):
        head = text[max(0, match.start() - _REACH) : match.start()]
        # Keep only what follows the last boundary, so that
        # "Contains silicone. Paraben free." does not read as a silicone
        # claim.
        last = None
        for boundary in stopper.finditer(head):
            last = boundary
        if last is not None:
            head = head[last.end() :]
        start = max(0, match.start() - len(head))
        spans.append((start, start, head))
    return spans


def find(text: str, *, inside_ingredient_panel: bool = False) -> list[Claim]:
    """Claims found in label text, one per family, in order of appearance.

    A pack that says "paraben free" in the headline and "free from parabens"
    in the body has made one claim twice. The first occurrence is kept and
    the offset retained so a caller can point at where it was said.
    """
    found: dict[str, Claim] = {}

    def record(key: str, offset: int, snippet: str) -> None:
        text_ = " ".join(snippet.split())[:60]
        existing = found.get(key)
        if existing is None:
            found[key] = Claim(family=key, text=text_, offset=offset)
            return
        # One claim, found more than one way. Keep the earliest position,
        # but quote the shortest wording: a reader looking for "sls-free" on
        # the pack is not helped by sixty characters of the slug it was
        # embedded in.
        found[key] = Claim(
            family=key,
            text=text_ if len(text_) < len(existing.text) else existing.text,
            offset=min(offset, existing.offset),
        )

    for key, rx in (*_STANDALONE_RES, *_UNVERIFIABLE_RES, *_SUFFIX_RES):
        match = rx.search(text)
        if match is not None:
            record(key, match.start(), match.group(0))

    spans = (
        *_forward_spans(text, inside_ingredient_panel),
        *_backward_spans(text, inside_ingredient_panel),
    )
    for start, span_start, span in spans:
        qualifier = _QUALIFIER.search(span)
        for key, token_rx in _TOKEN_RES:
            hit = token_rx.search(span)
            if hit is None:
                continue
            # A qualifier sitting BEFORE the noun narrows the claim:
            # "ohne rein synthetische Duftstoffe" permits a natural aroma.
            # A qualifier the noun pattern swallowed is part of the claim
            # itself -- "no artificial colours" is a colourant claim -- so
            # only a qualifier that starts earlier disqualifies it.
            if qualifier is not None and qualifier.start() < hit.start():
                continue
            record(key, start, text[start : span_start + hit.end()])

    return sorted(found.values(), key=lambda c: (c.offset, c.family))


def strip_claim_text(text: str) -> str:
    """Blank out claim phrases so they are not read as ingredients.

    A pack that prints "Formulated without mineral oil, paraffin, petrolatum"
    inside its ingredient panel states one claim and names three things it
    does NOT contain. Parsing that sentence as ingredients made the label
    contradict itself with its own promise, which is both wrong and exactly
    the kind of wrongness that destroys trust in a checker.

    Replacement is by spaces rather than deletion so that every offset in the
    original text still lines up.
    """
    spans: list[tuple[int, int]] = []
    for match in _NEGATION.finditer(text):
        rest = text[match.end() : match.end() + _REACH]
        stop = _STOP_AFTER.search(rest)
        governed = _coordinated_prefix(rest[: stop.start()] if stop else rest)
        if governed.strip():
            spans.append((match.start(), match.end() + len(governed)))
    for _, rx in _SUFFIX_RES:
        for match in rx.finditer(text):
            spans.append(match.span())

    if not spans:
        return text
    out = list(text)
    for start, end in spans:
        for i in range(start, min(end, len(out))):
            if out[i] not in "\n":
                out[i] = " "
    return "".join(out)
