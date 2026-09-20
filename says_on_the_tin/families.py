"""What each "free-from" claim actually excludes.

This module is the opinionated part of the tool, and the part most likely to
be wrong, so it states its reasoning in the open.

Three kinds of entry, and the difference between them is the difference
between a tool people trust and one they laugh at:

  members   ingredients that plainly break the claim. Methylparaben under a
            paraben-free claim.
  disputed  ingredients whose membership is genuinely contested, conditional,
            or depends on sourcing that a label does not state. Squalane under
            a vegan claim can come from a shark or from an olive and the pack
            will not say which. These produce a review, never a conflict.
  excluded  ingredients that look like members to a naive string match and are
            not. Cetearyl Alcohol is a waxy emollient, not the volatile
            alcohol an alcohol-free claim is about. Flagging it is the single
            fastest way for a tool like this to lose its reader. Each carries
            the reason, and the tool reports what it excluded rather than
            silently dropping it.

Every pattern is matched against a normalised ingredient string: casefolded,
whitespace-collapsed, with British spellings folded to American so that
"sulphate" and "sulfate" are one thing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Member:
    pattern: str
    label: str
    # When set, a match is a review rather than a conflict, and this text says
    # what the reader has to decide.
    caveat: str = ""


@dataclass(frozen=True)
class Excluded:
    pattern: str
    reason: str


@dataclass(frozen=True)
class Family:
    key: str
    # How the report names the group, e.g. "parabens".
    noun: str
    # Nouns a negation can attach to, e.g. "parabens?". claims.py builds
    # the negation forms around them.
    claim_tokens: tuple[str, ...] = ()
    # Standalone claim regexes for families that are not "free from X"
    # shaped, such as "vegan" and "unscented".
    claim_patterns: tuple[str, ...] = ()
    members: tuple[Member, ...] = ()
    disputed: tuple[Member, ...] = ()
    excluded: tuple[Excluded, ...] = ()
    note: str = ""
    _member_res: list[tuple[re.Pattern[str], Member]] = field(
        default_factory=list, compare=False, repr=False
    )
    _disputed_res: list[tuple[re.Pattern[str], Member]] = field(
        default_factory=list, compare=False, repr=False
    )
    _excluded_res: list[tuple[re.Pattern[str], Excluded]] = field(
        default_factory=list, compare=False, repr=False
    )

    def __post_init__(self) -> None:
        for m in self.members:
            self._member_res.append((re.compile(m.pattern), m))
        for m in self.disputed:
            self._disputed_res.append((re.compile(m.pattern), m))
        for e in self.excluded:
            self._excluded_res.append((re.compile(e.pattern), e))

    def classify(
        self, normalised: str
    ) -> tuple[str, Member | Excluded] | None:
        """Return ("member"|"disputed"|"excluded", entry) or None.

        Exclusions are tested first and win outright: they exist precisely to
        stop a broader member pattern from firing on a look-alike.
        """
        for rx, exc in self._excluded_res:
            if rx.search(normalised):
                return "excluded", exc
        for rx, mem in self._member_res:
            if rx.search(normalised):
                return "member", mem
        for rx, mem in self._disputed_res:
            if rx.search(normalised):
                return "disputed", mem
        return None


# A family declares the NOUNS a negation can attach to. The negation forms
# themselves live in claims.py, because one negation routinely governs a
# whole list of them -- "free from parabens, sulphates and silicones" is one
# word of negation and three claims, and binding a negation to a single noun
# found only the last of them.
#
# On a European pack the negation is usually not in English at all: measured
# against 2,554 real published labels, every contradiction in the sample was
# tagged in Portuguese, French, German, Italian or Dutch, and an
# English-only pass found none of them.


def _tokens(*tokens: str) -> tuple[str, ...]:
    return tokens


FAMILIES: tuple[Family, ...] = (
    Family(
        key="paraben",
        noun="parabens",
        claim_tokens=_tokens(r"parabens?", r"parabenos?", r"parab[eè]nes?",
                                    r"parabene?n?", r"parabeni",
                                    # Dutch compounds it as "parabeenvrij".
                                    r"parabeen(?:en)?"),
        members=(
            Member(r"paraben\b", "a paraben"),
            Member(r"\b(?:methyl|ethyl|propyl|butyl)\s+\d?-?hydroxybenzoate\b",
                   "a paraben under its chemical name"),
        ),
        note=(
            "Parabens are a clean family: an ingredient name ending in "
            "'paraben' is one, including its sodium and potassium salts."
        ),
    ),
    Family(
        key="sulfate",
        noun="cleansing sulfates",
        claim_tokens=_tokens(r"sulfates?", r"sulphates?", r"sulfatos?",
                             r"sulfaten?", r"sulfaat", r"sulphaat",
                             r"solfati?", r"sls", r"sles"),
        members=(
            # "coco" is deliberately absent here: Sodium Coco-Sulfate is
            # contested and is listed under `disputed` instead. Matching it
            # as a member would shadow that entry, because members are
            # tested first.
            Member(r"\b(?:sodium|ammonium|tea|mea|magnesium)[\s\-]"
                   r"(?:lauryl|laureth|myreth)[\s\-]?sulfate\b",
                   "a sulfate surfactant"),
            Member(r"\bsodium\s+c\d+[\s\-]?\d*\s*(?:pareth|alkyl)?[\s\-]?sulfate\b",
                   "a sulfate surfactant"),
            Member(r"\b(?:sodium|ammonium)\s+(?:lauryl|dodecyl)\s+ether\s+sulfate\b"
                   r"|\bsodium\s+dodecyl\s+sulfate\b",
                   "a sulfate surfactant"),
        ),
        disputed=(
            Member(
                r"\bsodium\s+coco[\s\-]?sulfate\b",
                "sodium coco-sulfate",
                caveat=(
                    "Sodium Coco-Sulfate is a sulfate surfactant, but it is "
                    "widely used in products marketed as sulfate-free on the "
                    "argument that it is a coconut-derived blend rather than "
                    "pure SLS. Whether it breaks the claim is a position, not "
                    "a fact."
                ),
            ),
        ),
        excluded=(
            Excluded(
                r"\b(?:magnesium|zinc|sodium|ammonium|copper|manganese|iron|"
                r"chondroitin|dextran|heparan|keratan|barium|calcium)\s+sulfate\b",
                "an inorganic or polysaccharide sulfate salt, not a cleansing "
                "surfactant. 'Sulfate-free' is a claim about detergents such "
                "as SLS and SLES; Magnesium Sulfate is Epsom salt.",
            ),
            Excluded(
                r"\bsulfoacetate\b",
                "Sodium Lauryl Sulfoacetate is a different, milder surfactant "
                "that is commonly used to replace sulfates in exactly these "
                "products. Despite the name it is not a sulfate.",
            ),
            Excluded(
                r"\b(?:sulfonate|sulfosuccinate|isethionate|taurate)\b",
                "a sulfonate-class surfactant, not a sulfate ester.",
            ),
        ),
        note=(
            "'Sulfate-free' is an industry claim about harsh cleansing "
            "surfactants, chiefly SLS and SLES. It has never meant the "
            "absence of every sulfate ion, and treating it that way produces "
            "nonsense findings on any product containing Epsom salt."
        ),
    ),
    Family(
        key="silicone",
        noun="silicones",
        claim_tokens=_tokens(r"silicones?", r"siliconas?", r"silikone?n?",
                                    r"siliconi"),
        members=(
            Member(r"methicone\b", "a silicone"),
            Member(r"siloxane\b", "a silicone"),
            Member(r"\bdimethiconol\b", "a silicone"),
            Member(r"silsesquioxane\b", "a silicone resin"),
            # No leading \b: the real INCI is Trimethylsiloxysilicate,
            # where the fragment sits mid-word.
            Member(r"siloxysilicate\b", "a silicone resin"),
            Member(r"\bpolysilicone-\d", "a silicone"),
            Member(r"\bsilicone\s+quaternium-\d", "a silicone"),
        ),
        excluded=(
            Excluded(
                r"\b(?:silica|silicon\s+dioxide|hydrated\s+silica)\b",
                "silica is a mineral, not a silicone polymer.",
            ),
            Excluded(
                r"(?<!siloxy)silicate\b",
                "silicates are minerals such as Magnesium Aluminum Silicate, "
                "not silicone polymers.",
            ),
        ),
    ),
    Family(
        key="fragrance",
        noun="fragrance",
        claim_tokens=_tokens(
            r"fragrances?", r"parfum", r"perfume", r"scent",
            r"fragr[aâ]ncias?", r"duftstoffe?", r"duft", r"profumo",
            r"geur", r"aroma",
        ),
        members=(
            # Packs print this as "Parfum", "Parfum (Fragrance)",
            # "PARFUM/ FRAGRANCE" and "Fragrance (Parfum)". All of them are
            # the same single declared entry, so the pattern accepts the
            # synonyms joined by any punctuation and nothing else.
            Member(
                r"^(?:parfum|fragrance|aroma|perfume|duft)"
                r"(?:[\s/(),.-]+(?:parfum|fragrance|aroma|perfume|duft))*"
                r"[\s)]*$",
                "declared fragrance",
            ),
        ),
        disputed=(
            Member(
                r"\b(?:linalool|limonene|citral|geraniol|citronellol|eugenol|"
                r"isoeugenol|coumarin|farnesol|cinnamal|cinnamyl\s+alcohol|"
                r"benzyl\s+salicylate|benzyl\s+benzoate|benzyl\s+cinnamate|"
                r"hexyl\s+cinnamal|amyl\s+cinnamal|anise\s+alcohol|"
                r"hydroxycitronellal|alpha[\s\-]isomethyl\s+ionone|"
                r"butylphenyl\s+methylpropional|evernia\s+\w+)\b",
                "a declarable fragrance allergen",
                caveat=(
                    "This is one of the fragrance allergens the EU requires to "
                    "be named on the label. It can occur naturally as a "
                    "component of an essential oil rather than as added "
                    "perfume, so it does not on its own prove added fragrance "
                    "-- but a fragrance-free claim sitting above it is worth "
                    "a look."
                ),
            ),
            Member(
                r"\b(?:lavandula|citrus\s+\w+|mentha|melaleuca|rosmarinus|"
                r"eucalyptus|pelargonium|cananga|jasminum|rosa\s+\w+|"
                r"pogostemon|santalum)\b[^,]*\b(?:oil|extract)\b",
                "a botanical essential oil",
                caveat=(
                    "Essential oils are fragrant by definition. Many brands "
                    "treat 'fragrance-free' as meaning no synthetic parfum "
                    "while still using them; others do not. This is a "
                    "position the brand has to own."
                ),
            ),
        ),
        note=(
            "'Unscented' is not the same claim as 'fragrance-free'. An "
            "unscented product may legitimately contain a masking fragrance "
            "whose job is to hide a raw-material smell, so this tool treats a "
            "fragrance match under an unscented claim as something to review "
            "rather than a contradiction."
        ),
    ),
    Family(
        key="unscented",
        noun="added scent",
        claim_patterns=(r"\bunscented\b",),
        disputed=(
            Member(
                r"^(?:parfum|fragrance|aroma)$",
                "declared fragrance",
                caveat=(
                    "'Unscented' does not mean fragrance-free. A masking "
                    "fragrance used to neutralise a base odour is consistent "
                    "with an unscented claim in normal industry usage, so "
                    "this is only worth checking, not a contradiction."
                ),
            ),
        ),
    ),
    Family(
        key="alcohol",
        noun="volatile alcohol",
        claim_tokens=_tokens(r"alcohols?", r"alcool", r"alkohol", r"alcol",
                                    r"alcoholes"),
        members=(
            Member(r"^alcohol$", "alcohol"),
            Member(r"^alcohol\s*[/(]\s*(?:alcool|ethanol)\)?$",
                   "alcohol"),
            Member(r"^alcohol\s*denat\.?$", "denatured alcohol"),
            Member(r"\bsd\s+alcohol\b", "SD alcohol"),
            Member(r"^(?:ethanol|ethyl\s+alcohol)$", "ethanol"),
            Member(r"^(?:isopropyl\s+alcohol|isopropanol)$",
                   "isopropyl alcohol"),
            Member(r"\bdenatured\s+alcohol\b", "denatured alcohol"),
        ),
        excluded=(
            Excluded(
                r"\b(?:cetyl|cetearyl|stearyl|behenyl|myristyl|lauryl|"
                r"arachidyl|oleyl|isostearyl|coconut|c\d+[\s\-]\d+)\s+alcohol\b",
                "a fatty alcohol. These are waxy emollients and thickeners "
                "that soften skin; they are the opposite of the drying, "
                "volatile alcohol an alcohol-free claim is about. This is the "
                "most common false alarm in ingredient checking.",
            ),
            Excluded(
                r"\bbenzyl\s+alcohol\b",
                "Benzyl Alcohol is an aromatic solvent and preservative. It "
                "is not the volatile alcohol meant by an alcohol-free claim, "
                "though it is separately a declarable fragrance allergen.",
            ),
            Excluded(
                r"\b(?:lanolin|batyl|phytantriol)\s+alcohol\b",
                "a wax alcohol, not a volatile alcohol.",
            ),
        ),
        note=(
            "'Alcohol-free' conventionally means no ethanol or denatured "
            "alcohol. Cetearyl Alcohol and its relatives are fatty alcohols "
            "and do not break the claim."
        ),
    ),
    Family(
        key="vegan",
        noun="animal-derived ingredients",
        claim_patterns=(r"\bvegan\b", r"\b100\s*%\s*plant[\s\-]based\b"),
        members=(
            Member(r"\b(?:carmine|cochineal|ci\s*75470)\b",
                   "carmine, a pigment made from insects"),
            Member(r"\b(?:cera\s+alba|beeswax|cire\s+d'abeille)\b", "beeswax"),
            Member(r"\blanolin\b", "lanolin, from sheep's wool"),
            Member(r"\bmel\b|\bhoney\b", "honey"),
            Member(r"\bgelatin\b", "gelatin"),
            Member(r"\bcera\s+flava\b", "yellow beeswax"),
            # Bare "milk" is not dairy. A warning sentence caught inside an
            # ingredient panel -- "if swallowed give a glass of water or
            # milk" -- matched it, and so did every oat, coconut and almond
            # milk on the market. Dairy has to be named.
            Member(r"\b(?:goat|cow|donkey|sheep|buffalo|camel|whole|"
                   r"skimmed|dairy|jument|[aâ]nesse)\s+milk\b"
                   r"|\bmilk\s+(?:protein|powder|fat|lipids?|solids)\b"
                   r"|\blactis\s+proteinum\b|\bbutyrum\b",
                   "a milk derivative"),
            Member(r"\b(?:propolis|royal\s+jelly)\b", "a bee product"),
            Member(r"\b(?:serica|silk\s+\w+|hydrolyzed\s+silk)\b", "silk"),
            Member(r"\bshellac\b", "shellac, an insect resin"),
            Member(r"\bguanine\b", "guanine, from fish scales"),
            Member(r"\b(?:tallow|adeps|lard)\b", "rendered animal fat"),
            Member(r"\bsnail\s+secretion\b", "snail secretion filtrate"),
            Member(r"\bcasein\w*\b|\b(?:lactose|lactis|whey|ovum|egg)\b",
                   "a milk or egg derivative"),
            Member(r"\b(?:emu|mink|marine)\s+oil\b", "an animal oil"),
        ),
        disputed=(
            Member(r"\bsqualane\b", "squalane", caveat=(
                "Squalane is made either from shark liver or from olives and "
                "sugarcane. The two are the same molecule and the label does "
                "not say which was used. Only the supplier can answer.")),
            Member(r"\b(?:hydrolyzed\s+)?(?:collagen|elastin|keratin)\b",
                   "a structural protein", caveat=(
                       "Collagen, elastin and keratin were historically "
                       "animal-derived, and plant-hydrolysate and "
                       "biotechnology versions of all three are now sold "
                       "under names that read the same on a pack. The "
                       "supplier's specification settles it.")),
            Member(r"\bhyaluronic\s+acid\b", "hyaluronic acid", caveat=(
                "Historically extracted from rooster combs; almost all "
                "cosmetic supply is now bacterial fermentation. Usually "
                "vegan, but the label does not say.")),
        ),
        excluded=(
            Excluded(
                r"^glycerin$|\bstearic\s+acid\b",
                "sourcing-ambiguous but overwhelmingly plant-derived or "
                "synthetic in cosmetic supply, and present in most products "
                "on the market. Measured against 2,554 real published "
                "labels, flagging these two produced 524 of 538 review "
                "findings and buried everything worth reading. If your "
                "vegan claim is audited, the supplier declaration for these "
                "is worth holding, but a checker cannot usefully say so "
                "on every product.",
            ),
            Excluded(
                r"\b(?:coconut|cocos|almond|amygdalus|oat|avena|rice|"
                r"oryza|soy|soja|glycine|cashew|hemp|macadamia|plant|"
                r"vegetable|nut)\b[^,]{0,24}\bmilk\b"
                r"|\bmilk\s+thistle\b|\bsilybum\b",
                "a plant milk or an unrelated plant whose common name "
                "contains the word. Coconut milk is not dairy.",
            ),
            Excluded(
                r"\bzea\s+mays\b|\bcorn\s?silk\b|\bmaize\b",
                "corn. 'Zea Mays (Corn) Silk Extract' is the silk of a "
                "maize cob, not the fibre spun by a silkworm.",
            ),
            Excluded(
                r"\ballantoin\b",
                "Allantoin used in cosmetics is synthetic or comfrey-derived, "
                "despite an old association with animal sources.",
            ),
            Excluded(
                r"\blactic\s+acid\b",
                "Cosmetic lactic acid is produced by fermenting sugars, not "
                "from milk, despite the name.",
            ),
            Excluded(
                r"\b(?:vegetable|soy|wheat|rice|pea|oat)\s+\w*protein\b",
                "a named plant protein.",
            ),
            Excluded(
                r"\b(?:vegan|plant[\s\-]based|plant[\s\-]derived|synthetic|"
                r"bio[\s\-]?identical|biotech\w*)\b",
                "the ingredient name itself says it is not animal-derived, "
                "as in 'Sr-Hydrozoan Polypeptide-1 (Vegan Collagen)'. A "
                "checker that ignores the qualifier in the name contradicts "
                "a claim the label already answered.",
            ),
        ),
        note=(
            "A vegan claim is about sourcing, and sourcing is frequently "
            "invisible in an INCI name. This tool can catch the "
            "unambiguous cases and can tell you which ingredients only your "
            "supplier can settle. It cannot confirm a product is vegan."
        ),
    ),
    Family(
        key="gluten",
        noun="gluten grains",
        claim_tokens=_tokens(r"gluten", r"gl[uú]ten", r"glutine"),
        members=(
            Member(r"^gluten$|\bwheat\s+gluten\b", "gluten itself"),
        ),
        disputed=(
            Member(
                r"\btriticum\b|\bhordeum\b|\bsecale\b|\bwheat\b|"
                r"\bbarley\b|\brye\b",
                "a wheat, barley or rye derivative",
                caveat=(
                    "Gluten-free is not a defined term for cosmetics in any "
                    "market, and most grain-derived cosmetic ingredients are "
                    "hydrolysates, refined oils or extracts whose gluten "
                    "content is far below the 20 ppm food threshold and is "
                    "not stated on the pack. A coeliac customer using a lip "
                    "product may still care. Only the supplier's "
                    "specification can settle it."
                ),
            ),
            Member(r"\bavena\b|\boat\b", "oat", caveat=(
                "Oats contain no gluten of their own but are very commonly "
                "cross-contaminated in milling. Whether this breaks a "
                "gluten-free claim depends on the supplier's certification.")),
        ),
    ),
    Family(
        key="mineral-oil",
        noun="petroleum-derived oils and waxes",
        claim_tokens=_tokens(
            r"mineral\s+oils?", r"petrolatum", r"petroleum", r"paraffins?",
            r"[oó]leo\s+mineral", r"aceite\s+mineral", r"huile\s+min[ée]rale",
            r"mineral[öo]l", r"olio\s+minerale",
        ),
        members=(
            Member(r"\bparaffinum\s+liquidum\b", "liquid paraffin"),
            Member(r"\bmineral\s+oil\b", "mineral oil"),
            Member(r"\bpetrolatum\b", "petrolatum"),
            Member(r"\bcera\s+microcristallina\b", "microcrystalline wax"),
            Member(r"\bmicrocrystalline\s+wax\b", "microcrystalline wax"),
            Member(r"\bozokerite\b", "ozokerite"),
            Member(r"\bparaffin\b(?!um\s+liquidum)", "paraffin"),
            Member(r"\bpetroleum\s+jelly\b", "petroleum jelly"),
            Member(r"\bceresin\b", "ceresin"),
            Member(r"\bisoparaffin\b", "isoparaffin"),
        ),
        disputed=(
            Member(r"\bhydrogenated\s+polyisobutene\b",
                   "hydrogenated polyisobutene", caveat=(
                       "A synthetic hydrocarbon made from petroleum "
                       "feedstock. Not mineral oil, but not free of petroleum "
                       "origin either.")),
        ),
    ),
    Family(
        key="phthalate",
        noun="phthalates",
        claim_tokens=_tokens(r"phthalates?", r"ftalatos?", r"phtalates?",
                                    r"ftalati"),
        members=(
            Member(r"\bphthalate\b", "a phthalate"),
        ),
        disputed=(
            Member(r"^(?:parfum|fragrance)$", "undisclosed fragrance",
                   caveat=(
                       "Phthalates are used as fragrance fixatives and are "
                       "not separately declared, because 'Parfum' may lawfully "
                       "stand for an undisclosed mixture. A phthalate-free "
                       "claim over an undisclosed fragrance rests on the "
                       "fragrance house's statement, not on the label.")),
        ),
    ),
    Family(
        key="formaldehyde",
        noun="formaldehyde and its releasers",
        claim_tokens=_tokens("formaldehydes?"),
        members=(
            Member(r"\bformaldehyde\b", "formaldehyde"),
            Member(r"\bformalin\b", "formalin"),
            Member(r"\bmethylene\s+glycol\b", "methylene glycol"),
        ),
        disputed=(
            Member(
                r"\b(?:dmdm\s+hydantoin|diazolidinyl\s+urea|"
                r"imidazolidinyl\s+urea|quaternium-15|bronopol|"
                r"2-bromo-2-nitropropane|sodium\s+hydroxymethylglycinate|"
                r"benzylhemiformal|methenamine|"
                r"5-bromo-5-nitro-1,3-dioxane|"
                r"tris\(hydroxymethyl\)nitromethane|glyoxal)\b",
                "a formaldehyde releaser",
                caveat=(
                    "This preservative is not formaldehyde, but it works by "
                    "slowly releasing it. Whether a 'formaldehyde-free' claim "
                    "survives a releaser is a long-running argument in the "
                    "industry and a frequent subject of consumer complaints. "
                    "Decide deliberately rather than by accident."
                ),
            ),
        ),
    ),
    Family(
        key="peg",
        noun="PEGs and ethoxylates",
        claim_tokens=_tokens("pegs?", "ethoxylates?"),
        members=(
            Member(r"\bpeg[\s\-]?\d", "a PEG"),
            Member(r"\bppg[\s\-]?\d", "a PPG"),
            Member(r"\b[a-z]+eth[\s\-]\d+\b", "an ethoxylated ingredient"),
            Member(r"\bpolysorbate\s*\d+\b", "a polysorbate"),
            Member(r"\bpolyethylene\s+glycol\b", "polyethylene glycol"),
        ),
    ),
    Family(
        key="talc",
        noun="talc",
        claim_tokens=_tokens(r"talc", r"talco", r"talkum"),
        # "Talc (Magnesium Silicate)" is how 62 of the 2,554 corpus
        # labels print it; an anchored pattern found none of them.
        members=(Member(r"\btalc\b", "talc"),),
    ),
    Family(
        key="nut",
        noun="tree nuts",
        claim_tokens=_tokens("nuts?", "tree\\s+nuts?"),
        members=(
            Member(r"\bprunus\s+(?:amygdalus|dulcis)\b",
                   "sweet almond"),
            Member(r"\bsweet\s+almond\b|\balmond\s+oil\b",
                   "sweet almond"),
            Member(r"\bcastanea\b", "chestnut"),
            Member(r"\bpinus\s+pinea\b", "pine nut"),
            Member(r"\barachis\s+hypogaea\b|\bpeanut\b",
                   "peanut, a legume that nut-free claims are "
                   "normally read to cover"),
            Member(r"\bcorylus\b", "hazelnut"),
            Member(r"\bjuglans\b", "walnut"),
            Member(r"\bmacadamia\b", "macadamia"),
            Member(r"\banacardium\b", "cashew"),
            Member(r"\bbertholletia\b", "brazil nut"),
            Member(r"\bpistacia\s+vera\b", "pistachio"),
            Member(r"\bcarya\b", "pecan"),
        ),
        disputed=(
            Member(r"\bargania\b", "argan", caveat=(
                "Argan is botanically a drupe kernel rather than a tree nut, "
                "but it is commonly treated as a nut allergen risk.")),
            Member(r"\bcocos\s+nucifera\b", "coconut", caveat=(
                "The FDA classifies coconut as a tree nut for allergen "
                "labelling; botanically it is not one, and most tree-nut "
                "allergic people tolerate it.")),
            Member(r"\bbutyrospermum\b", "shea", caveat=(
                "Shea comes from a tree nut but the refined butter is very "
                "rarely allergenic. Positions differ.")),
        ),
    ),
    Family(
        key="soy",
        noun="soy",
        claim_tokens=_tokens(r"soya?", r"soybeans?", r"soja"),
        members=(
            Member(r"\bglycine\s+(?:soja|max)\b", "soy"),
            Member(r"\bsoybean\b|\bsoja\b", "soy"),
            Member(r"\bhydrolyzed\s+soy\b|\bsoy\s+\w*protein\b",
                   "a soy protein"),
        ),
        disputed=(
            Member(r"^lecithin$", "lecithin", caveat=(
                "Unqualified lecithin is usually soy-derived. Sunflower "
                "lecithin is normally labelled as such.")),
            Member(r"^tocopherol", "tocopherol", caveat=(
                "Vitamin E is frequently produced from soybean oil, though "
                "the finished ingredient is generally considered free of soy "
                "protein.")),
        ),
    ),
    Family(
        key="dye",
        noun="added colourants",
        # "colou?rs?" on its own is deliberately absent. "No colour
        # transfer" is a wear claim on almost every long-wear lipstick,
        # and reading it as a colourant-free claim is a false accusation
        # against a list that legitimately contains CI numbers.
        # "colou?rs?" on its own is deliberately absent. "No colour
        # transfer" is a wear claim on almost every long-wear lipstick,
        # and reading it as a colourant-free claim is a false accusation
        # against a list that legitimately contains CI numbers.
        claim_tokens=_tokens(
            r"dyes?", r"colou?rants?", r"colorantes?", r"farbstoffe?",
            r"(?:artificial|added|synthetic)\s+colou?rs?",
        ),
        members=(
            Member(r"\bci\s*\d{5}\b", "a colour index pigment"),
            Member(r"\b(?:fd&c|d&c)\s+\w+", "a certified colour"),
            Member(r"\b(?:red|blue|yellow|green|violet|orange)\s+\d+\b",
                   "a certified colour"),
        ),
        disputed=(
            Member(r"\bmica\b", "mica", caveat=(
                "Mica is a mineral used for shimmer and is often listed "
                "alongside colourants. Whether it counts as an added colour "
                "depends on what the claim was meant to promise.")),
            Member(r"\b(?:titanium\s+dioxide|iron\s+oxides?|"
                   r"zinc\s+oxide)\b", "a mineral pigment", caveat=(
                       "A mineral pigment rather than a synthetic dye. Many "
                       "brands consider these consistent with a 'no "
                       "artificial colours' claim.")),
        ),
    ),
)


@dataclass(frozen=True)
class Unverifiable:
    key: str
    patterns: tuple[str, ...]
    explanation: str


# Claims that no ingredient list can settle, whatever it contains. Reporting
# these is not padding: a reader who sees "cruelty-free" pass silently through
# a checking tool may reasonably conclude the tool checked it.
UNVERIFIABLE: tuple[Unverifiable, ...] = (
    Unverifiable(
        "cruelty-free",
        (r"\bcruelty[\s\-]?free\b", r"\bnot\s+tested\s+on\s+animals\b",
         r"\bleaping\s+bunny\b"),
        "This is a claim about testing policy across a supply chain. Nothing "
        "in an ingredient list can confirm or contradict it.",
    ),
    Unverifiable(
        "dermatologically-tested",
        (r"\bdermatologically\s+(?:tested|approved)\b",
         r"\bclinically\s+(?:proven|tested)\b",
         r"\ballergy\s+tested\b", r"\bophthalmologically\s+tested\b"),
        "This refers to a study that was or was not run. The ingredient list "
        "says nothing about it, and the phrase itself does not say what the "
        "study measured or what result it produced.",
    ),
    Unverifiable(
        "hypoallergenic",
        (r"\bhypo[\s\-]?allergenic\b", r"\bnon[\s\-]?comedogenic\b",
         r"\bsuitable\s+for\s+sensitive\s+skin\b"),
        "There is no agreed standard behind this word, and no ingredient list "
        "can demonstrate it. It describes an expectation about reactions in "
        "people.",
    ),
    Unverifiable(
        "chemical-free",
        (r"\bchemical[\s\-]?free\b", r"\bno\s+chemicals\b",
         r"\bnon[\s\-]?toxic\b", r"\btoxin[\s\-]?free\b"),
        "Every ingredient in every cosmetic is a chemical, water included, so "
        "this cannot be true of any product. The European Commission's "
        "Technical Document on Cosmetic Claims addresses this class of claim "
        "under the common criteria in Regulation (EU) 655/2013; whether it is "
        "permissible where you sell is a question for a regulatory adviser, "
        "not for this tool.",
    ),
    Unverifiable(
        "natural",
        (r"\b100\s*%\s*natural\b", r"\ball[\s\-]natural\b",
         r"\bcompletely\s+natural\b"),
        "There is no legal definition of 'natural' for cosmetics in the EU, "
        "the US or India, and no ingredient list can settle a word without a "
        "definition. Certification schemes such as COSMOS and NATRUE each "
        "have their own, and they disagree.",
    ),
    Unverifiable(
        "clean",
        (r"\bclean\s+beauty\b", r"\bclean\s+formula\b",
         r"\bnon[\s\-]?toxic\s+beauty\b"),
        "'Clean' is a retailer and marketing term, not a defined one. Each "
        "retailer that uses it maintains its own restricted list and those "
        "lists disagree with each other, so the same product can be clean in "
        "one shop and not in the next.",
    ),
    Unverifiable(
        "organic",
        (r"\b(?:certified\s+)?organic\b", r"\b100\s*%\s*organic\b"),
        "An organic claim rests on a certification held by the product or its "
        "inputs. An INCI list does not carry certification status, and the "
        "asterisks that often mark organic content on a pack are a brand's "
        "own annotation rather than proof.",
    ),
)


FAMILY_BY_KEY = {f.key: f for f in FAMILIES}
