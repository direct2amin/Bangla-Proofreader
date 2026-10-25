"""Unit tests for word-level diff calculation."""

import unittest
from app.utils.diff_highlighter import DiffHighlighter, tokenize


class TestDiffHighlighter(unittest.TestCase):
    def test_tokenize_bangla(self):
        text = "আমি বাংলায় গান গাই।"
        tokens = tokenize(text)
        self.assertEqual("".join(tokens), text)
        self.assertIn("আমি", tokens)
        self.assertIn("বাংলায়", tokens)
        self.assertIn("গান", tokens)
        self.assertIn("গাই", tokens)
        self.assertIn("।", tokens)

    def test_diff_replacement(self):
        orig = "আমি বাংল দেশ কে ভালবসি।"
        corr = "আমি বাংলাদেশকে ভালোবাসি।"
        res = DiffHighlighter.compute_diff(orig, corr)

        self.assertGreater(res.stats["total_changes"], 0)
        self.assertIn("diff-del", res.original_html)
        self.assertIn("diff-ins", res.corrected_html)
        self.assertEqual(res.corrected_text, corr)

    def test_diff_identical(self):
        text = "বাংলাদেশ একটি সুন্দর দেশ।"
        res = DiffHighlighter.compute_diff(text, text)
        self.assertEqual(res.stats["total_changes"], 0)
        self.assertNotIn("diff-del", res.original_html)
        self.assertNotIn("diff-ins", res.corrected_html)

    def test_word_by_word_granularity(self):
        orig = "তথ্য সম্বলিত ডায়েরী মত তা‘আলা হক্ব বলবো ইনশা-আল্লাহ"
        corr = "তথ্যসম্বলিত ডায়েরি মতো তাআলা হক বলব ইনশাআল্লাহ"
        res = DiffHighlighter.compute_diff(orig, corr)

        # Ensure changes are strictly word-by-word
        orig_words = [c.original for c in res.changes]
        self.assertIn("তথ্য সম্বলিত", orig_words)
        self.assertIn("ডায়েরী", orig_words)
        self.assertIn("বলবো", orig_words)
        self.assertIn("ইনশা-আল্লাহ", orig_words)
        self.assertNotIn("তথ্য সম্বলিত ডায়েরী", orig_words)
        self.assertNotIn("বলবো ইনশা-আল্লাহ", orig_words)


if __name__ == "__main__":
    unittest.main()
