import unittest

from says_on_the_tin.families import FAMILY_BY_KEY, FAMILIES, UNVERIFIABLE


def kind(family_key, ingredient):
    result = FAMILY_BY_KEY[family_key].classify(ingredient)
    return None if result is None else result[0]


class ClassicFalsePositives(unittest.TestCase):
    """Each of these is a way a naive checker loses its reader."""

    def test_fatty_alcohols_do_not_break_an_alcohol_free_claim(self):
        for name in ("cetyl alcohol", "cetearyl alcohol", "stearyl alcohol",
                     "behenyl alcohol", "myristyl alcohol", "lauryl alcohol"):
            with self.subTest(name=name):
                self.assertEqual(kind("alcohol", name), "excluded")

    def test_benzyl_alcohol_is_not_the_alcohol_in_alcohol_free(self):
        self.assertEqual(kind("alcohol", "benzyl alcohol"), "excluded")

    def test_inorganic_sulfate_salts_are_not_cleansing_sulfates(self):
        for name in ("magnesium sulfate", "zinc sulfate", "sodium sulfate",
                     "chondroitin sulfate"):
            with self.subTest(name=name):
                self.assertEqual(kind("sulfate", name), "excluded")

    def test_sulfoacetate_is_not_a_sulfate(self):
        self.assertEqual(
            kind("sulfate", "sodium lauryl sulfoacetate"), "excluded"
        )

    def test_silica_and_silicates_are_not_silicones(self):
        for name in ("silica", "hydrated silica", "silicon dioxide",
                     "magnesium aluminum silicate"):
            with self.subTest(name=name):
                self.assertEqual(kind("silicone", name), "excluded")

    def test_lactic_acid_and_allantoin_are_not_animal_derived(self):
        self.assertEqual(kind("vegan", "lactic acid"), "excluded")
        self.assertEqual(kind("vegan", "allantoin"), "excluded")

    def test_paraben_pattern_does_not_fire_on_other_ingredients(self):
        for name in ("phenoxyethanol", "sodium benzoate", "benzyl alcohol"):
            with self.subTest(name=name):
                self.assertIsNone(kind("paraben", name))

    def test_peg_pattern_does_not_fire_on_names_merely_containing_eth(self):
        for name in ("methylparaben", "ethylhexylglycerin", "dimethicone",
                     "methylisothiazolinone"):
            with self.subTest(name=name):
                self.assertIsNone(kind("peg", name))


class Members(unittest.TestCase):
    def test_parabens_including_salts(self):
        for name in ("methylparaben", "propylparaben", "butylparaben",
                     "sodium methylparaben"):
            with self.subTest(name=name):
                self.assertEqual(kind("paraben", name), "member")

    def test_cleansing_sulfates(self):
        for name in ("sodium lauryl sulfate", "sodium laureth sulfate",
                     "ammonium laureth sulfate", "tea-lauryl sulfate"):
            with self.subTest(name=name):
                self.assertEqual(kind("sulfate", name), "member")

    def test_silicones_by_suffix(self):
        for name in ("dimethicone", "amodimethicone", "cyclopentasiloxane",
                     "dimethiconol", "cetearyl methicone"):
            with self.subTest(name=name):
                self.assertEqual(kind("silicone", name), "member")

    def test_volatile_alcohols(self):
        for name in ("alcohol", "alcohol denat.", "sd alcohol 40", "ethanol",
                     "isopropyl alcohol"):
            with self.subTest(name=name):
                self.assertEqual(kind("alcohol", name), "member")

    def test_ethoxylates_and_pegs(self):
        for name in ("peg-100 stearate", "ppg-15 stearyl ether",
                     "ceteareth-20", "laureth-4", "polysorbate 80"):
            with self.subTest(name=name):
                self.assertEqual(kind("peg", name), "member")

    def test_animal_derived_for_vegan(self):
        # "hydrolyzed collagen" used to be asserted here as a member. It was
        # moved to disputed after a sample of real published lists showed
        # plant-hydrolysate and biotech collagen, elastin and keratin sold
        # under names that read identically on a pack. Calling those a
        # contradiction would be wrong.
        for name in ("carmine", "ci 75470", "cera alba", "beeswax", "lanolin",
                     "shellac", "guanine"):
            with self.subTest(name=name):
                self.assertEqual(kind("vegan", name), "member")


