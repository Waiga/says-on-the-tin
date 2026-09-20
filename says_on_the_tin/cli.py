"""Command line entry point."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from says_on_the_tin import __version__, report as report_mod
from says_on_the_tin.check import check_label

# 0  nothing contradicted
# 1  at least one contradiction between a claim and the ingredient list
# 2  the check could not be carried out: unreadable input, or claims were
#    found with no ingredient list to check them against. Exiting 0 there
#    would let a CI job go green over a label nothing was compared to,
#    which is the one thing this tool exists not to do.
EXIT_OK = 0
EXIT_CONFLICT = 1
EXIT_ERROR = 2


def _read(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    # Real label text is copied out of PDFs, spreadsheets and web pages, and
    # arrives with whatever encoding that produced. Refusing to open it is
    # worse than reading it imperfectly and saying so.
    return Path(path).read_text(encoding="utf-8", errors="replace")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="says-on-the-tin",
        description=(
            "Find where a cosmetic label contradicts itself: a free-from "
            "claim on the front, and an ingredient on the back that breaks "
            "it. Runs entirely on your machine."
        ),
        epilog=(
            "Exit codes: 0 nothing contradicted, 1 at least one "
            "contradiction, 2 could not run."
        ),
    )
    parser.add_argument(
        "label",
        nargs="?",
        help=(
            "File containing the label text, or '-' for standard input. The "
            "file may hold the marketing copy and the ingredient list "
            "together, as copied from a product page."
        ),
    )
    parser.add_argument(
        "--ingredients",
        metavar="FILE",
        help="File holding only the ingredient list, or '-' for stdin.",
    )
    parser.add_argument(
        "--claims",
        metavar="FILE",
        help="File holding only the marketing copy, or '-' for stdin.",
    )
    parser.add_argument(
        "--format",
        choices=("text", "markdown", "json"),
        default="text",
        help="Output format. Default: text.",
    )
    parser.add_argument(
        "--list-families",
        action="store_true",
        help=(
            "Print every claim family this tool knows and what it counts, "
            "then exit."
        ),
    )
    parser.add_argument(
        "--version", action="version", version=f"says-on-the-tin {__version__}"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.list_families:
        sys.stdout.write(report_mod.render_families())
        return EXIT_OK

    if args.label and (args.ingredients or args.claims):
        parser.error(
            "give either a single label file or --ingredients/--claims, "
            "not both"
        )
    if not args.label and not (args.ingredients or args.claims):
        parser.error(
            "nothing to check: pass a label file, '-' for standard input, or "
            "--ingredients/--claims"
        )
    if [args.label, args.ingredients, args.claims].count("-") > 1:
        parser.error("standard input can only be read once")

    try:
        if args.label:
            text = _read(args.label)
            source = "standard input" if args.label == "-" else args.label
            result = check_label(text, source=source)
        else:
            ingredients = _read(args.ingredients) if args.ingredients else ""
            claims = _read(args.claims) if args.claims else ""
            source = args.claims or args.ingredients or ""
            result = check_label(
                ingredients_text=ingredients,
                claims_text=claims,
                source=source,
            )
    except OSError as exc:
        sys.stderr.write(f"says-on-the-tin: cannot read input: {exc}\n")
        return EXIT_ERROR

    renderers = {
        "text": report_mod.render_text,
        "markdown": report_mod.render_markdown,
        "json": report_mod.render_json,
    }
    # A label may legitimately contain characters the terminal encoding
    # cannot represent. Losing a character is acceptable; failing the run
    # over it is not.
    output = renderers[args.format](result)
    sys.stdout.buffer.write(
        output.encode(sys.stdout.encoding or "utf-8", errors="backslashreplace")
    )
    sys.stdout.buffer.write(b"\n")

    if result.conflicts:
        return EXIT_CONFLICT
    if any(f.verdict == "not-checked" for f in result.findings):
        return EXIT_ERROR
    return EXIT_OK
