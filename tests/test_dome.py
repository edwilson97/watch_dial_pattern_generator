"""Shared dome layout coverage, physical boundaries, and export compatibility."""
import inspect
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import numpy as np
from PIL import Image

from dial_patterns import DOME_PATTERNS, ENUM_FIELDS, PATTERNS, PATTERN_FIELDS, render


class DomeTests(unittest.TestCase):
    def test_control_visibility_and_unsupported_patterns(self):
        for pattern in PATTERNS:
            with self.subTest(pattern=pattern):
                self.assertEqual('dome' in PATTERN_FIELDS[pattern], pattern in DOME_PATTERNS)
                if pattern not in DOME_PATTERNS:
                    with self.assertRaisesRegex(ValueError, 'unavailable'):
                        render(pattern=pattern, pixels=128, dome=.8)

    def test_each_compatible_pattern_changes_and_preserves_physical_boundaries(self):
        zone = dict(shape='rectangle', x_mm=2, y_mm=0,
                    width_mm=1, height_mm=2, level=.4, clearance_mm=0, feather_mm=0)
        coord = (np.arange(128) + .5) * (8 / 128) - 4
        x, y = coord[None, :], coord[:, None]
        outside = np.hypot(x, y) > 4
        inside_zone = (np.abs(x - 2) < .5) & (np.abs(y) < 1)
        for pattern in sorted(DOME_PATTERNS):
            options = dict(pattern=pattern, pixels=128, size_mm=8)
            with self.subTest(pattern=pattern):
                flat, _ = render(**options)
                np.testing.assert_array_equal(flat, render(**options, dome=0)[0])
                dome, meta = render(**options, dome=.8)
                self.assertFalse(np.array_equal(flat, dome))
                self.assertEqual(meta['dome'], .8)
                inverted, _ = render(**options, dome=.8, invert=True)
                np.testing.assert_allclose(dome.astype(int) + inverted.astype(int), 65535, atol=1)
                bounded, _ = render(**options, dome=1, circular=True, background=.25,
                                    exclusion_zones=[zone])
                np.testing.assert_array_equal(bounded[outside], round(.25 * 65535))
                np.testing.assert_array_equal(bounded[inside_zone], round(.4 * 65535))

    def test_style_variants_remain_available_with_dome(self):
        variants = [('brick', 'brick_layout'), ('brick', 'brick_style'),
                    ('asanoha', 'asanoha_style'), ('fishscales', 'fishscales_style')]
        for pattern, field in variants:
            for value in ENUM_FIELDS[field]:
                with self.subTest(pattern=pattern, field=field, value=value):
                    flat, _ = render(pattern=pattern, pixels=128, **{field: value})
                    dome, _ = render(pattern=pattern, pixels=128, dome=1, **{field: value})
                    self.assertFalse(np.array_equal(flat, dome))
                    self.assertGreater(np.ptp(dome), 0)

    def test_validation_and_legacy_dimple_option(self):
        for strength in (-.1, 1.1, float('inf'), float('nan')):
            with self.subTest(strength=strength), self.assertRaisesRegex(ValueError, 'dome effect'):
                render(pattern='honeycomb', pixels=128, dome=strength)
        current, _ = render(pattern='dimples', pixels=128, dome=.8)
        legacy, _ = render(pattern='dimples', pixels=128, dimple_dome=.8)
        both, _ = render(pattern='dimples', pixels=128, dome=.8, dimple_dome=.8)
        np.testing.assert_array_equal(current, legacy)
        np.testing.assert_array_equal(current, both)
        with self.assertRaisesRegex(ValueError, 'matching values'):
            render(pattern='dimples', pixels=128, dome=.5, dimple_dome=.8)

    def test_cli_and_saved_settings_reproduce_dome(self):
        with tempfile.TemporaryDirectory() as directory:
            for pattern in ('honeycomb', 'diamondlattice', 'dimples'):
                with self.subTest(pattern=pattern):
                    path = Path(directory) / (pattern + '.png')
                    subprocess.run([sys.executable, 'dial_patterns.py', '--cli', '--pattern', pattern,
                                    '--pixels', '128', '--dome', '.8', '--circular', '--output', str(path)],
                                   check=True, capture_output=True)
                    meta = json.loads(path.with_suffix('.json').read_text())
                    self.assertEqual(meta['dome'], .8)
                    settings = {key: value for key, value in meta.items()
                                if key in inspect.signature(render).parameters}
                    expected, _ = render(**settings)
                    with Image.open(path) as image:
                        np.testing.assert_array_equal(np.asarray(image), expected)


if __name__ == '__main__':
    unittest.main()
