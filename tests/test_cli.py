import contextlib
import io
import json
import os
import tempfile
import unittest

from says_on_the_tin.cli import EXIT_CONFLICT, EXIT_ERROR, EXIT_OK, main


def run(argv):
    """Run the CLI and return (exit code, stdout, stderr).

    The CLI writes bytes to stdout.buffer, so the fake stdout needs a real
    binary buffer underneath. The TextIOWrapper is detached before it goes
    out of scope, because closing it would close the buffer we still have to
    read.
    """
    raw, err = io.BytesIO(), io.StringIO()
    stdout = io.TextIOWrapper(raw, encoding="utf-8", newline="")
    try:
        with contextlib.redirect_stdout(stdout), \
                contextlib.redirect_stderr(err):
            code = main(argv)
        stdout.flush()
    finally:
        stdout.detach()
    return code, raw.getvalue().decode("utf-8"), err.getvalue()


def write(text):
    handle = tempfile.NamedTemporaryFile(
        "w", suffix=".txt", delete=False, encoding="utf-8"
    )
    handle.write(text)
    handle.close()
    return handle.name


CONTRADICTS = "Paraben free.\nIngredients: Aqua, Methylparaben, Glycerin"
CLEAN = "Paraben free.\nIngredients: Aqua, Glycerin, Citric Acid"


class ExitCodes(unittest.TestCase):
    def test_a_contradiction_exits_one(self):
        path = write(CONTRADICTS)
        self.addCleanup(os.unlink, path)
        code, out, _ = run([path])
        self.assertEqual(code, EXIT_CONFLICT)
        self.assertIn("CONTRADICTIONS", out)

    def test_no_contradiction_exits_zero(self):
        path = write(CLEAN)
        self.addCleanup(os.unlink, path)
        code, _, _ = run([path])
        self.assertEqual(code, EXIT_OK)

    def test_an_unreadable_file_exits_two(self):
        code, _, err = run(["/definitely/not/here.txt"])
        self.assertEqual(code, EXIT_ERROR)
        self.assertIn("cannot read input", err)


class Formats(unittest.TestCase):
    def test_json_is_valid_and_carries_the_verdicts(self):
        path = write(CONTRADICTS)
        self.addCleanup(os.unlink, path)
        _, out, _ = run([path, "--format", "json"])
        payload = json.loads(out)
        self.assertEqual(payload["tool"], "says-on-the-tin")
        self.assertEqual(payload["findings"][0]["verdict"], "conflict")
        self.assertTrue(payload["ingredients_parsed"])

    def test_markdown_renders(self):
        path = write(CONTRADICTS)
        self.addCleanup(os.unlink, path)
        _, out, _ = run([path, "--format", "markdown"])
        self.assertIn("## Contradictions", out)

    def test_list_families_needs_no_input(self):
        code, out, _ = run(["--list-families"])
        self.assertEqual(code, EXIT_OK)
        self.assertIn("paraben", out)
        self.assertIn("deliberately not counted", out)


class Usage(unittest.TestCase):
    def test_no_arguments_is_an_error_not_an_empty_pass(self):
        with self.assertRaises(SystemExit) as raised:
            run([])
        self.assertNotEqual(raised.exception.code, 0)

    def test_a_label_file_and_split_inputs_together_is_rejected(self):
        with self.assertRaises(SystemExit):
            run(["a.txt", "--ingredients", "b.txt"])

    def test_stdin_cannot_be_read_twice(self):
        with self.assertRaises(SystemExit):
            run(["--ingredients", "-", "--claims", "-"])


class Encoding(unittest.TestCase):
    def test_undecodable_bytes_do_not_stop_the_run(self):
        handle = tempfile.NamedTemporaryFile(suffix=".txt", delete=False)
        handle.write(
            "Paraben free.\nIngredients: Aqua, M\xe9thylparaben".encode(
                "latin-1"
            )
        )
        handle.close()
        self.addCleanup(os.unlink, handle.name)
        code, out, _ = run([handle.name])
        self.assertIn(code, (EXIT_OK, EXIT_CONFLICT))
        self.assertIn("says-on-the-tin", out)


if __name__ == "__main__":
    unittest.main()
