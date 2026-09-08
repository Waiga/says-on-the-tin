"""Find and parse the ingredient list inside a block of label text.

Real ingredient lists are not tidy. They arrive with the preamble in three
languages, colourants in a shared "may contain" block, supplier blend notation
in the middle of a name, asterisks pointing at an organic-content footnote,
and commas inside parentheses that must not be split on. Everything this
module does is a response to something that actually appears on packs.
"""

from __future__ import annotations

import html
import re
import unicodedata

from says_on_the_tin.models import Ingredient, Position


# The word that introduces the list, in the languages that share a European
# pack, plus the two abbreviations used on spec sheets.
_PREAMBLE = re.compile(
    r"(?im)^\W{0,4}(?:"
    r"ingredients?|ingr[ée]dients?|inhaltsstoffe|zutaten|ingredienti|"
    r"ingredientes|ingredi[eë]nten|composition|sk[lł]adniki|"
    r"st[oa]f[fn]er|ainesosat|inci"
    r")\b\s*[:\-–]?\s*"
)

# Where the list stops, when the text continues into another pack panel.
_TERMINATOR = re.compile(
    r"(?im)^\W{0,4}(?:"
    r"directions?|how\s+to\s+use|usage|application|warnings?|caution|"
    r"precautions?|storage|store\s+in|net\s+(?:wt|weight|vol)|"
    r"manufactured\s+(?:by|for)|marketed\s+by|distributed\s+by|made\s+in|"
    r"best\s+before|expiry|use\s+by|customer\s+care|for\s+external\s+use|"
    r"keep\s+out\s+of\s+reach"
    r")\b"
)

# The same panels, when they run on inline rather than starting a line. A
# poison-control warning parsed as ingredients produced tokens that matched
# real family patterns.
_INLINE_TERMINATOR = re.compile(
    r"(?i)\b(?:if\s+swallowed|if\s+in\s+eyes|avoid\s+contact\s+with\s+"
    r"(?:the\s+)?eyes|call\s+a?\s*poison|seek\s+medical|discontinue\s+use|"
    r"keep\s+out\s+of\s+reach|for\s+external\s+use\s+only)\b"
)

# The colourant block. Anything after this marker may or may not be in the
# specific unit in your hand, because one list is printed across a whole shade
# range.
_MAY_CONTAIN = re.compile(
    r"(?i)(?:\[?\s*(?:\+/?-|±)\s*\]?\s*)?\b(?:may\s+contain|peut\s+contenir|"
    r"kann\s+enthalten|puede\s+contener)\b\s*[:\-]?\s*"
    r"|\[\s*(?:\+/?-|±)\s*\]\s*"
)

# A sentence boundary inside an ingredient field. Packs run marketing prose,
# usage instructions and the claim itself into the same field, separated only
# by full stops: "Sans paraben. Ne pas appliquer sur le visage." Splitting
# there recovers them as their own tokens so the claim veto can drop them.
# The abbreviations are the ones that legitimately end an INCI name.
_SENTENCE = re.compile(
    r"(?i)(?<!\bdenat)(?<!\bspp)(?<!\bsp)(?<!\bapprox)(?<!\bapprox\.)"
    r"(?<!\bcert)(?<!\bq\.s)(?<!\bviz)\.\s+(?=\S)"
)

# Supplier blend notation: "Ingredient A (and) Ingredient B" is two things.
_BLEND = re.compile(r"(?i)\s*\((?:and|et|und)\)\s*")

# Percentage and footnote annotations that ride along with a name.
_ANNOTATION = re.compile(
    r"(?:\b\d+(?:[.,]\d+)?\s*%(?:\s*(?:min|max|w/w|v/v))?\.?)"
    r"|(?:\b(?:min|max|approx\.?)\s*\d+(?:[.,]\d+)?\s*%)"
)
_FOOTNOTE = re.compile(r"[*†‡°^•·]+")

# Tokens that are punctuation or numbering rather than an ingredient.
_NOT_AN_INGREDIENT = re.compile(r"^[\W\d_]*$")

# Brands frequently print the claim itself inside the ingredient panel:
# "SANS PARABEN" closing a French list, "Sin parabenos" and "Parabeenvrij" in
# a six-language block. These are claims, not ingredients, and counting them
# as ingredients inflates every result that touches them.
_CLAIM_IN_LIST = re.compile(
    r"(?i)^(?:\[[^\]]*\]|\([^)]*\))?\s*(?:"
    r"(?:sans|sin|sem|senza|ohne|zonder|uten|no|without|free\s+from|"
    r"free\s+of|livre\s+de|libre\s+de)\b.*"
    # Dutch and German compound these onto the word with no space:
    # "Parabeenvrij", "Parabenfrei". No INCI name ends in any of them.
    r"|.*(?:free|frei|vrij|libre|fri)$"
    r"|.*\b(?:hypoallergenic|hipoalerg\w+|dermatologically\s+tested|"
    r"non[\s\-]?comedogenic|cruelty[\s\-]?free)\b.*"
    r")$"
)

_BRITISH = (
    ("sulphate", "sulfate"),
    ("sulphite", "sulfite"),
    ("sulphur", "sulfur"),
    ("colour", "color"),
    ("aluminium", "aluminum"),
    ("oestr", "estr"),
)


