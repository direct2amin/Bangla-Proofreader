"""Unit tests for Bijoy-to-Unicode conversion and Arabic script preservation."""

import unittest
from app.utils.bijoy_converter import convert_bijoy_to_unicode, is_bijoy_text


class TestBijoyConverter(unittest.TestCase):

    def test_is_bijoy_text_positive(self):
        bijoy_samples = [
            "Avgvi †mvbvi evsjv",
            "evsjv‡`k",
            "AvšÍR©vwZK gvZ…fvlv w`em",
            "cÖ_g wk¶v",
            "hy³ivóª",
            "Kg©KZ©vi",
        ]
        for s in bijoy_samples:
            self.assertTrue(is_bijoy_text(s), f"Should identify as Bijoy: {s}")

    def test_is_bijoy_text_negative_unicode(self):
        unicode_samples = [
            "আমার সোনার বাংলা",
            "বাংলাদেশ",
            "আন্তর্জাতিক মাতৃভাষা দিবস",
            "প্রথম শিক্ষা",
        ]
        for s in unicode_samples:
            self.assertFalse(is_bijoy_text(s), f"Should NOT identify Unicode Bengali as Bijoy: {s}")

    def test_is_bijoy_text_negative_english_and_arabic(self):
        other_samples = [
            "",
            "   ",
            "Hello world! This is a test.",
            "Quick brown fox jumps over the lazy dog.",
            "قال رسول الله صلى الله عليه وسلم",
            "Hello https://google.com world",
        ]
        for s in other_samples:
            self.assertFalse(is_bijoy_text(s), f"Should NOT identify as Bijoy: {s}")

    def test_bijoy_to_unicode_common_phrases(self):
        cases = [
            ("Avgvi †mvbvi evsjv", "আমার সোনার বাংলা"),
            ("evsjv‡`k", "বাংলাদেশ"),
            ("AvšÍR©vwZK gvZ…fvlv w`em", "আন্তর্জাতিক মাতৃভাষা দিবস"),
            ("cÖ_g wk¶v", "প্রথম শিক্ষা"),
            ("hy³ivóª", "যুক্তরাষ্ট্র"),
            ("Kg©KZ©vi", "কর্মকর্তার"),
        ]
        for bijoy, expected in cases:
            converted = convert_bijoy_to_unicode(bijoy)
            self.assertEqual(converted, expected, f"Failed for {bijoy}: got {converted}, expected {expected}")

    def test_arabic_script_preservation(self):
        arabic_text = "قال رسول الله ﷺ: «إِنَّمَا الأَعْمَالُ بِالنِّيَّاتِ»"
        mixed_input = f"Avgvi †mvbvi evsjv {arabic_text} evsjv‡`k"
        converted = convert_bijoy_to_unicode(mixed_input)

        self.assertIn(arabic_text, converted, "Arabic text with diacritics must remain 100% unaltered")
        self.assertTrue(converted.startswith("আমার সোনার বাংলা"))
        self.assertTrue(converted.endswith("বাংলাদেশ"))

    def test_url_and_email_preservation(self):
        url = "https://example.com/api/test?query=abc#section"
        email = "support-team@test.org"
        mixed_input = f"Avgvi mvBU {url} Ges B‡gBj {email} wVK Av‡Q"
        converted = convert_bijoy_to_unicode(mixed_input)

        self.assertIn(url, converted, "URL must remain completely untouched")
        self.assertIn(email, converted, "Email must remain completely untouched")
        self.assertIn("আমার", converted)

    def test_digits_conversion(self):
        bijoy_digits = "1234567890"
        expected = "১২৩৪৫৬৭৮৯০"
        self.assertEqual(convert_bijoy_to_unicode(bijoy_digits), expected)

    def test_engine_manager_auto_converts_bijoy(self):
        from unittest.mock import MagicMock
        from app.core.engine_manager import EngineManager

        mgr = EngineManager()
        mgr.mode = "online"
        mgr.gemini_engine = MagicMock()
        mgr.gemini_engine.is_available.return_value = True
        mgr.gemini_engine.proofread.return_value = "আমার সোনার বাংলা"

        bijoy_input = "Avgvi †mvbvi evsjv"
        result = mgr.proofread(bijoy_input)

        # Ensure the engine received converted Unicode, not raw Bijoy
        mgr.gemini_engine.proofread.assert_called_once_with("আমার সোনার বাংলা")
        self.assertEqual(result, "আমার সোনার বাংলা")

    def test_jsx_ported_dictionaries_and_helpers(self):
        from app.utils.bijoy_converter import (
            preConversionMap,
            conversionMap,
            proConversionMap,
            postConversionMap,
            reph,
            swapHalant,
            swapRa,
            preKars,
            nukta,
            convert,
        )

        self.assertIsInstance(preConversionMap, dict)
        self.assertIsInstance(conversionMap, dict)
        self.assertIsInstance(proConversionMap, dict)
        self.assertIsInstance(postConversionMap, dict)

        # Verify individual algorithmic helpers
        self.assertEqual(reph("কর্"), "র্ক")
        self.assertEqual(swapHalant("কা্ম"), "ক্মা")
        self.assertEqual(swapRa("র্া"), "ার্")
        self.assertEqual(preKars("েকা"), "কো")
        self.assertEqual(preKars("েকৗ"), "কৌ")
        self.assertEqual(nukta("ঁা"), "াঁ")
        self.assertEqual(convert("Avgvi †mvbvi evsjv"), "আমার সোনার বাংলা")


if __name__ == '__main__':
    unittest.main()

