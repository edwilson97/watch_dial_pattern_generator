"""Geometry-specific regression checks for true Asanoha and rhombille cubes."""
import unittest
import numpy as np
from dial_patterns import render, PATTERN_FIELDS, FIELD_SPECS


class LatticeGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.asanoha, _ = render(pattern='asanoha', pixels=512, size_mm=8, pitch_mm=.8)
        cls.cubes, _ = render(pattern='isometriccubes', pixels=512, size_mm=8, pitch_mm=.8)

    def test_different_patterns_not_aliases(self):
        a = self.asanoha.astype(np.float32) / 65535
        b = self.cubes.astype(np.float32) / 65535
        self.assertGreater(float(np.mean(np.abs(a - b))), .10)
        self.assertFalse(np.array_equal(self.asanoha, self.cubes))

    def test_asanoha_has_true_relief_beyond_the_grooves(self):
        a = self.asanoha.astype(np.int32)
        self.assertGreater(float(np.mean(a > 52000)), .08)
        self.assertGreater(float(np.mean(a < 4000)), .03)
        mids = a[(a > 8000) & (a < 56000)]
        self.assertGreater(mids.size, a.size * 0.18)
        self.assertGreater(float(np.std(mids)), 7000.0)

    def test_cubes_have_three_distinct_terraces(self):
        h = self.cubes
        expected = [1.0, .72, .44]
        for height in expected:
            self.assertGreater(float(np.mean(abs(h.astype(np.int32) - int(height * 65535)) < 10)), .05)

    def test_new_controls_registered(self):
        for name, fields in [('asanoha',('line_width_mm','asanoha_style')),
                             ('isometriccubes',('cube_gap_mm','cube_step_fraction'))]:
            for field in fields:
                self.assertIn(field, PATTERN_FIELDS[name])
                self.assertIn(field, FIELD_SPECS)

    def test_line_width_and_cube_gap_control_geometry(self):
        a, _ = render(pattern='asanoha', pixels=256, line_width_mm=.04)
        b, _ = render(pattern='asanoha', pixels=256, line_width_mm=.12)
        self.assertGreater(np.count_nonzero(b < 3000), np.count_nonzero(a < 3000))
        a, _ = render(pattern='isometriccubes', pixels=256, cube_gap_mm=.02)
        b, _ = render(pattern='isometriccubes', pixels=256, cube_gap_mm=.12)
        self.assertGreater(np.count_nonzero(b < 3000), np.count_nonzero(a < 3000))

    def test_cube_step_changes_face_heights(self):
        a, _ = render(pattern='isometriccubes', pixels=256, cube_step_fraction=.1)
        b, _ = render(pattern='isometriccubes', pixels=256, cube_step_fraction=.4)
        self.assertFalse(np.array_equal(a, b))


    def test_asanoha_style_modes_have_expected_depth_behavior(self):
        engraved, _ = render(pattern='asanoha', pixels=256, asanoha_style='engraved')
        faceted, _ = render(pattern='asanoha', pixels=256, asanoha_style='faceted')
        rounded, _ = render(pattern='asanoha', pixels=256, asanoha_style='rounded')
        e = engraved.astype(np.int32)
        f = faceted.astype(np.int32)
        r = rounded.astype(np.int32)
        # engraved should have relatively few mid-tones vs relief styles
        e_mid = np.mean((e > 8000) & (e < 56000))
        f_mid = np.mean((f > 8000) & (f < 56000))
        r_mid = np.mean((r > 8000) & (r < 56000))
        self.assertLess(e_mid, f_mid)
        self.assertLess(e_mid, r_mid)
        self.assertFalse(np.array_equal(engraved, faceted))
        self.assertFalse(np.array_equal(faceted, rounded))

    def test_invalid_parameters(self):
        for key, val in [('line_width_mm',0),('line_width_mm',1),
                         ('cube_gap_mm',0),('cube_gap_mm',1),
                         ('cube_step_fraction',0),('cube_step_fraction',.5),
                         ('asanoha_style','nope')]:
            with self.subTest(key=key, val=val), self.assertRaises(ValueError):
                render(pixels=128, **{key:val})

if __name__ == '__main__':
    unittest.main()