def normalise(name: str) -> str:
    """Fold one ingredient name to the form the family patterns expect."""
    # 70 records in a 2,554-product sample of real published lists carry
    # HTML entities, from pack text that went through a web form.
    text = html.unescape(name)
    text = unicodedata.normalize("NFKC", text)
    # Non-breaking and thin spaces are endemic in copy-pasted pack text.
    text = re.sub(r"[    ​]", " ", text)
    text = text.replace("’", "'").replace("‘", "'")
    # Unify the several dashes packs use inside names such as PEG-100.
    text = re.sub(r"[‐-―−]", "-", text)
    # OCR and copy-paste routinely put spaces around a hyphen that belongs
    # inside a name: "PEG - 100 Stearate", "Butyrosper - mum Parkii".
    text = re.sub(r"\s*-\s*", "-", text)
    text = text.casefold()
    for british, american in _BRITISH:
        text = text.replace(british, american)
    text = re.sub(r"\s+", " ", text).strip()
    return text.strip(" .,;:")


def extract(text: str) -> tuple[str, str, bool]:
    """Split label text into (ingredient block, everything else, found).

    When no preamble is present the whole text is treated as marketing copy
    and no ingredient list is reported. Guessing would be worse than
    admitting it: a run that quietly treats a paragraph of marketing as an
    ingredient list produces confident nonsense, and the caller has an
    explicit way to say "this file is the list" instead.
    """
    match = _PREAMBLE.search(text)
    if match is None:
        return "", text, False

    before = text[: match.start()]
    rest = text[match.end() :]

    end = _TERMINATOR.search(rest)
    inline = _INLINE_TERMINATOR.search(rest)
    if inline is not None and (end is None or inline.start() < end.start()):
        end = inline
    if end is not None:
        block, after = rest[: end.start()], rest[end.start() :]
    else:
        block, after = rest, ""

    if not block.strip():
        return "", text, False
    return block, (before + "\n" + after), True


def _split_top_level(block: str) -> list[str]:
    """Split on separators that are not inside brackets.

    "Butyrospermum Parkii (Shea, Karite) Butter" is one ingredient, and the
    comma inside the parentheses must not end it.
    """
    parts: list[str] = []
    buf: list[str] = []
    depth = 0
    for char in block:
        if char in "([{":
            depth += 1
            buf.append(char)
        elif char in ")]}":
            depth = max(0, depth - 1)
            buf.append(char)
        elif depth == 0 and (char in ",;\n\r" or char in "•·‣|"):
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(char)
    parts.append("".join(buf))
    return parts


def _clean(token: str) -> str:
    token = _ANNOTATION.sub(" ", token)
    token = _FOOTNOTE.sub(" ", token)
    token = re.sub(r"\s+", " ", token).strip()
    return token.strip(" .,;:-")


def parse(block: str) -> list[Ingredient]:
    """Turn an ingredient block into ingredients, in printed order."""
    sections: list[tuple[str, Position]] = []
    pieces = _MAY_CONTAIN.split(block)
    sections.append((pieces[0], "declared"))
    for piece in pieces[1:]:
        sections.append((piece, "may-contain"))

    out: list[Ingredient] = []
    for section, position in sections:
        index = 0
        for chunk in _split_top_level(section):
            for piece in _BLEND.split(chunk):
                for token in _SENTENCE.split(piece):
                    raw = _clean(token)
                    if not raw or _NOT_AN_INGREDIENT.match(raw):
                        continue
                    if _CLAIM_IN_LIST.search(raw):
                        continue
                    # A stray repeated preamble inside the block, common
                    # when a pack prints the list once per language.
                    if _PREAMBLE.fullmatch(raw + " ") or raw.casefold() in {
                        "ingredients", "ingredients list", "inci"
                    }:
                        continue
                    index += 1
                    out.append(
                        Ingredient(
                            raw=raw,
                            normalised=normalise(raw),
                            index=index,
                            position=position,
                        )
                    )
    return out


def looks_binary(text: str) -> bool:
    """Whether a block is bytes rather than a printed ingredient list.

    A binary file appended after an "Ingredients:" heading used to parse into
    junk tokens, match nothing, and be reported as no contradiction found --
    the most reassuring thing this tool can say, about a file it never read.
    """
    sample = text[:4000]
    if not sample:
        return False
    if "\x00" in sample:
        return True
    printable = sum(
        1 for ch in sample if ch.isprintable() or ch in "\t\n\r"
    )
    return printable / len(sample) < 0.85


def looks_like_a_list(text: str) -> bool:
    """Whether a bare block plausibly is an ingredient list.

    Used only to warn when the user passed marketing copy to --ingredients,
    never to decide silently that some text is a list.
    """
    stripped = text.strip()
    if len(stripped) < 20:
        return False
    commas = stripped.count(",")
    if commas < 3:
        return False
    head = normalise(stripped[:120])
    return bool(
        re.search(r"\b(?:aqua|water|eau|alcohol|glycerin|parfum|cyclo|"
                  r"sodium|cetearyl|butyrospermum|dimethicone)\b", head)
    ) or commas >= 6
