import unittest

from says_on_the_tin.check import check_label


def verdicts(report):
    return {f.claim.family: f.verdict for f in report.findings}


class Verdicts(unittest.TestCase):
    def test_a_plain_contradiction(self):
        r = check_label(
            "Paraben free.\nIngredients: Aqua, Methylparaben"
        )
        self.assertEqual(verdicts(r)["paraben"], "conflict")
        self.assertEqual(len(r.conflicts), 1)

    def test_nothing_matched_is_not_a_pass(self):
        r = check_label("Paraben free.\nIngredients: Aqua, Glycerin")
        finding = r.findings[0]
        self.assertEqual(finding.verdict, "no-conflict")
        # The wording has to stop a reader concluding the claim was verified.
        self.assertIn("not the same as the claim being true",
                      finding.explanation)

    def test_a_disputed_ingredient_is_a_review(self):
        r = check_label("Vegan.\nIngredients: Aqua, Squalane")
        self.assertEqual(verdicts(r)["vegan"], "review")
        self.assertTrue(r.findings[0].matches[0].caveat)

    def test_unverifiable_claims_are_reported_not_dropped(self):
        r = check_label(
            "Cruelty free and hypoallergenic.\nIngredients: Aqua"
        )
        self.assertEqual(
            {f.verdict for f in r.findings}, {"unverifiable"}
        )
        self.assertEqual(len(r.findings), 2)


class AbsentIsNotUnknown(unittest.TestCase):
    """The distinction the whole tool rests on."""

    def test_no_ingredient_list_means_not_checked_never_no_conflict(self):
        r = check_label("Paraben free, sulfate free, vegan.")
        self.assertFalse(r.ingredients_parsed)
        self.assertEqual(
            {f.verdict for f in r.findings if not
             f.claim.family.startswith("unverifiable")},
            {"not-checked"},
        )
        self.assertEqual(r.conflicts, [])

    def test_the_limit_says_so_in_words(self):
        r = check_label("Paraben free.")
        self.assertTrue(
            any("not the same as finding nothing wrong" in limit
                or "not actually been checked" in limit
                for limit in r.limits),
            r.limits,
        )

    def test_a_heading_with_an_empty_list_is_not_a_checked_list(self):
        r = check_label("Paraben free.\nIngredients:\n")
        self.assertFalse(r.ingredients_parsed)


class MayContain(unittest.TestCase):
    def test_a_colourant_in_may_contain_is_a_review_not_a_conflict(self):
        r = check_label(
            "Vegan.\nIngredients: Talc, Mica [+/-] CI 75470"
        )
        self.assertEqual(verdicts(r)["vegan"], "review")

    def test_the_same_colourant_declared_outright_is_a_conflict(self):
        r = check_label("Vegan.\nIngredients: Talc, CI 75470")
        self.assertEqual(verdicts(r)["vegan"], "conflict")

    def test_the_limit_is_stated(self):
        r = check_label("Vegan.\nIngredients: Talc [+/-] CI 75470")
        self.assertTrue(any("may contain" in limit for limit in r.limits))


class Exclusions(unittest.TestCase):
    def test_a_near_miss_is_reported_rather_than_dropped_silently(self):
        r = check_label(
            "Alcohol free.\nIngredients: Aqua, Cetearyl Alcohol"
        )
        self.assertEqual(verdicts(r)["alcohol"], "no-conflict")
        self.assertEqual(len(r.exclusions), 1)
        self.assertEqual(r.exclusions[0].ingredient.raw, "Cetearyl Alcohol")
        self.assertIn("fatty alcohol", r.exclusions[0].reason)

    def test_exclusions_are_only_reported_for_claims_actually_made(self):
        # Cetearyl Alcohol in a product making no alcohol claim is just an
        # ingredient, and saying anything about it would be noise.
        r = check_label("Vegan.\nIngredients: Aqua, Cetearyl Alcohol")
        self.assertEqual(r.exclusions, [])


class SeparateInputs(unittest.TestCase):
    def test_the_two_halves_can_be_passed_separately(self):
        r = check_label(
            ingredients_text="Aqua, Methylparaben, Glycerin, Parfum",
            claims_text="Paraben free",
        )
        self.assertEqual(verdicts(r)["paraben"], "conflict")

    def test_marketing_copy_passed_as_a_list_is_flagged(self):
        r = check_label(
            ingredients_text="Our finest shampoo. Try it today.",
            claims_text="Paraben free",
        )
        self.assertTrue(
            any("does not read like" in limit for limit in r.limits)
        )


if __name__ == "__main__":
    unittest.main()
