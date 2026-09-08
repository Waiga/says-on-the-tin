# Limitations

The short version is in the README. This is the detail, for anyone deciding
how far to trust a result.

## The tool answers one question only

*Does this label's own ingredient list contradict a claim printed on the same
label?*

It does not answer, and cannot answer:

- Is this product legal to sell in the EU, US, UK or India?
- Is it safe?
- Will a retailer accept it?
- Is the claim substantiated?
- Is the ingredient list itself complete or correct?

Those need a regulatory adviser, a lab, or the retailer. The reason the tool
is worth anything is that it is honest about the one question it does answer.

## Absent is not unknown

The distinction the whole design rests on. Three different situations that a
careless tool would report identically:

| Situation | What it reports |
|---|---|
| Claim made, list parsed, nothing matched | `no-conflict` |
| Claim made, no ingredient list found | `not-checked`, plus a stated limit |
| Claim made, list parsed, match found | `conflict` or `review` |

A run with no ingredient list produces **no** `no-conflict` results at all.
It cannot: nothing was compared. The report says so in words, at the top and
in the closing section.

## Where a false negative can come from

A false negative — the tool says nothing and the label really does contradict
itself — is the failure that matters, because it can be read as reassurance.
The known routes:

1. **An ingredient name the family patterns do not cover.** The families are
   pattern-based, not a complete INCI dictionary. There is no redistributable
   machine-readable INCI dictionary; the PCPC one is proprietary.
2. **A claim phrasing not recognised.** Detection covers English, French,
   Spanish, Portuguese, Italian, German, Dutch and Norwegian negation forms.
   Anything else is missed silently.
3. **An ingredient list the extractor could not find.** Without an
   `Ingredients:`-style heading in one of the languages it knows, the text is
   treated as marketing copy and nothing is checked — but this case is
   reported as `not-checked`, not as a pass.
4. **A truncated list.** If a pack panel is cut off mid-list, the tool checks
   what it was given and has no way to know the rest existed.

## Where a review, rather than a contradiction, is the honest answer

Several things genuinely cannot be settled from a pack:

- **Sourcing.** Squalane is the same molecule from a shark or an olive.
  Stearic acid, glycerin and hyaluronic acid are the same INCI name whatever
  they came from.
- **Grade.** Hydrolysed wheat protein under a gluten-free claim depends on a
  gluten content the pack does not state.
- **Formaldehyde releasers.** DMDM Hydantoin is not formaldehyde, but it
  releases it. Whether that breaks a "formaldehyde-free" claim is a
  long-standing industry argument.
- **Undisclosed fragrance.** "Parfum" may lawfully stand for a mixture, so a
  phthalate-free claim over it rests on the fragrance house's statement, not
  on the label.
- **`may contain` colourants.** One block is printed across a whole shade
  range.

The tool surfaces all of these rather than deciding them.

## Claims it will never check

`cruelty-free`, `dermatologically tested`, `clinically proven`,
`hypoallergenic`, `non-comedogenic`, `organic`, `natural`, `clean`, and
`chemical-free` are reported as unverifiable with a reason. They are about
testing, certification or marketing vocabulary, and no ingredient list bears
on them.

`chemical-free` is a special case: it cannot be true of any cosmetic, water
included. The European Commission's Technical Document on Cosmetic Claims
addresses this class of claim under the common criteria in Regulation (EU)
655/2013. Whether the phrase is permissible where you sell is a question for
a regulatory adviser.

## Data and licensing

The tool bundles no third-party data. The claim families are written from
public chemistry and published industry convention, in `families.py`, with
the reasoning next to each entry so it can be argued with.

The 2,554-label corpus used for measurement is an Open Beauty Facts export.
That database is ODbL 1.0 — attribution and share-alike — which is
incompatible with redistributing a filtered subset inside an MIT repository.
The corpus is therefore not included here; only the measurements are.
