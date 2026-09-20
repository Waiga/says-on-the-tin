"""No punctuation dash reaches the reader, in any format the tool prints.

An em dash, an en dash or an ASCII " -- " reads as punctuation on the page.
They are not written in this project's output. A hyphen inside a word is
spelling, not punctuation: 'sulfate-free', 'may-contain', '1,4-dioxane' and
'Cetearyl Alcohol' are left alone, and so is the '-' that names standard
input on the command line, because it is an argument value rather than a
mark.

Two line shapes are syntax rather than punctuation and are excluded
deliberately: a markdown list bullet at the start of a line, and a rule line
of repeated hyphens. Everything after the bullet marker is still checked.

The fixtures below contain no dash of any kind, so any dash these renderers
produce is the tool's own punctuation and not an echo of its input.
"""

import json
import re
import unittest

from says_on_the_tin import report as report_mod
from says_on_the_tin.check import check_label
from says_on_the_tin.cli import build_parser

DASHES = {
    "‐": "hyphen U+2010",
    "‑": "non-breaking hyphen",
    "‒": "figure dash",
    "–": "en dash",
    "—": "em dash",
    "―": "horizontal bar",
    "−": "minus sign",
}
SPACED = {
    " -- ": "spaced double hyphen",
    " - ": "spaced hyphen",
}

_BULLET = re.compile(r"^[ \t]*-[ \t]")
_RULE = re.compile(r"^[ \t]*-{3,}[ \t]*$")


def offences(text):
    """Every punctuation dash in `text`, as readable descriptions."""
    found = []
    for number, line in enumerate(text.splitlines(), start=1):
        if _RULE.match(line):
            continue
        body = _BULLET.sub("", line, count=1)
        for mark, name in sorted(DASHES.items()):
            if mark in body:
                found.append(f"line {number}: {name} in {line!r}")
        for mark, name in sorted(SPACED.items()):
            if mark in body:
                found.append(f"line {number}: {name} in {line!r}")
    return found


def json_offences(text):
    """`render_json` escapes non-ASCII, so scan the decoded strings."""
    found = []

    def walk(node, path):
        if isinstance(node, str):
            for offence in offences(node):
                found.append(f"{path}: {offence}")
        elif isinstance(node, dict):
            for key, value in node.items():
                walk(key, f"{path}.{key}")
                walk(value, f"{path}.{key}")
        elif isinstance(node, list):
            for index, value in enumerate(node):
                walk(value, f"{path}[{index}]")

    walk(json.loads(text), "$")
    return found


CONTRADICTS_AND_MORE = (
    "Paraben free. Sulfate free. Silicone free. Alcohol free. Vegan.\n"
    "Cruelty free and dermatologically tested.\n"
    "\n"
    "Ingredients: Aqua, Sodium Laureth Sulfate, Methylparaben, Glycerin,\n"
    "Magnesium Sulfate, Cetearyl Alcohol, Squalane, Citric Acid,\n"
    "Parfum (Fragrance), Tocopherol, Xanthan Gum, Sodium Chloride"
)
MAY_CONTAIN = (
    "No artificial colours.\n"
    "Ingredients: Aqua, Glycerin.\n"
    "May contain: CI 77491, CI 77492, CI 77499."
)
NOTHING_MATCHED = "Paraben free. Vegan.\nIngredients: Aqua, Citric Acid"
NO_CLAIMS = "Ingredients: Aqua, Glycerin, Citric Acid"
UNREADABLE = "Paraben free.\nIngredients: \x00\x01\x02"


def reports():
    """One report per branch the renderers have to walk."""
    return {
        "contradictions, reviews, unverifiable and exclusions": check_label(
            CONTRADICTS_AND_MORE, source="label.txt"
        ),
        "a may contain block": check_label(MAY_CONTAIN, source="label.txt"),
        "nothing matched": check_label(NOTHING_MATCHED, source="label.txt"),
        "no claims at all": check_label(NO_CLAIMS, source="label.txt"),
        "claims with no ingredient list": check_label(
            claims_text="Paraben free. Sulfate free.", source="copy.txt"
        ),
        "an ingredient list that did not parse": check_label(
            UNREADABLE, source="label.txt"
        ),
        "no source given": check_label(CONTRADICTS_AND_MORE),
    }


