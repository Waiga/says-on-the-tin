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
        # An independent pass over the same corpus called this an animal
        # product under a vegan claim. It is maize.
        #
        # The earlier version of this test used "(Cornsilk)" as one word,
        # where a bracket happened to block the silk pattern, so it passed
        # while the real INCI form -- "Zea Mays (Corn) Silk Extract" -- was
        # still reported as a contradiction. Both forms are checked now, and
        # the tool reports them as considered-and-not-counted rather than
        # silently ignoring them.
        for name in ("zea mays silk (cornsilk) extract",
                     "zea mays (corn) silk extract",
                     "corn silk extract"):
            with self.subTest(name=name):
                self.assertEqual(kind("vegan", name), "excluded")

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


class ReviewFindings(unittest.TestCase):
    """Raised by an independent adversarial review before publication."""

    def test_a_silicone_resin_is_not_shadowed_by_the_silicate_exclusion(self):
        # Exclusions are tested first, so "\w*silicate" swallowed
        # Trimethylsiloxysilicate -- a real silicone -- in 39 of the 2,554
        # corpus labels.
        self.assertEqual(kind("silicone", "trimethylsiloxysilicate"),
                         "member")
        self.assertEqual(kind("silicone", "polysilicone-11"), "member")
        self.assertEqual(kind("silicone", "silicone quaternium-16"),
                         "member")
        # and the exclusion still works on actual minerals
        self.assertEqual(kind("silicone", "magnesium aluminum silicate"),
                         "excluded")

    def test_family_gaps_the_review_found(self):
        for family, name in [
            ("soy", "glycine max"), ("soy", "soybean oil"),
            ("soy", "hydrolyzed soy protein"),
            ("nut", "prunus dulcis oil"), ("nut", "sweet almond oil"),
            ("nut", "castanea sativa seed extract"),
            ("mineral-oil", "paraffin wax"),
            ("mineral-oil", "petroleum jelly"),
            ("mineral-oil", "ceresin"),
            ("vegan", "gelatin"), ("vegan", "goat milk"),
            ("vegan", "honey extract"), ("vegan", "cera flava"),
            ("peg", "bis-peg-18 methyl ether dimethyl silane"),
            ("peg", "sodium peg-7 olive oil carboxylate"),
            ("sulfate", "sodium lauryl ether sulfate"),
            ("sulfate", "sodium dodecyl sulfate"),
            ("talc", "talc (magnesium silicate)"),
            ("alcohol", "alcohol (ethanol)"),
            ("paraben", "methyl 4-hydroxybenzoate"),
            ("formaldehyde", "tris(hydroxymethyl)nitromethane"),
            ("formaldehyde", "glyoxal"),
        ]:
            with self.subTest(family=family, name=name):
                self.assertIn(kind(family, name), ("member", "disputed"))

    def test_plant_milks_are_not_dairy(self):
        for name in ("avena sativa (oat) milk",
                     "cocos nucifera (coconut) milk protein",
                     "almond milk", "soy milk"):
            with self.subTest(name=name):
                self.assertEqual(kind("vegan", name), "excluded")

    def test_dairy_still_is(self):
        for name in ("hydrolyzed milk protein", "goat milk",
                     "sodium caseinate", "lactose"):
            with self.subTest(name=name):
                self.assertEqual(kind("vegan", name), "member")

    def test_bare_milk_in_a_sentence_is_not_an_ingredient_match(self):
        # From a real panel: "if swallowed give a glass of water or milk".
        self.assertIsNone(
            kind("vegan", "if swallowed give glass of water or milk and call")
        )

    def test_paraffinum_liquidum_is_still_matched_once(self):
        self.assertEqual(kind("mineral-oil", "paraffinum liquidum"),
                         "member")


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


class CoordinatedClaims(unittest.TestCase):
    """One negation routinely governs a list of nouns. Binding it to a single
    noun found only one claim per sentence, so a label with four
    contradictions reported two -- which reads as a pass on the other two."""

    def test_a_negation_governs_the_whole_list_after_it(self):
        from says_on_the_tin.claims import find
        found = {c.family for c in
                 find("Free from parabens, sulphates and silicones.")}
        self.assertEqual(found, {"paraben", "sulfate", "silicone"})

    def test_a_colon_does_not_break_a_free_from_panel(self):
        # "FREE FROM:" bullet panels are ubiquitous on packs.
        from says_on_the_tin.claims import find
        found = {c.family for c in
                 find("Free from: Parabens, Sulfates, Silicones")}
        self.assertEqual(found, {"paraben", "sulfate", "silicone"})

    def test_a_trailing_free_governs_the_list_before_it(self):
        from says_on_the_tin.claims import find
        found = {c.family for c in find("Paraben & sulfate free")}
        self.assertEqual(found, {"paraben", "sulfate"})

    def test_a_negation_does_not_reach_past_a_sentence(self):
        from says_on_the_tin.claims import find
        found = {c.family for c in find("Contains silicone. Paraben free.")}
        self.assertEqual(found, {"paraben"})

    def test_an_unrelated_no_is_not_a_claim(self):
        from says_on_the_tin.claims import find
        self.assertEqual(find("No more frizz. Nourishes with shea."), [])

    def test_no_colour_transfer_is_not_a_colourant_claim(self):
        # A wear claim on nearly every long-wear lipstick. Reading it as
        # dye-free is a false accusation against a legitimate CI list.
        from says_on_the_tin.claims import find
        self.assertEqual(
            find("Matte Lipstick. No colour transfer, 12 hour wear."), []
        )

    def test_no_artificial_colours_is_still_a_colourant_claim(self):
        from says_on_the_tin.claims import find
        found = {c.family for c in find("No artificial colours added.")}
        self.assertEqual(found, {"dye"})

    def test_a_qualifier_before_the_noun_narrows_the_claim(self):
        from says_on_the_tin.claims import find
        self.assertEqual(find("No synthetic fragrance"), [])
        self.assertEqual(find("ohne rein synthetische Duftstoffe"), [])

    def test_but_no_added_fragrance_is_absolute(self):
        from says_on_the_tin.claims import find
        found = {c.family for c in find("No added fragrance")}
        self.assertEqual(found, {"fragrance"})


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
                # A family is claimable either through nouns a negation can
                # attach to, or through a standalone pattern like "vegan".
                self.assertTrue(family.claim_tokens or family.claim_patterns)
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
