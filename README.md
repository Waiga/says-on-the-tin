# says-on-the-tin

Finds where a cosmetic label contradicts itself: a free-from claim on the
front, and an ingredient on the back that breaks it.

Runs entirely on your machine. No account, no upload, no network access, no
dependencies beyond Python itself.

What it found across 2,554 real published labels, and the caveat that matters
more than the finding, is written up in
[An ingredient list cannot tell you most of what you want to know](https://medium.com/@aryawaiga0/an-ingredient-list-cannot-tell-you-most-of-what-you-want-to-know-f3807f357837).

```
$ says-on-the-tin shampoo-label.txt

says-on-the-tin 0.1.1 — shampoo-label.txt

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
pip install says-on-the-tin
```

Python 3.11 or newer. Nothing else. To install from a clone instead, `pip install .`
from the repository root.

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
| Individual ingredients parsed | 55,606 |
| Claims found | 3,435 |
| …that no ingredient list can settle | 660 (19.2% of 3,435) |
| **Contradictions** | **54, across 49 products** (1.9% of 2,554 labels) |
| Sent for review | 84 |
| Known false-positive cases wrongly flagged | **0 of 14** |

Those 14 are cases an earlier, independent pass over the same corpus had
itself identified as things that must *not* be called contradictions — Epsom
salt under sulfate-free, fatty alcohols and benzyl alcohol under
alcohol-free. None is reported as a contradiction here.

**Two things that table does not say, stated so it cannot mislead.** Every
record in the corpus was selected for having an ingredient list of at least
50 characters, so a parse rate of 2,554 out of 2,554 is guaranteed by the
selection and is not an achievement of the extractor. And the claims in that
run came from the database's own label tags — `without-paraben`, `no-gluten`
— which are tidier than anything printed on a pack.

So there is a second measurement arm, over the one field in that corpus a
brand actually wrote: the product name. It found **76 claims in 71 real
product names** and **0 contradictions** — those brands' names and lists
agree. That arm exists because an adversarial review pointed out that three
real defects had survived precisely because claim detection had never met
prose, and it earned its place immediately: it caught a bug that reported
`Ammonium Lauryl Sulfate` as breaking a *silicone*-free claim.

### What the measurement found that the tests did not

Every one of these was a real defect, found only by meeting real labels or by
an independent reviewer attacking the code:

- **Claim detection was English-only.** Every contradiction in the sample was
  tagged in Portuguese, French, German, Italian or Dutch. An English-only
  pass found none of them. It now reads `sem parabenos`, `sans paraben`,
  `sin parabenos`, `ohne Parabene`, `senza parabeni`, `Parabeenvrij` and
  `Parabenfrei`.
- **One negation governs a whole list.** "Free from parabens, sulphates and
  silicones" is three claims. Binding the negation to a single noun found
  one of them, and reported a label with three contradictions as having one
   — which reads as a clean bill of health on the other two. `FREE FROM:`
  bullet panels found nothing at all, because of the colon.
- **`Parfum (Fragrance)` is the most common printed form** of the fragrance
  entry, and an exact-match pattern missed all of it — 20 real
  contradictions.
- **Glycerin and stearic acid buried everything.** Both are
  sourcing-ambiguous under a vegan claim, and flagging them produced 524 of
  538 review findings. Technically defensible, practically useless.
- **Wheat derivatives under a gluten-free claim are contested**, not
  clear-cut. Hydrolysed wheat protein is not gluten. They are reviews now.
- **Brands print the claim inside the ingredient panel** — `SANS PARABEN`
  closing a French list, or `Formulated without mineral oil, paraffin,
  petrolatum`. Read as ingredients, those words made labels contradict
  themselves with their own promises.
- **"No colour transfer"** on a long-wear lipstick was read as a
  colourant-free claim, and **"ohne rein synthetische Duftstoffe"** — no
  *purely synthetic* fragrance — as an absolute one.
- **Bare `milk` is not dairy.** It matched oat milk, coconut milk, and a
  poison-control warning caught inside a panel.
- **`Zea Mays (Corn) Silk Extract` was called silk.** The README named
  cornsilk as a look-alike the tool handled; it did not, and the test that
  claimed it did used a bracket that happened to block the pattern.
- **A `\w*silicate` exclusion swallowed Trimethylsiloxysilicate**, a real
  silicone, in 39 of the 2,554 labels.
- **`\w*paraben` backtracked quadratically.** One label with a 40,000-
  character unbroken run took 20.8 seconds; it now takes 0.07.
- **A binary file after `Ingredients:`** was parsed as a list and reported as
  no contradiction found — the most reassuring thing this tool can say, about
  a file it never read.
- **Exit code 0 when nothing was checked.** A CI job over a label whose list
  did not parse went green. It now exits 2.

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
- **Marketing prose inside an ingredient panel is only partly handled.**
  Claim sentences and common safety warnings are recognised and set aside,
  but a panel containing arbitrary prose can still produce junk tokens.
- **Crowd-sourced label data can be wrong.** In the measurement above, a
  "contradiction" may be a mislabelled record rather than a mislabelled pack.
  The tool reports what the text it was given says.

## Licence

MIT. See `LICENSE`.

Nothing in this repository is legal or regulatory advice.