RENDERERS = {
    "text": report_mod.render_text,
    "markdown": report_mod.render_markdown,
}


class NoDashReachesTheReader(unittest.TestCase):
    def test_the_fixtures_themselves_carry_no_dash(self):
        # Otherwise a clean run would only prove the input was clean.
        for name, fixture in (
            ("contradicts", CONTRADICTS_AND_MORE),
            ("may contain", MAY_CONTAIN),
            ("nothing matched", NOTHING_MATCHED),
            ("no claims", NO_CLAIMS),
        ):
            with self.subTest(fixture=name):
                self.assertEqual(offences(fixture), [])

    def test_text_and_markdown(self):
        for label, report in reports().items():
            for fmt, render in RENDERERS.items():
                with self.subTest(label=label, format=fmt):
                    self.assertEqual(offences(render(report)), [])

    def test_json(self):
        for label, report in reports().items():
            with self.subTest(label=label, format="json"):
                rendered = report_mod.render_json(report)
                self.assertEqual(json_offences(rendered), [])
                # The raw text carries — style escapes, so check it too.
                self.assertNotIn("\\u201", rendered)
                self.assertNotIn("\\u2212", rendered)

    def test_list_families(self):
        self.assertEqual(offences(report_mod.render_families()), [])

    def test_command_line_help(self):
        parser = build_parser()
        self.assertEqual(offences(parser.format_help()), [])
        self.assertEqual(offences(parser.format_usage()), [])

    def test_the_error_messages(self):
        parser = build_parser()
        for action in parser._actions:
            with self.subTest(option=action.dest):
                self.assertEqual(offences(action.help or ""), [])


class TheScanWouldCatchOne(unittest.TestCase):
    """The check above is worth nothing if it cannot fail."""

    def test_it_catches_each_mark(self):
        for mark in list(DASHES) + list(SPACED):
            with self.subTest(mark=mark):
                self.assertTrue(offences(f"a claim {mark} and its list"))

    def test_it_catches_a_dash_after_a_bullet_marker(self):
        self.assertTrue(offences("- Methylparaben — a paraben"))

    def test_it_reads_through_json_escaping(self):
        self.assertTrue(json_offences(json.dumps({"k": "a — b"})))

    def test_it_leaves_spelling_and_syntax_alone(self):
        for allowed in (
            "sulfate-free is a claim about detergents",
            "  - Only the 16 claim families were compared.",
            "1,4-dioxane in an ethoxylate is a lab question",
            "Cetearyl Alcohol, a fatty alcohol, is not counted",
            "| --- | --- |",
            "  -h, --help            show this help message and exit",
            "or '-' for standard input",
        ):
            with self.subTest(text=allowed):
                self.assertEqual(offences(allowed), [])


class CoverageOfTheRenderers(unittest.TestCase):
    """A scan proves nothing about a branch it never reached."""

    def test_every_verdict_and_section_is_exercised(self):
        seen = set()
        exclusions = 0
        caveats = 0
        for report in reports().values():
            seen.update(f.verdict for f in report.findings)
            exclusions += len(report.exclusions)
            caveats += sum(
                1 for f in report.findings for m in f.matches if m.caveat
            )
        self.assertEqual(
            seen,
            {
                "conflict",
                "review",
                "no-conflict",
                "unverifiable",
                "not-checked",
            },
        )
        self.assertTrue(exclusions, "no exclusion section was rendered")
        self.assertTrue(caveats, "no per match caveat was rendered")

    def test_every_documented_format_is_covered(self):
        choices = set()
        for action in build_parser()._actions:
            if action.dest == "format":
                choices = set(action.choices)
        self.assertEqual(choices, set(RENDERERS) | {"json"})


if __name__ == "__main__":
    unittest.main()
