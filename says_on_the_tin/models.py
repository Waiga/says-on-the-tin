from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


# What this tool concluded about one claim it found on the label.
#
# There is deliberately no "true" or "compliant". The tool compares two halves
# of the same document and reports where they disagree. Whether a claim is
# lawful, substantiated, or acceptable to a particular retailer is not
# something an ingredient list can answer, and this tool does not pretend it
# can.
#
#   conflict    the claim is made and the ingredient list contains something
#               this tool recognises as a member of the family the claim
#               excludes. This is a statement about two strings in one
#               document, not a legal conclusion.
#   review      something was found whose membership is genuinely contested,
#               conditional, or depends on sourcing the label does not state.
#               A person has to settle it.
#   no-conflict the claim is made and nothing matched. Read this as "nothing
#               matched among the ingredients that were parsed and are known
#               to this tool" -- never as "the claim is true".
#   unverifiable the claim cannot be settled from an ingredient list at all,
#               whatever it contains. "Cruelty-free" is about testing policy;
#               "dermatologically tested" is about a study.
#   not-checked  the claim was found but no ingredient list was available to
#               check it against. Distinct from no-conflict, and the
#               distinction is the whole point: not looking is not the same
#               as looking and finding nothing.
Verdict = Literal[
    "conflict", "review", "no-conflict", "unverifiable", "not-checked"
]

# Where an ingredient sits in the list. A colourant in a shared "may contain"
# block may or may not be in the tub in your hand, so a match there can never
# be reported at the same strength as a match in the declared list.
Position = Literal["declared", "may-contain"]


@dataclass(frozen=True)
class Ingredient:
    """One entry parsed out of an ingredient list."""

    # As printed, minus footnote marks and percentage annotations.
    raw: str
    # Casefolded, whitespace-collapsed, British/American spelling unified.
    normalised: str
    # 1-based index within its section, for "the third ingredient" reporting.
    index: int
    position: Position = "declared"


@dataclass(frozen=True)
class Claim:
    """A claim found in the marketing text."""

    # The family this claim excludes, or the pseudo-family for claims that no
    # ingredient list can settle.
    family: str
    # Exactly as it appeared on the label, so the reader can find it.
    text: str
    # Character offset in the source, for tooling.
    offset: int


@dataclass(frozen=True)
class Match:
    """An ingredient that bears on a claim."""

    ingredient: Ingredient
    # Why this ingredient counts: the family member pattern it matched.
    member: str
    # Present when the match is contested rather than clear-cut.
    caveat: str = ""


@dataclass(frozen=True)
class Finding:
    claim: Claim
    verdict: Verdict
    matches: list[Match] = field(default_factory=list)
    # Plain-English explanation, always populated. For a conflict it says what
    # was found; for a review it says what a person must decide; for
    # unverifiable it says why no ingredient list can answer.
    explanation: str = ""


@dataclass(frozen=True)
class Exclusion:
    """An ingredient this tool saw, considered, and deliberately did not count.

    Reported so that a reader can tell the difference between "the tool did
    not notice Cetearyl Alcohol" and "the tool noticed it and knows it is a
    waxy emollient rather than the volatile alcohol an alcohol-free claim is
    about". Silence about a near-miss reads as an oversight; saying it out
    loud is what makes the absence of a finding worth anything.
    """

    ingredient: Ingredient
    family: str
    reason: str


@dataclass(frozen=True)
class LabelReport:
    findings: list[Finding]
    exclusions: list[Exclusion]
    ingredients: list[Ingredient]
    # True when an ingredient list was located and parsed. When False, every
    # finding is "not-checked" and no absence may be reported.
    ingredients_parsed: bool
    # Things that limit what the run could conclude, in the reader's words.
    limits: list[str] = field(default_factory=list)
    source: str = ""

    @property
    def conflicts(self) -> list[Finding]:
        return [f for f in self.findings if f.verdict == "conflict"]

    @property
    def reviews(self) -> list[Finding]:
        return [f for f in self.findings if f.verdict == "review"]
