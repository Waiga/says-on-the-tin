import unittest

from says_on_the_tin.ingredients import (
    extract,
    looks_like_a_list,
    normalise,
    parse,
)


class Normalise(unittest.TestCase):
    def test_folds_british_spelling(self):
        self.assertEqual(normalise("Sodium Laureth Sulphate"),
                         "sodium laureth sulfate")

    def test_collapses_non_breaking_and_thin_spaces(self):
        self.assertEqual(normalise("PEG -​100  Stearate"),
                         "peg-100 stearate")

    def test_unifies_dashes(self):
        # Packs use en dashes and minus signs inside numbered INCI names.
        self.assertEqual(normalise("Ceteareth–20"), "ceteareth-20")

    def test_strips_trailing_punctuation(self):
        self.assertEqual(normalise("Parfum."), "parfum")


class Extract(unittest.TestCase):
    def test_finds_english_preamble(self):
        block, rest, found = extract("Lovely cream.\nIngredients: Aqua, Glycerin")
        self.assertTrue(found)
        self.assertIn("Aqua", block)
        self.assertIn("Lovely cream", rest)

    def test_finds_non_english_preambles(self):
        for word in ("Ingrédients", "Inhaltsstoffe", "Ingredienti",
                     "Ingredientes", "Composition", "INCI"):
            with self.subTest(word=word):
                _, _, found = extract(f"{word}: Aqua, Glycerin")
                self.assertTrue(found)

    def test_stops_at_the_next_panel(self):
        block, rest, _ = extract(
            "Ingredients: Aqua, Glycerin\nDirections: apply to wet hair"
        )
        self.assertNotIn("wet hair", block)
        self.assertIn("wet hair", rest)

    def test_absent_preamble_is_reported_not_guessed(self):
        # Treating marketing copy as an ingredient list would produce
        # confident nonsense, so the tool declines rather than guesses.
        block, rest, found = extract("Paraben free, vegan, cruelty free.")
        self.assertFalse(found)
        self.assertEqual(block, "")
        self.assertIn("Paraben free", rest)

    def test_heading_with_nothing_under_it_is_not_a_list(self):
        _, _, found = extract("Ingredients:\n")
        self.assertFalse(found)


class Parse(unittest.TestCase):
    def test_comma_inside_parentheses_does_not_split(self):
        items = parse("Butyrospermum Parkii (Shea, Karite) Butter, Aqua")
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0].raw,
                         "Butyrospermum Parkii (Shea, Karite) Butter")

    def test_blend_notation_is_two_ingredients(self):
        items = parse("Glycerin (and) Cetearyl Alcohol")
        self.assertEqual([i.raw for i in items],
                         ["Glycerin", "Cetearyl Alcohol"])

    def test_may_contain_block_is_marked(self):
        items = parse("CI 19140 [+/-] CI 77491, CI 75470")
        self.assertEqual(items[0].position, "declared")
        self.assertEqual([i.position for i in items[1:]],
                         ["may-contain", "may-contain"])

    def test_may_contain_written_in_words(self):
        items = parse("Talc, Mica. May contain: CI 77491")
        self.assertEqual(items[-1].position, "may-contain")

    def test_percentage_and_footnote_annotations_are_stripped(self):
        items = parse("Aloe Barbadensis Leaf Juice*, Retinol 0.3%")
        self.assertEqual([i.raw for i in items],
                         ["Aloe Barbadensis Leaf Juice", "Retinol"])

    def test_bullets_and_semicolons_separate(self):
        items = parse("Aqua; Glycerin • Parfum")
        self.assertEqual(len(items), 3)

    def test_slash_names_stay_whole(self):
        # "Aqua/Water/Eau" is one ingredient printed in three languages.
        items = parse("Aqua/Water/Eau, Glycerin")
        self.assertEqual(items[0].raw, "Aqua/Water/Eau")

    def test_index_is_one_based_within_its_section(self):
        items = parse("Aqua, Glycerin [+/-] CI 77491")
        self.assertEqual((items[0].index, items[1].index), (1, 2))
        self.assertEqual(items[2].index, 1)

    def test_empty_and_punctuation_only_tokens_are_dropped(self):
        items = parse("Aqua, , . , Glycerin")
        self.assertEqual(len(items), 2)


class RealWorldRegressions(unittest.TestCase):
    """Each of these came from a sample of 2,554 real published labels."""

    def test_html_entities_are_decoded(self):
        # 70 of 2,554 real records carried entities from a web form.
        self.assertEqual(normalise("&lt;5% jab&oacute;n"), "<5% jabón")

    def test_ocr_hyphen_spacing_is_closed_up(self):
        self.assertEqual(normalise("Butyrosper - mum Parkii"),
                         "butyrosper-mum parkii")
        self.assertEqual(normalise("PEG - 100 Stearate"), "peg-100 stearate")

    def test_claims_printed_inside_the_panel_are_not_ingredients(self):
        # Brands close a list with the claim itself. Counting "SANS PARABEN"
        # as an ingredient inflated paraben findings from 5 to 16 in the
        # sample.
        items = parse(
            "Aqua, Glycerin, SANS PARABEN, Sin parabenos, Parabeenvrij, "
            "Hypoallergenic, Parfum"
        )
        self.assertEqual([i.raw for i in items], ["Aqua", "Glycerin", "Parfum"])

    def test_bullet_middot_and_pipe_separators(self):
        # All three appear in real exports.
        self.assertEqual(
            len(parse("AQUA / WATER / EAU • PARAFFIN • POTASSIUM")), 3
        )
        self.assertEqual(len(parse("Kernel Oil · Hydrolyzed Jojoba")), 2)
        self.assertEqual(len(parse("Water/Aqua|Beeswax/Cera Alba")), 2)

    def test_may_contain_written_with_a_bracketed_prefix(self):
        items = parse("Mica, [+/- MAY CONTAIN: CI 77499, CI 77891]")
        self.assertEqual(items[0].position, "declared")
        self.assertTrue(all(i.position == "may-contain" for i in items[1:]))

    def test_french_may_contain(self):
        items = parse("Talc. Peut contenir : CI 15880")
        self.assertEqual(items[-1].position, "may-contain")


class LooksLikeAList(unittest.TestCase):
    def test_marketing_copy_is_rejected(self):
        self.assertFalse(
            looks_like_a_list("Our best shampoo yet. Try it today!")
        )

    def test_real_list_is_accepted(self):
        self.assertTrue(
            looks_like_a_list("Aqua, Glycerin, Parfum, Citric Acid")
        )


if __name__ == "__main__":
    unittest.main()
