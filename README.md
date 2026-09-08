# says-on-the-tin

Finds where a cosmetic label contradicts itself: a free-from claim on the
front, and an ingredient on the back that breaks it.

Runs entirely on your machine. No account, no upload, no network access, no
dependencies beyond Python itself.

```
$ says-on-the-tin shampoo-label.txt

says-on-the-tin 0.1.0 — shampoo-label.txt

3 contradictions, 1 to review, 2 claims no ingredient list can settle.

CONTRADICTIONS
  The label makes these claims, and its own ingredient list breaks them.

  "SULFATE FREE"
    The label claims no cleansing sulfates, and its own ingredient list
    contains Sodium Laureth Sulfate.
      Sodium Laureth Sulfate — a sulfate surfactant, 2nd of 12 in the list

  "paraben-free"
    The label claims no parabens, and its own ingredient list contains
    Methylparaben.
      Methylparaben — a paraben, 9th of 12 in the list
```

## What it does not do

It never says a product is compliant, clean, safe, or legal to sell. It
compares two halves of one document and reports where they disagree. Whether
a claim is lawful where you sell, substantiated, or acceptable to a
particular retailer is not something an ingredient list can answer, and this
tool does not pretend otherwise.

That is not modesty. It is the only claim the evidence supports.

## Install

```
pip install .
```

Python 3.11 or newer. Nothing else.

## Use

```
says-on-the-tin label.txt              # marketing copy and list in one file
cat product-page.txt | says-on-the-tin -
says-on-the-tin --ingredients inci.txt --claims copy.txt
says-on-the-tin label.txt --format markdown   # to paste into an email
says-on-the-tin label.txt --format json       # for a pipeline
says-on-the-tin --list-families               # everything it knows
```

Exit codes: `0` nothing contradicted, `1` at least one contradiction, `2`
could not run. So it works as a check in CI over your label copy.

## The five things it can say about a claim

| | |
|---|---|
| **conflict** | The claim is made and the ingredient list contains something the tool recognises as breaking it. |
| **review** | Something was found whose status is genuinely contested, conditional, or depends on sourcing the label does not state. A person has to settle it. |
| **no-conflict** | The claim is made and nothing matched. Read that as *nothing matched among the ingredients parsed and known to this tool* — never as the claim being true. |
| **unverifiable** | The claim cannot be settled from an ingredient list at all. "Cruelty-free" is about testing policy. "Dermatologically tested" is about a study. |
| **not-checked** | The claim was found but there was no ingredient list to check it against. This is deliberately not the same as no-conflict. |

## What makes it worth trusting: the things it refuses to flag

A checker that flags Cetearyl Alcohol under an "alcohol-free" claim is wrong,
and one wrong flag is enough for a formulator to close it and never open it
again. So the tool carries an explicit list of look-alikes, each with the
reason, and it **reports what it deliberately did not count** rather than
dropping it silently:

```
CONSIDERED AND NOT COUNTED
  These ingredients look like they break a claim above and do not. They are
  listed so you can see the tool noticed them.

  Magnesium Sulfate
    an inorganic or polysaccharide sulfate salt, not a cleansing surfactant.
    'Sulfate-free' is a claim about detergents such as SLS and SLES;
    Magnesium Sulfate is Epsom salt.
  Cetearyl Alcohol
    a fatty alcohol. These are waxy emollients and thickeners that soften
    skin; they are the opposite of the drying, volatile alcohol an
    alcohol-free claim is about. This is the most common false alarm in
    ingredient checking.
```

Silence about a near-miss reads as an oversight. Saying it out loud is what
makes the absence of a finding worth anything.

Other look-alikes it knows: silica and silicates are not silicones. Sodium
Lauryl Sulfoacetate is not a sulfate. Lactic acid is not from milk. Zea Mays
Silk is corn, not silk. An ingredient whose own name says "Vegan Collagen"
has already answered the question.

## Measured against real labels

Unit tests pass on the inputs their author imagined. That proves very little,
so this was run over **2,554 real published cosmetic labels** taken from a
public Open Beauty Facts export — real packs, real messiness, none of it
written by this project.

| | |
|---|---|
| Labels processed | 2,554 |
| Crashes | 0 |
| Ingredient lists parsed | 2,554 of 2,554 |
| Individual ingredients parsed | 55,604 |
| Claims found | 3,289 |
| …that no ingredient list can settle | 577 (17.5% of 3,289) |
| **Contradictions** | **51, across 46 products** (1.8% of 2,554 labels) |
| Sent for review | 82 |
| Known false-positive cases wrongly flagged | **0 of 14** |

Those 14 are cases an earlier, independent pass over the same corpus had
itself identified as things that must *not* be called contradictions — Epsom
salt under sulfate-free, fatty alcohols and benzyl alcohol under
alcohol-free. None of them is reported as a contradiction here.

### What the measurement found that the tests did not

Every one of these was a real defect, found only by meeting real labels:

- **Claim detection was English-only.** Every single contradiction in the
  sample was tagged in Portuguese, French, German, Italian or Dutch. An
  English-only pass found none of them. The tool now reads `sem parabenos`,
  `sans paraben`, `sin parabenos`, `ohne Parabene`, `senza parabeni`,
  `Parabeenvrij` and `Parabenfrei`.
- **`Parfum (Fragrance)` is the most common printed form** of the fragrance
  entry, and an exact-match pattern missed all of it — 20 real
  contradictions.
- **Glycerin and stearic acid buried everything.** Both are sourcing-ambiguous
  under a vegan claim, and flagging them produced 524 of 538 review findings.
  Technically defensible, practically useless. They are now listed as
  considered-and-not-counted.
- **Wheat derivatives under a gluten-free claim are contested, not
  clear-cut.** Treating them as contradictions produced 19 findings against
  hydrolysed wheat protein, which is not the same thing as gluten. They are
  reviews now.
- **Brands print the claim inside the ingredient panel** — `SANS PARABEN`
  closing a French list. Counted as an ingredient, it inflated paraben
  findings from 5 to 16.
- **`Sodium Caseinate`** was missed by a word-boundary pattern on `casein`.
- **A member pattern broad enough to include `coco`** shadowed the disputed
  entry for Sodium Coco-Sulfate, turning a judgement call into a false
  accusation.

The corpus itself is not redistributed here: Open Beauty Facts is ODbL, which
is share-alike and incompatible with this repository's MIT licence. Only the
measurements are published.

## What it misses

Stated plainly, because a checking tool that hides its blind spots is worse
than none.

- **It only knows the claim families in `--list-families`.** An ingredient it
  has never heard of cannot break a claim it cannot see.
- **A `no-conflict` is not a pass.** It means nothing matched, over the part
  of the label that parsed, among the names the tool knows.
- **Claims in languages beyond the ones listed above are not detected.**
  A pack in Polish, Japanese or Hindi will report far fewer claims than it
  makes, and the tool will not tell you it is under-reading them.
- **It cannot see concentration.** Retailer and regulatory limits are
  frequently expressed in ppm, and an ingredient list does not carry
  concentrations.
- **It cannot see impurities.** 1,4-dioxane in an ethoxylate, or asbestos in
  talc, are lab questions, not label questions.
- **`may contain` colourants** are shared across a shade range, so a match
  there is always a review, never a contradiction.
- **Crowd-sourced label data can be wrong.** In the measurement above, a
  "contradiction" may be a mislabelled record rather than a mislabelled pack.
  The tool reports what the text it was given says.

## Licence

MIT. See `LICENSE`.

Nothing in this repository is legal or regulatory advice.
