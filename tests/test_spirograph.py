"""Closed Spirograph geometry, physical groove dimensions, and export coverage."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import numpy as np
from PIL import Image

from dial_patterns import _spirograph_points, render, render_preview


class SpirographTests(unittest.TestCase):
    def test_curve_closes_with_expected_outer_tips(self):
        points = _spirograph_points(30, 11, 1.55, 26, .0001)
        np.testing.assert_array_equal(points[0], points[-1])
        self.assertAlmostEqual(np.linalg.norm(points[0]), 13)
        self.assertLessEqual(float(np.linalg.norm(points, axis=1).max()), 13 + 1e-10)
        # Each of the thirty outer tips occurs along the single closed path.
        t = np.arange(30) * 2 * np.pi * 11 / 30
        for tip in 13 * np.column_stack((np.cos(t), np.sin(t))):
            self.assertLess(np.min(np.linalg.norm(points - tip, axis=1)), .06)

    def test_zero_pen_offset_is_a_circle_with_physical_groove_width(self):
        size, pixels, diameter, width = 8, 512, 6, .5
        actual, _ = render(pattern='spirograph', size_mm=size, pixels=pixels,
                           spirograph_pen_offset=0, spirograph_diameter_mm=diameter,
                           groove_width_mm=width, spirograph_style='rounded')
        coord = (np.arange(pixels) + .5) * size / pixels - size / 2
        distance = np.abs(np.hypot(coord[None, :], coord[:, None]) - diameter / 2)
        expected = 1 - np.sqrt(np.maximum(0, 1 - np.minimum(distance / (width / 2), 1)**2))
        self.assertLess(np.mean(np.abs(actual / 65535 - expected)), .001)
        np.testing.assert_array_equal(actual[distance > width / 2 + .01], 65535)
        self.assertEqual(actual[pixels // 2, pixels // 2], 65535)

    def test_v_cut_has_linear_slopes_and_grayscale_at_export_resolution(self):
        size, pixels, diameter, width = 8, 512, 6, .8
        options = dict(pattern='spirograph', size_mm=size, pixels=pixels,
                       spirograph_pen_offset=0, spirograph_diameter_mm=diameter,
                       groove_width_mm=width)
        image, meta = render(**options)
        coord = (np.arange(pixels) + .5) * size / pixels - size / 2
        distance = np.abs(np.hypot(coord[None, :], coord[:, None]) - diameter / 2)
        expected = np.clip(distance / (width / 2), 0, 1)
        # Verify physical height samples, rather than simulated lighting.
        np.testing.assert_allclose(image / 65535, expected, atol=.006)
        self.assertEqual(meta['spirograph_style'], 'v_cut')
        self.assertGreater(len(np.unique(image)), 1000)
        self.assertGreater(np.count_nonzero((image > 6553) & (image < 58982)), pixels**2 * .15)
        rounded, _ = render(**options, spirograph_style='rounded')
        self.assertFalse(np.array_equal(image, rounded))
        self.assertTrue(np.all(image.astype(int) >= rounded.astype(int) - 1))

    def test_controls_transform_shape_and_shared_processing_works(self):
        options = dict(pattern='spirograph', pixels=256)
        base, _ = render(**options)
        for change in ({'spirograph_fixed_teeth': 29}, {'spirograph_rolling_teeth': 13},
                       {'spirograph_pen_offset': .8}, {'spirograph_diameter_mm': 22},
                       {'rotation': 9}):
            with self.subTest(change=change):
                changed, meta = render(**options, **change)
                self.assertFalse(np.array_equal(base, changed))
                for key, value in change.items():
                    self.assertEqual(meta[key], value)
        wide, _ = render(**options, groove_width_mm=.4)
        self.assertGreater(np.count_nonzero(wide < 65535), np.count_nonzero(base < 65535))
        inverted, _ = render(**options, invert=True)
        np.testing.assert_allclose(base.astype(int) + inverted.astype(int), 65535, atol=1)
        masked, _ = render(**options, circular=True, background=.25)
        self.assertEqual(masked[0, 0], round(.25 * 65535))
        zoned, _ = render(**options, exclusion_zones=[dict(shape='circle', x_mm=0, y_mm=0,
                                                          width_mm=4, level=.5)])
        self.assertEqual(zoned[128, 128], round(.5 * 65535))
        preview, _ = render_preview(**options)
        np.testing.assert_array_equal(np.asarray(preview), (base / 257).astype('uint8'))
        # Gears with the same reduced ratio give identical curves, without retracing.
        reduced, _ = render(**options, spirograph_fixed_teeth=60, spirograph_rolling_teeth=22)
        np.testing.assert_array_equal(base, reduced)

    def test_cusps_and_small_rolling_gears_are_finite(self):
        for fixed, rolling, offset in ((30, 15, 1), (96, 1, 2), (96, 95, 1), (3, 1, 0)):
            with self.subTest(fixed=fixed, rolling=rolling, offset=offset):
                with np.errstate(all='raise'):
                    image, _ = render(pattern='spirograph', pixels=256,
                                      spirograph_fixed_teeth=fixed, spirograph_rolling_teeth=rolling,
                                      spirograph_pen_offset=offset)
                self.assertGreater(np.ptp(image), 0)

    def test_retraced_turning_point_at_export_resolution(self):
        # This sampling resolution puts a zero-length segment at a cusp.
        with np.errstate(all='raise'):
            image, _ = render(pattern='spirograph', pixels=2048,
                              spirograph_fixed_teeth=30, spirograph_rolling_teeth=15,
                              spirograph_pen_offset=1)
        self.assertGreater(np.ptp(image), 60000)
        self.assertTrue(np.all(image[1024, 100:-100] < 5000))

    def test_invalid_parameters(self):
        cases = {
            'spirograph_fixed_teeth': (0, 2, 97, 30.5, float('nan'), float('inf')),
            'spirograph_rolling_teeth': (0, -1, 30, 31, 11.5, float('nan'), float('inf')),
            'spirograph_pen_offset': (-.1, 2.1, float('nan'), float('inf')),
            'spirograph_diameter_mm': (0, -1, float('nan'), float('inf')),
            'groove_width_mm': (0, -.1, 26, float('nan'), float('inf')),
            'rotation': (float('nan'), float('inf')),
            'spirograph_style': ('flat', ''),
        }
        for key, values in cases.items():
            for value in values:
                with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                    render(pattern='spirograph', pixels=128, **{key: value})

    def test_cli_and_metadata_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'spirograph.png'
            options = dict(pattern='spirograph', pixels=256, spirograph_fixed_teeth=35,
                           spirograph_rolling_teeth=12, spirograph_pen_offset=1.4,
                           spirograph_diameter_mm=24, groove_width_mm=.3, rotation=17, spirograph_style='rounded')
            args = [sys.executable, 'dial_patterns.py', '--cli', '--output', str(path)]
            for key, value in options.items():
                args += ['--' + key.replace('_', '-'), str(value)]
            subprocess.run(args, check=True, capture_output=True)
            expected, _ = render(**options)
            with Image.open(path) as image:
                np.testing.assert_array_equal(np.asarray(image), expected)
            with Image.open(path.with_name('spirograph_8bit.png')) as image:
                self.assertEqual(image.mode, 'L')
            meta = json.loads(path.with_suffix('.json').read_text())
            self.assertEqual(meta['pattern_name'], 'Spirograph')
            np.testing.assert_array_equal(render(**{key: meta[key] for key in options})[0], expected)


if __name__ == '__main__':
    unittest.main()
