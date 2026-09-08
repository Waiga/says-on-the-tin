"""Compare what a label claims against what its own ingredient list contains."""

from __future__ import annotations

from says_on_the_tin import claims as claims_mod
from says_on_the_tin import ingredients as ingredients_mod
from says_on_the_tin.families import (
    FAMILY_BY_KEY,
    Excluded,
    Member,
    UNVERIFIABLE,
)
from says_on_the_tin.models import (
    Exclusion,
    Finding,
    Ingredient,
    LabelReport,
    Match,
)

_UNVERIFIABLE_BY_KEY = {entry.key: entry for entry in UNVERIFIABLE}

_MAY_CONTAIN_CAVEAT = (
    "This appears in the 'may contain' block rather than the declared list. "
    "One such block is printed across a whole shade range, so it may or may "
    "not be in this particular product. Your filling records can settle it; "
    "the label cannot."
)


def _describe_conflict(noun: str, matches: list[Match]) -> str:
    names = ", ".join(sorted({m.ingredient.raw for m in matches}))
    return (
        f"The label claims no {noun}, and its own ingredient list contains "
        f"{names}."
    )


def _describe_review(noun: str, matches: list[Match]) -> str:
    # The per-ingredient caveats are rendered underneath each match, so
    # repeating them here produced the same paragraph twice.
    names = ", ".join(sorted({m.ingredient.raw for m in matches}))
    return (
        f"The claim about {noun} cannot be settled from the label alone. "
        f"{names} — each is explained below."
    )


def check_label(
    text: str = "",
    *,
    ingredients_text: str = "",
    claims_text: str = "",
    source: str = "",
) -> LabelReport:
    """Check one label.

    Pass either `text` (one blob containing both halves, the usual case when
    copying a product page) or the two halves separately when you have them.
    """
    limits: list[str] = []

    if ingredients_text or claims_text:
        block = ingredients_text
        marketing = claims_text
        parsed = bool(block.strip())
        if block.strip() and not ingredients_mod.looks_like_a_list(block):
            limits.append(
                "The text given as the ingredient list does not read like "
                "one. If marketing copy was passed by mistake, every result "
                "below is meaningless."
            )
    else:
        block, marketing, parsed = ingredients_mod.extract(text)

    ing: list[Ingredient] = (
        ingredients_mod.parse(block) if parsed else []
    )
    if parsed and not ing:
        parsed = False
        limits.append(
            "An ingredient heading was found but nothing could be parsed "
            "underneath it."
        )

    if not parsed:
        limits.append(
            "No ingredient list was found, so no claim below has actually "
            "been checked against anything. This is not the same as finding "
            "nothing wrong. Pass the list with --ingredients, or include an "
            "'Ingredients:' heading in the text."
        )

    found_claims = claims_mod.find(marketing)
    findings: list[Finding] = []
    exclusions: list[Exclusion] = []

    for claim in found_claims:
        if claim.family.startswith(claims_mod.UNVERIFIABLE_PREFIX):
            key = claim.family[len(claims_mod.UNVERIFIABLE_PREFIX) :]
            findings.append(
                Finding(
                    claim=claim,
                    verdict="unverifiable",
                    explanation=_UNVERIFIABLE_BY_KEY[key].explanation,
                )
            )
            continue

        family = FAMILY_BY_KEY[claim.family]

        if not parsed:
            findings.append(
                Finding(
                    claim=claim,
                    verdict="not-checked",
                    explanation=(
                        "No ingredient list was available to check this "
                        "against."
                    ),
                )
            )
            continue

        hard: list[Match] = []
        soft: list[Match] = []
        for item in ing:
            verdict = family.classify(item.normalised)
            if verdict is None:
                continue
            kind, entry = verdict
            if kind == "excluded":
                assert isinstance(entry, Excluded)
                exclusions.append(
                    Exclusion(
                        ingredient=item,
                        family=family.key,
                        reason=entry.reason,
                    )
                )
            elif kind == "member":
                assert isinstance(entry, Member)
                if item.position == "may-contain":
                    soft.append(
                        Match(item, entry.label, _MAY_CONTAIN_CAVEAT)
                    )
                else:
                    hard.append(Match(item, entry.label))
            else:
                assert isinstance(entry, Member)
                caveat = entry.caveat
                if item.position == "may-contain":
                    caveat = f"{caveat} {_MAY_CONTAIN_CAVEAT}".strip()
                soft.append(Match(item, entry.label, caveat))

        if hard:
            findings.append(
                Finding(
                    claim=claim,
                    verdict="conflict",
                    matches=hard + soft,
                    explanation=_describe_conflict(family.noun, hard),
                )
            )
        elif soft:
            findings.append(
                Finding(
                    claim=claim,
                    verdict="review",
                    matches=soft,
                    explanation=_describe_review(family.noun, soft),
                )
            )
        else:
            findings.append(
                Finding(
                    claim=claim,
                    verdict="no-conflict",
                    explanation=(
                        f"Nothing this tool recognises as {family.noun} "
                        f"appears in the ingredient list it parsed. That is "
                        f"not the same as the claim being true."
                    ),
                )
            )

    if parsed and any(i.position == "may-contain" for i in ing):
        limits.append(
            "This list has a 'may contain' colourant block. Those "
            "ingredients are shared across a shade range and may not be in "
            "this product, so matches there are reported for review rather "
            "than as contradictions."
        )

    return LabelReport(
        findings=findings,
        exclusions=exclusions,
        ingredients=ing,
        ingredients_parsed=parsed,
        limits=limits,
        source=source,
    )
