"""Regression: WebView2 est initialise sur Form.Shown, pas dans __init__."""
import unittest
from scripts.patch_webview_startup import ORIGINAL, PATCHED, patch_source


class WebView2ShownPatchTests(unittest.TestCase):
    def test_patches_only_constructor_and_preserves_other_logic(self):
        source = "before\n" + ORIGINAL + "\nafter\n"
        patched = patch_source(source)
        self.assertEqual(patched, "before\n" + PATCHED + "\nafter\n")
        self.assertIn("self.form.BeginInvoke(Action(self._initialize_after_first_paint))", patched)
        self.assertIn("self.form.Shown += self._initialize_when_shown", patched)
        self.assertEqual(patch_source(patched), patched)

    def test_fails_closed_for_unrecognized_upstream(self):
        with self.assertRaises(RuntimeError):
            patch_source("new upstream API")
        with self.assertRaises(RuntimeError):
            patch_source(ORIGINAL + ORIGINAL)


if __name__ == "__main__":
    unittest.main()
