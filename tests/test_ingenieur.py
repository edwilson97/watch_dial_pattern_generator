"""Relief, checkerboard topology, and export coverage for the grid pattern."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import numpy as np
from PIL import Image

from dial_patterns import _ingenieur_height, render


class IngenieurTests(unittest.TestCase):
    def height(self, x, y):
        return _ingenieur_height(np.asarray(x), np.asarray(y), 1, 3, .1, .15)

    def test_alternating_ribs_and_round_posts(self):
        # Centers lie at .2, .5 and .8 within each square.
        xs = np.array([.2, .35, .5, .65, .8])
        np.testing.assert_allclose(self.height(xs, .2), 1)
        np.testing.assert_allclose(self.height(xs + 1, .2), [1, 0, 1, 0, 1])
        np.testing.assert_allclose(self.height(xs, 1.2), [1, 0, 1, 0, 1])
        np.testing.assert_allclose(self.height(xs + 1, 1.2), 1)
        # Post cross-section is radial, flat on top, and recessed outside its rim.
        r = np.array([0, .02, .06, .08])
        axis = self.height(1.2 + r, .2)
        diagonal = self.height(1.2 + r / np.sqrt(2), .2 + r / np.sqrt(2))
        np.testing.assert_allclose(axis, diagonal, atol=1e-6)
        np.testing.assert_allclose(axis[:2], 1)
        self.assertGreater(axis[2], 0)
        self.assertLess(axis[2], 1)
        self.assertEqual(axis[3], 0)

    def test_repeats_and_recessed_square_boundaries(self):
        x = np.linspace(-2, 2, 103)
        y = x * .71
        base = self.height(x, y)
        for dx, dy in ((2, 0), (0, 2), (1, 1), (-1, -1)):
            np.testing.assert_allclose(self.height(x + dx, y + dy), base, atol=1e-6)
        for boundary in (-1, 0, 1, 2):
            np.testing.assert_array_equal(self.height(x, boundary), 0)
            np.testing.assert_array_equal(self.height(boundary, x), 0)

    def test_parameters_and_render_transforms(self):
        options = dict(pattern='ingenieur', pixels=256, size_mm=4, pitch_mm=1)
        base, _ = render(**options)
        for change in ({'ingenieur_count': 4}, {'ingenieur_gap_mm': .15},
                       {'ingenieur_feature_width_mm': .2}, {'rotation': 23}, {'phase': .2}):
            self.assertFalse(np.array_equal(base, render(**options, **change)[0]), change)
        inverted, _ = render(**options, invert=True)
        np.testing.assert_allclose(base.astype(int) + inverted.astype(int), 65535, atol=1)
        masked, _ = render(**options, circular=True, background=1)
        self.assertEqual(masked[0, 0], 65535)

    def test_invalid_settings(self):
        for key, values in {
            'ingenieur_count': (0, 13, 2.5, float('nan'), float('inf')),
            'ingenieur_gap_mm': (-.1, .75, float('nan'), float('inf')),
            'ingenieur_feature_width_mm': (0, -.1, .23, float('nan'), float('inf')),
            'pitch_mm': (float('nan'), float('inf')),
        }.items():
            for value in values:
                with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                    options = dict(pattern='ingenieur', pixels=128, pitch_mm=.75)
                    options[key] = value
                    render(**options)

    def test_cli_exports_and_metadata_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'grid.png'
            subprocess.run([sys.executable, 'dial_patterns.py', '--cli', '--pattern', 'ingenieur',
                            '--pixels', '256', '--ingenieur-count', '4', '--ingenieur-gap-mm', '.08',
                            '--ingenieur-feature-width-mm', '.12', '--output', str(path)],
                           check=True, capture_output=True)
            meta = json.loads(path.with_suffix('.json').read_text())
            self.assertEqual(meta['ingenieur_count'], 4)
            self.assertEqual(meta['ingenieur_gap_mm'], .08)
            self.assertEqual(meta['ingenieur_feature_width_mm'], .12)
            import inspect
            options = {key: value for key, value in meta.items() if key in inspect.signature(render).parameters}
            with Image.open(path) as image:
                np.testing.assert_array_equal(np.asarray(image), render(**options)[0])
            with Image.open(path.with_name('grid_8bit.png')) as image:
                self.assertEqual(image.mode, 'L')


if __name__ == '__main__':
    unittest.main()
