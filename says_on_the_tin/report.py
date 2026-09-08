"""Render a label report.

The text form is written to be pasted into an email to whoever can act on it
-- a packaging designer, a contract manufacturer, a marketplace team -- so it
leads with the contradictions, quotes the label's own words back, and ends by
saying plainly what was not checked.
"""

from __future__ import annotations

import json

from says_on_the_tin import __version__
from says_on_the_tin.families import FAMILIES, FAMILY_BY_KEY
from says_on_the_tin.models import Finding, LabelReport


def _ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _where(finding: Finding, total: int) -> list[str]:
    lines = []
    for match in finding.matches:
        item = match.ingredient
        place = (
            f"{_ordinal(item.index)} in the 'may contain' block"
            if item.position == "may-contain"
            else f"{_ordinal(item.index)} of {total} in the list"
        )
        lines.append(f"      {item.raw} — {match.member}, {place}")
        if match.caveat:
            lines.extend(_wrap(match.caveat, "        "))
    return lines


def _wrap(
    text: str, indent: str, width: int = 78, hang: str | None = None
) -> list[str]:
    """Wrap to `width`, indenting continuation lines by `hang`.

    Without a hanging indent, a wrapped bullet's second line starts level
    with the bullet itself and stops looking like one item.
    """
    words = text.split()
    lines: list[str] = []
    continuation = indent if hang is None else hang
    current = indent
    for word in words:
        if len(current) + len(word) + 1 > width and current.strip():
            lines.append(current.rstrip())
            current = continuation
        current += word + " "
    if current.strip():
        lines.append(current.rstrip())
    return lines


def _headline(report: LabelReport) -> str:
    conflicts = len(report.conflicts)
    reviews = len(report.reviews)
    unverifiable = sum(
        1 for f in report.findings if f.verdict == "unverifiable"
    )
    not_checked = sum(1 for f in report.findings if f.verdict == "not-checked")

    if not report.findings:
        return "No claims of a kind this tool checks were found on this label."

    bits = []
    if conflicts:
        bits.append(
            f"{conflicts} contradiction{'s' if conflicts != 1 else ''}"
        )
    if reviews:
        bits.append(f"{reviews} to review")
    if not_checked:
        bits.append(f"{not_checked} not checked")
    if unverifiable:
        bits.append(
            f"{unverifiable} claim{'s' if unverifiable != 1 else ''} no "
            "ingredient list can settle"
        )
    if not bits:
        return (
            "No contradiction found between the claims on this label and its "
            "own ingredient list."
        )
    return ", ".join(bits) + "."


def render_text(report: LabelReport) -> str:
    total = sum(1 for i in report.ingredients if i.position == "declared")
    out: list[str] = []
    title = report.source or "label"
    out.append(f"says-on-the-tin {__version__} — {title}")
    out.append("")
    out.extend(_wrap(_headline(report), ""))
    out.append("")

    groups = (
        ("conflict", "CONTRADICTIONS", 
         "The label makes these claims, and its own ingredient list breaks "
         "them."),
        ("review", "WORTH A LOOK",
         "Something was found whose status a person has to settle. Each one "
         "says why."),
        ("not-checked", "NOT CHECKED",
         "These claims were found but there was no ingredient list to check "
         "them against."),
        ("unverifiable", "CANNOT BE CHECKED FROM AN INGREDIENT LIST",
         "These claims are about testing, certification or sourcing. Nothing "
         "in an ingredient list can confirm or contradict them, so this tool "
         "reports them rather than passing over them in silence."),
        ("no-conflict", "NOTHING MATCHED",
         "Nothing this tool recognises turned up against these claims. Read "
         "that as what it says, not as confirmation the claim is true."),
    )

    for verdict, heading, blurb in groups:
        items = [f for f in report.findings if f.verdict == verdict]
        if not items:
            continue
        out.append(heading)
        out.extend(_wrap(blurb, "  "))
        out.append("")
        for finding in items:
            out.append(f'  "{finding.claim.text}"')
            if verdict == "no-conflict":
                out.append("")
                continue
            out.extend(_wrap(finding.explanation, "    "))
            if finding.matches:
                out.extend(_where(finding, total))
            out.append("")

    if report.exclusions:
        out.append("CONSIDERED AND NOT COUNTED")
        out.extend(_wrap(
            "These ingredients look like they break a claim above and do "
            "not. They are listed so you can see the tool noticed them.",
            "  "))
        out.append("")
        for exclusion in report.exclusions:
            out.append(f"  {exclusion.ingredient.raw}")
            out.extend(_wrap(exclusion.reason, "    "))
        out.append("")

    out.append("WHAT THIS DID NOT CHECK")
    for limit in report.limits:
        out.extend(_wrap("- " + limit, "  ", hang="    "))
    out.extend(_wrap(
        f"- Only the {len(FAMILIES)} claim families this tool knows about "
        "were compared, against ingredient names it recognises. An "
        "ingredient it has never heard of cannot break a claim it cannot "
        "see.", "  ", hang="    "))
    out.extend(_wrap(
        "- Nothing here is a statement about whether this product is legal "
        "to sell, safe, or acceptable to any particular retailer. This tool "
        "compares two halves of one document and reports where they "
        "disagree.", "  ", hang="    "))
    out.append("")
    return "\n".join(out)


