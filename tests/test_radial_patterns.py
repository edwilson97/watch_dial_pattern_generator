"""Reference geometry, controls, and export coverage for the two radial designs."""
import inspect
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import numpy as np
from PIL import Image

from dial_patterns import _radial_checker_height, _turbine_height, render


class RadialPatternTests(unittest.TestCase):
    def test_checker_alternates_rows_and_columns_and_grows_outward(self):
        # Widths 1, 2, 4 occupy the annulus from radius 1 to 8.
        r = np.array([1.5, 3, 6, .5, 8.5])
        a = np.full(5, np.pi / 8)
        np.testing.assert_array_equal(_radial_checker_height(r, a, 8, 1, 3, 8, 2, 0), [1, 0, 1, 0, 0])
        np.testing.assert_array_equal(_radial_checker_height(r[:3], a[:3] + np.pi / 4, 8, 1, 3, 8, 2, 0), [0, 1, 0])
        for phase in (0, .3, 1):
            np.testing.assert_array_equal(
                _radial_checker_height(r, a, 8, 1, 3, 8, 2, phase),
                _radial_checker_height(r, a + 2 * np.pi, 8, 1, 3, 8, 2, phase))

    def test_checker_bevel_has_linear_physical_edge_ramp(self):
        # First raised check starts at radius 1; sample its circular edge.
        radius = np.array([.99, 1, 1.025, 1.05, 1.1, 1.3])
        theta = np.full(radius.shape, np.pi / 8)
        h = _radial_checker_height(radius, theta, 8, 1, 3, 8, 2, 0, .1)
        np.testing.assert_allclose(h, [0, 0, .25, .5, 1, 1], atol=1e-12)
        # Sector edges use distance in mm as well.
        theta = np.arcsin(np.array([.025, .05, .1]) / 1.5)
        h = _radial_checker_height(np.full(3, 1.5), theta, 8, 1, 3, 8, 2, 0, .1)
        np.testing.assert_allclose(h, [.25, .5, 1], atol=1e-12)

    def test_both_patterns_expose_configurable_grayscale_edges(self):
        from dial_patterns import PATTERN_FIELDS
        for pattern in ('radialchecker', 'turbine'):
            with self.subTest(pattern=pattern):
                self.assertIn('bevel_width_mm', PATTERN_FIELDS[pattern])
                sharp, _ = render(pattern=pattern, pixels=512, bevel_width_mm=0)
                np.testing.assert_array_equal(np.unique(sharp), [0, 65535])
                narrow, _ = render(pattern=pattern, pixels=512, bevel_width_mm=.03)
                wide, _ = render(pattern=pattern, pixels=512, bevel_width_mm=.1)
                count = lambda a: np.count_nonzero((a > 0) & (a < 65535))
                self.assertGreater(count(narrow), 0)
                self.assertGreater(count(wide), count(narrow))

    def test_turbine_band_counts_and_concentric_ribs(self):
        theta = (np.arange(16384) + .5) / 16384 * 2 * np.pi
        for radius, count in ((3, 12), (6, 24), (9, 48)):
            h = _turbine_height(np.full_like(theta, radius), theta, 10.5, 1.5, 3, 12, .65, .3, 0, 0)
            self.assertEqual(np.count_nonzero((h > .5) & (np.roll(h, 1) < .5)), count)
        for radius in (1.6, 4.5, 7.5, 10.4):
            h = _turbine_height(np.full_like(theta, radius), theta, 10.5, 1.5, 3, 12, .65, .3, 0, 0)
            np.testing.assert_array_equal(h, 1)

    def test_turbine_bow_alternates_between_bands(self):
        # At each band's midpoint, a vane bows by +/- .3 angular repeats.
        # Sample both candidate directions: only the alternating one is raised.
        for row, radius in enumerate((3, 6, 9)):
            count = 12 * 2**row
            theta = np.array([.3, -.3]) * 2 * np.pi / count
            h = _turbine_height(np.full(2, radius), theta, 10.5, 1.5,
                                3, 12, .3, .1, 0, 0)
            expected = [1, 0] if row % 2 == 0 else [0, 1]
            with self.subTest(band=row):
                np.testing.assert_array_equal(h, expected)

    def test_turbine_curves_reverse_and_bevels_encode_height(self):
        r = np.linspace(1.5, 10.5, 500)[:, None]
        theta = np.linspace(-np.pi, np.pi, 512)[None, :]
        args = (r, theta, 10.5, 1.5, 3, 12)
        bent = _turbine_height(*args, .65, .45, .08, 0)
        reverse = _turbine_height(r, -theta, 10.5, 1.5, 3, 12, -.65, .45, .08, 0)
        np.testing.assert_allclose(bent, reverse, atol=1e-10)
        self.assertGreater(np.count_nonzero((bent > 0) & (bent < 1)), 100)
        straight = _turbine_height(*args, 0, .45, .08, 0)
        self.assertGreater(np.mean(np.abs(bent - straight)), .1)

    def test_transforms_flat_center_and_exclusion_zones(self):
        for pattern in ('radialchecker', 'turbine'):
            with self.subTest(pattern=pattern):
                base, _ = render(pattern=pattern, pixels=256)
                self.assertEqual(base[128, 128], 0)
                self.assertEqual(base[0, 0], 0)
                for change in ({'rotation': 7}, {'phase': .3}):
                    self.assertFalse(np.array_equal(base, render(pattern=pattern, pixels=256, **change)[0]))
                inverted, _ = render(pattern=pattern, pixels=256, invert=True)
                np.testing.assert_allclose(base.astype(int) + inverted, 65535, atol=1)
                masked, _ = render(pattern=pattern, pixels=256, circular=True, background=.4)
                self.assertEqual(masked[0, 0], round(.4 * 65535))
                zone = dict(shape='circle', x_mm=0, y_mm=0, width_mm=2, level=.5)
                zoned, _ = render(pattern=pattern, pixels=256, exclusion_zones=[zone])
                self.assertEqual(zoned[128, 128], round(.5 * 65535))

    def test_invalid_parameters(self):
        shared = {'radial_inner_radius_mm': (0, -1, 14.25, float('nan'), float('inf')),
                  'rotation': (float('nan'), float('inf')), 'phase': (float('nan'),)}
        per_pattern = {
            'radialchecker': {'checker_rings': (0, 65, 1.5, float('nan')), 'checker_sectors': (3, 7, 514, float('inf')),
                              'checker_growth': (.9, 2.1, float('nan')),
                              'bevel_width_mm': (-.01, float('nan'), float('inf'))},
            'turbine': {'turbine_rings': (0, 7, 1.5, float('nan')), 'segments': (1, 65, 2.5),
                        'turbine_twist': (-2.1, 2.1, float('nan')), 'turbine_line_width_mm': (0, 4, float('nan')),
                        'bevel_width_mm': (-.01, .3, float('nan'))}}
        for pattern, fields in per_pattern.items():
            for field, values in (shared | fields).items():
                for value in values:
                    with self.subTest(pattern=pattern, field=field, value=value), self.assertRaises(ValueError):
                        render(pattern=pattern, pixels=128, **{field: value})

    def test_cli_export_and_settings_round_trip(self):
        for pattern, flags in (
                ('radialchecker', ['--checker-rings', '6', '--checker-sectors', '40', '--checker-growth', '1.3']),
                ('turbine', ['--turbine-rings', '4', '--segments', '10', '--turbine-twist', '-.7', '--turbine-line-width-mm', '.4'])):
            with self.subTest(pattern=pattern), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / 'dial.png'
                subprocess.run([sys.executable, 'dial_patterns.py', '--cli', '--pattern', pattern, '--pixels', '256',
                                '--radial-inner-radius-mm', '2', '--rotation', '17', '--bevel-width-mm', '.06', '--circular', '--output', str(path), *flags],
                               check=True, capture_output=True)
                meta = json.loads(path.with_suffix('.json').read_text())
                options = {k: v for k, v in meta.items() if k in inspect.signature(render).parameters}
                expected, _ = render(**options)
                with Image.open(path) as image:
                    np.testing.assert_array_equal(np.asarray(image), expected)
                with Image.open(path.with_name('dial_8bit.png')) as image:
                    np.testing.assert_array_equal(np.asarray(image), (expected / 257).astype(np.uint8))
                self.assertEqual(meta['radial_inner_radius_mm'], 2)
                self.assertEqual(meta['bevel_width_mm'], .06)


if __name__ == '__main__':
    unittest.main()