class RealWorldRegressions(unittest.TestCase):
    """Each of these came from a sample of 2,554 real published labels."""

    def test_a_name_that_disclaims_animal_origin_is_not_a_conflict(self):
        # Pacifica ships "Sr-Hydrozoan Polypeptide-1 (Vegan Collagen)".
        # The label already answered the question in the ingredient name.
        self.assertEqual(
            kind("vegan", "sr-hydrozoan polypeptide-1 (vegan collagen)"),
            "excluded",
        )

    def test_structural_proteins_are_reviews_not_conflicts(self):
        for name in ("hydrolyzed collagen", "keratin", "elastin"):
            with self.subTest(name=name):
                self.assertEqual(kind("vegan", name), "disputed")

    def test_cornsilk_is_not_silk(self):
        # "Zea Mays Silk (Cornsilk) Extract" is a plant. An independent pass
        # over the same corpus reported it as an animal product under a
        # vegan claim; it is maize.
        self.assertIsNone(
            kind("vegan", "zea mays silk (cornsilk) extract")
        )

    def test_sodium_caseinate_is_milk_derived(self):
        # A word-boundary pattern on "casein" missed the "-ate" form, which
        # is how it is actually printed.
        self.assertEqual(kind("vegan", "sodium caseinate"), "member")

    def test_the_common_printed_forms_of_fragrance(self):
        # In the sample, "Parfum (Fragrance)" and "Fragrance (Parfum)" were
        # far more common than the bare word, and an exact-match pattern
        # found none of them.
        for name in ("parfum", "parfum (fragrance)", "fragrance (parfum)",
                     "parfum/ fragrance", "parfum / fragrance"):
            with self.subTest(name=name):
                self.assertEqual(kind("fragrance", name), "member")

    def test_a_fragrant_ingredient_is_not_the_declared_entry(self):
        # The pattern must match the declared entry and nothing wider.
        for name in ("parfum de rose absolue", "sodium fragrance carrier"):
            with self.subTest(name=name):
                self.assertNotEqual(
                    (kind("fragrance", name) or ""), "member"
                )

    def test_sodium_coco_sulfate_is_a_review_not_a_conflict(self):
        # Members are tested before disputed entries, so a member pattern
        # broad enough to include "coco" would shadow the disputed one.
        self.assertEqual(kind("sulfate", "sodium coco-sulfate"), "disputed")

    def test_benzyl_alcohol_was_the_largest_source_of_false_alarms(self):
        # In the sample, benzyl/phenethyl alcohol produced 9 bogus
        # alcohol-free hits against 2 real ones.
        self.assertEqual(kind("alcohol", "benzyl alcohol"), "excluded")
        self.assertEqual(kind("alcohol", "phenethyl alcohol"), None)


class Disputed(unittest.TestCase):
    def test_squalane_is_a_review_not_a_conflict(self):
        self.assertEqual(kind("vegan", "squalane"), "disputed")

    def test_formaldehyde_releasers_are_reviews(self):
        for name in ("dmdm hydantoin", "diazolidinyl urea", "quaternium-15",
                     "bronopol"):
            with self.subTest(name=name):
                self.assertEqual(kind("formaldehyde", name), "disputed")

    def test_oats_are_a_review_under_gluten_free(self):
        self.assertEqual(kind("gluten", "avena sativa kernel flour"),
                         "disputed")

    def test_fragrance_allergen_without_parfum_is_a_review(self):
        self.assertEqual(kind("fragrance", "linalool"), "disputed")

    def test_unscented_treats_parfum_as_review_not_conflict(self):
        # An unscented product may carry a masking fragrance.
        self.assertEqual(kind("unscented", "parfum"), "disputed")
        self.assertEqual(kind("fragrance", "parfum"), "member")


class MultilingualClaims(unittest.TestCase):
    """Every contradiction in the real sample was tagged in a language other
    than English. An English-only claim detector found none of them."""

    def test_free_from_is_recognised_in_the_pack_languages(self):
        from says_on_the_tin.claims import find
        cases = [
            ("sem-parabenos", "paraben"),      # Portuguese
            ("livre-de-parabenos", "paraben"),
            ("sans paraben", "paraben"),       # French
            ("sin parabenos", "paraben"),      # Spanish
            ("ohne Parabene", "paraben"),      # German
            ("senza parabeni", "paraben"),     # Italian
            ("Parabeenvrij", "paraben"),       # Dutch, compounded
            ("Parabenfrei", "paraben"),        # German, compounded
            ("sem-sulfatos", "sulfate"),
            ("senza-sles", "sulfate"),
            ("sans-alcool", "alcohol"),
            ("sem-silicones", "silicone"),
            ("sem-fragrancia", "fragrance"),
        ]
        for text, family in cases:
            with self.subTest(text=text):
                self.assertIn(
                    family, {c.family for c in find(text)}, text
                )

    def test_a_qualified_claim_is_not_an_absolute_one(self):
        # "ohne rein synthetische Duftstoffe" is "no PURELY SYNTHETIC
        # fragrance". A product making it may lawfully contain a natural
        # aroma, so reading it as fragrance-free would be wrong.
        from says_on_the_tin.claims import find
        found = {c.family for c in find("ohne rein synthetische Duftstoffe")}
        self.assertNotIn("fragrance", found)


class Structure(unittest.TestCase):
    def test_every_family_has_a_way_to_be_matched(self):
        for family in FAMILIES:
            with self.subTest(family=family.key):
                self.assertTrue(family.members or family.disputed)
                self.assertTrue(family.claim_patterns)
                self.assertTrue(family.noun)

    def test_every_disputed_entry_explains_itself(self):
        # A review with no reason is just an unexplained warning.
        for family in FAMILIES:
            for member in family.disputed:
                with self.subTest(family=family.key, member=member.label):
                    self.assertTrue(member.caveat.strip())

    def test_every_exclusion_explains_itself(self):
        for family in FAMILIES:
            for excluded in family.excluded:
                with self.subTest(family=family.key):
                    self.assertTrue(excluded.reason.strip())

    def test_family_keys_are_unique(self):
        keys = [f.key for f in FAMILIES]
        self.assertEqual(len(keys), len(set(keys)))

    def test_every_unverifiable_class_explains_why(self):
        for entry in UNVERIFIABLE:
            with self.subTest(entry=entry.key):
                self.assertTrue(entry.patterns)
                self.assertGreater(len(entry.explanation), 40)


if __name__ == "__main__":
    unittest.main()