def render_markdown(report: LabelReport) -> str:
    total = sum(1 for i in report.ingredients if i.position == "declared")
    out: list[str] = [f"# {report.source or 'Label check'}", ""]
    out.append(_headline(report))
    out.append("")
    for verdict, heading in (
        ("conflict", "Contradictions"),
        ("review", "Worth a look"),
        ("not-checked", "Not checked"),
        ("unverifiable", "Cannot be checked from an ingredient list"),
        ("no-conflict", "Nothing matched"),
    ):
        items = [f for f in report.findings if f.verdict == verdict]
        if not items:
            continue
        out.append(f"## {heading}")
        out.append("")
        for finding in items:
            out.append(f"**“{finding.claim.text}”**")
            out.append("")
            if finding.explanation and verdict != "no-conflict":
                out.append(finding.explanation)
                out.append("")
            for match in finding.matches:
                item = match.ingredient
                place = (
                    "'may contain' block"
                    if item.position == "may-contain"
                    else f"{_ordinal(item.index)} of {total}"
                )
                out.append(f"- `{item.raw}` — {match.member}, {place}")
                if match.caveat:
                    out.append(f"  - {match.caveat}")
            out.append("")
    if report.exclusions:
        out.append("## Considered and not counted")
        out.append("")
        for exclusion in report.exclusions:
            out.append(f"- `{exclusion.ingredient.raw}` — {exclusion.reason}")
        out.append("")
    out.append("## What this did not check")
    out.append("")
    for limit in report.limits:
        out.append(f"- {limit}")
    out.append(
        f"- Only the {len(FAMILIES)} claim families this tool knows about "
        "were compared."
    )
    out.append(
        "- Nothing here says whether this product is legal, safe, or "
        "acceptable to a retailer."
    )
    out.append("")
    return "\n".join(out)


def render_json(report: LabelReport) -> str:
    return json.dumps(
        {
            "tool": "says-on-the-tin",
            "version": __version__,
            "source": report.source,
            "ingredients_parsed": report.ingredients_parsed,
            "ingredient_count": len(report.ingredients),
            "findings": [
                {
                    "claim": finding.claim.text,
                    "family": finding.claim.family,
                    "verdict": finding.verdict,
                    "explanation": finding.explanation,
                    "matches": [
                        {
                            "ingredient": m.ingredient.raw,
                            "normalised": m.ingredient.normalised,
                            "index": m.ingredient.index,
                            "position": m.ingredient.position,
                            "member": m.member,
                            "caveat": m.caveat,
                        }
                        for m in finding.matches
                    ],
                }
                for finding in report.findings
            ],
            "considered_and_not_counted": [
                {
                    "ingredient": e.ingredient.raw,
                    "family": e.family,
                    "reason": e.reason,
                }
                for e in report.exclusions
            ],
            "limits": report.limits,
        },
        indent=2,
    )


def render_families() -> str:
    """Everything the tool knows, so a reader can judge it before trusting it."""
    out: list[str] = [
        f"says-on-the-tin {__version__} knows {len(FAMILIES)} claim families.",
        "",
    ]
    for family in FAMILIES:
        out.append(f"{family.key} — {family.noun}")
        out.append(f"  breaks the claim: {len(family.members)} pattern(s)")
        if family.disputed:
            out.append(f"  needs review:     {len(family.disputed)} pattern(s)")
        if family.excluded:
            out.append(
                f"  deliberately not counted: "
                f"{len(family.excluded)} pattern(s)"
            )
        if family.note:
            out.extend(_wrap(family.note, "  "))
        out.append("")
    return "\n".join(out)
