"""Geometry and export regressions for the recessed golf-ball texture."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import numpy as np
from PIL import Image

from dial_patterns import _dimple_height, render


class DimpleTests(unittest.TestCase):
    def test_bowls_are_radial_and_recessed_with_flat_land(self):
        radii = np.array([0, .1, .2, .3, .4, .5], dtype=np.float32)
        heights = _dimple_height(radii, np.zeros_like(radii), 1, .8)
        self.assertAlmostEqual(float(heights[0]), 0, places=6)
        self.assertTrue(np.all(np.diff(heights[:5]) > 0))
        np.testing.assert_allclose(heights[4:], 1, atol=1e-6)
        np.testing.assert_allclose(
            _dimple_height(radii / np.sqrt(2), radii / np.sqrt(2), 1, .8),
            heights, atol=1e-6)

    def test_staggered_centers_and_lattice_repeat(self):
        row = np.sqrt(3) / 2
        x = np.array([0, 1, .5, -.5, .5, -.5])
        y = np.array([0, 0, row, row, -row, -row])
        np.testing.assert_allclose(_dimple_height(x, y, 1, .8), 0, atol=1e-6)
        x = np.linspace(-2, 2, 51)
        y = np.linspace(-1, 1, 51)
        base = _dimple_height(x, y, 1, .8)
        np.testing.assert_allclose(_dimple_height(x + .5, y + row, 1, .8),
                                   base, atol=2e-6)

    def test_diameter_controls_coverage_and_parameters_transform_map(self):
        options = dict(pattern='dimples', pixels=256, size_mm=4, pitch_mm=1)
        small, _ = render(**options, dimple_diameter_mm=.4)
        large, _ = render(**options, dimple_diameter_mm=.8)
        self.assertGreater(np.count_nonzero(large < 65535), np.count_nonzero(small < 65535))
        for extra in ({'rotation': 17}, {'phase': .2}):
            changed, _ = render(**options, dimple_diameter_mm=.4, **extra)
            self.assertFalse(np.array_equal(small, changed))
        inverted, _ = render(**options, dimple_diameter_mm=.4, invert=True)
        np.testing.assert_allclose(small.astype(int) + inverted.astype(int), 65535, atol=1)
        masked, _ = render(**options, circular=True, background=1)
        self.assertEqual(masked[0, 0], 65535)

    def test_invalid_diameters(self):
        for diameter in (0, -.1, .76, float('nan'), float('inf')):
            with self.subTest(diameter=diameter), self.assertRaises(ValueError):
                render(pattern='dimples', pixels=128, dimple_diameter_mm=diameter)
        render(pattern='dimples', pixels=128, dimple_diameter_mm=.75)

    def test_touching_dimples_at_small_pitch(self):
        for pitch in (.65, .11, .08, .05):
            with self.subTest(pitch=pitch):
                array, _ = render(pattern='dimples', pixels=256, size_mm=pitch * 4,
                                  pitch_mm=pitch, dimple_diameter_mm=pitch)
                self.assertGreater(np.ptp(array), 60000)
        # Every bowl touches all six nearest neighbors at its rim. Samples
        # just before and after each tangent point lie inside the two bowls.
        angles = np.arange(6) * np.pi / 3
        for radius in (.49, .5, .51):
            height = _dimple_height(radius * np.cos(angles), radius * np.sin(angles), .05, .05)
            if radius == .5:
                np.testing.assert_allclose(height, 1, atol=1e-6)
            else:
                self.assertTrue(np.all(height < .99))

    def test_cli_exports_exact_height_samples_and_settings(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'dimples.png'
            subprocess.run([sys.executable, 'dial_patterns.py', '--cli', '--pattern', 'dimples',
                            '--pixels', '256', '--pitch-mm', '1.2', '--dimple-diameter-mm', '1',
                            '--depth-mm', '.08', '--output', str(path)],
                           check=True, capture_output=True)
            expected, _ = render(pattern='dimples', pixels=256, pitch_mm=1.2,
                                 dimple_diameter_mm=1, depth_mm=.08)
            with Image.open(path) as image:
                np.testing.assert_array_equal(np.asarray(image), expected)
            with Image.open(path.with_name('dimples_8bit.png')) as image:
                self.assertEqual(image.mode, 'L')
            meta = json.loads(path.with_suffix('.json').read_text())
            self.assertEqual(meta['dimple_diameter_mm'], 1)
            self.assertEqual(meta['depth_mm'], .08)
            np.testing.assert_array_equal(render(**{
                key: meta[key] for key in ('pattern', 'pixels', 'pitch_mm',
                                          'dimple_diameter_mm', 'depth_mm')})[0], expected)


if __name__ == '__main__':
    unittest.main()
