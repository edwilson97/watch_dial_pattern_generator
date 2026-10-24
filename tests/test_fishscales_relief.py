"""Regression tests for Fish Scales relief geometry."""
import unittest
import numpy as np
from dial_patterns import render, PATTERN_FIELDS, FIELD_SPECS


class FishScalesTests(unittest.TestCase):
    def test_new_controls_registered(self):
        self.assertIn('fishscales_style', PATTERN_FIELDS['fishscales'])
        self.assertIn('fishscales_style', FIELD_SPECS)

    def test_relief_styles_have_expected_midtone_behavior(self):
        engraved, _ = render(pattern='fishscales', pixels=256, fishscales_style='engraved')
        faceted, _ = render(pattern='fishscales', pixels=256, fishscales_style='faceted')
        rounded, _ = render(pattern='fishscales', pixels=256, fishscales_style='rounded')
        e = engraved.astype(np.int32)
        f = faceted.astype(np.int32)
        r = rounded.astype(np.int32)
        e_mid = np.mean((e > 8000) & (e < 56000))
        f_mid = np.mean((f > 8000) & (f < 56000))
        r_mid = np.mean((r > 8000) & (r < 56000))
        self.assertLess(e_mid, f_mid)
        self.assertLess(e_mid, r_mid)
        self.assertFalse(np.array_equal(engraved, faceted))
        self.assertFalse(np.array_equal(faceted, rounded))

    def test_line_style_still_has_deep_recesses(self):
        arr, _ = render(pattern='fishscales', pixels=256, fishscales_style='engraved')
        self.assertGreater(np.mean(arr < 3000), 0.015)

if __name__ == '__main__':
    unittest.main()
