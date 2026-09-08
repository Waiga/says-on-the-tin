# Contributing

Contributions should improve evidence quality, reproducibility, failure safety, or
clarity. More rules and more output are not automatically improvements.

## Setup

```bash
python3 -m pip install --no-deps .
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
```

## Change standard

1. Start from a scoped issue or explain the observed user problem in the pull request.
2. Add a failing test for behavior changes.
3. Make the smallest implementation that passes the test.
4. Run the full suite.
5. Update documentation when commands, evidence, limitations, or output change.
6. Disclose material AI assistance and confirm that you reviewed the resulting change.

no earlier pattern already covers. That contract is deliberately exhaustive and compared
in file order, so a new pattern without a probe, or a probe in the wrong position, fails
the suite. It exists because the patterns that keep scan output and cached responses out
of the repository were previously unguarded, and a dropped line would not have failed
anything.

rather than trying to recognise every equivalent way of writing it, because four
attempts to infer the property by parsing were each defeated by a formulation the
previous one had not anticipated, twice by silently accepting a disabled workflow. Any
edit therefore fails the suite on purpose, and the failure prints the diff.

## Where to start

and the exact shortfall, so it can be picked up without further discovery work.

## Review expectations

Maintenance is best effort by a single maintainer working in a weekly review block, so a
response can take days. Small, tested, single-purpose changes are reviewed fastest.

Never include credentials, private data, copied proprietary code, or unlicensed assets.
Reviewers may close changes that manufacture activity, inflate claims, or expand scope
without evidence.
