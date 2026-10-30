"""Reserved footprints, transition boundaries, transforms, and CLI exports."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import numpy as np
from PIL import Image

from dial_patterns import PATTERNS, render
from exclusion_zones import apply_zones, validate_zones


class ExclusionZoneTests(unittest.TestCase):
    def test_rectangle_clearance_and_outward_feather(self):
        zone = validate_zones([dict(width_mm=4, height_mm=2, x_mm=0, y_mm=0,
                                    clearance_mm=1, feather_mm=2)])[0]
        # Right edge at 2, clearance ends at 3; feather ends at 5.
        x = np.array([0, 2, 3, 4, 5, 6.])
        np.testing.assert_allclose(apply_zones(np.zeros(6), x, 0, [zone]),
                                   [1, 1, 1, .5, 0, 0])
        zone['feather_mm'] = 0
        # Clearance rounds rectangle corners by Euclidean distance.
        np.testing.assert_allclose(apply_zones(np.zeros(2), np.array([2.7, 2.8]),
                                               np.array([1.7, 1.8]), [zone]), [1, 0])

    def test_circle_position_orientation_and_outside_unchanged(self):
        settings = dict(pixels=256, size_mm=16, pattern='hobnail')
        zone = dict(shape='circle', x_mm=3, y_mm=4, width_mm=2, clearance_mm=.25, level=.7)
        base, _ = render(**settings)
        result, meta = render(**settings, exclusion_zones=[zone])
        coords = (np.arange(256) + .5) * 16 / 256 - 8
        mask = np.hypot(coords[None, :] - 3, coords[:, None] + 4) <= 1.25
        np.testing.assert_array_equal(result[mask], round(.7 * 65535))
        np.testing.assert_array_equal(result[~mask], base[~mask])
        self.assertGreater(np.count_nonzero(mask[:128]), 0)
        self.assertEqual(np.count_nonzero(mask[128:]), 0)
        self.assertEqual(meta['exclusion_zones'][0]['x_mm'], 3)

    def test_every_pattern_inversion_rotation_and_circular_boundary(self):
        zone = dict(shape='rectangle', x_mm=0, y_mm=0, width_mm=2, height_mm=2,
                    clearance_mm=0, level=1)
        for pattern in PATTERNS:
            with self.subTest(pattern=pattern):
                plain, _ = render(pattern=pattern, pixels=128)
                empty, _ = render(pattern=pattern, pixels=128, exclusion_zones=[])
                np.testing.assert_array_equal(plain, empty)
                result, _ = render(pattern=pattern, pixels=128, rotation=31,
                                   phase=.3, invert=True, exclusion_zones=[zone])
                np.testing.assert_array_equal(result[61:67, 61:67], 65535)
        result, _ = render(pixels=128, circular=True, background=.2,
                           exclusion_zones=[dict(zone, width_mm=80, height_mm=80)])
        self.assertEqual(result[64, 64], 65535)
        self.assertEqual(result[0, 0], round(.2 * 65535))

    def test_overlap_order_and_metadata_copy(self):
        zones = [dict(x_mm=0, y_mm=0, width_mm=4, height_mm=4),
                 dict(shape='circle', x_mm=0, y_mm=0, width_mm=1, level=.25)]
        arr, meta = render(pixels=128, exclusion_zones=zones)
        self.assertEqual(arr[64, 64], round(.25 * 65535))
        zones[0]['width_mm'] = 80
        self.assertEqual(meta['exclusion_zones'][0]['width_mm'], 4)

    def test_invalid_zones(self):
        for zones in ({}, 'circle', [None], [dict(shape='ellipse')], [dict(typo=1)],
                      [dict(width_mm=0)], [dict(height_mm=-1)], [dict(clearance_mm=-1)],
                      [dict(feather_mm=-1)], [dict(level=1.1)], [dict(x_mm=float('nan'))],
                      [dict(y_mm=float('inf'))], [dict(width_mm='oops')]):
            with self.subTest(zones=zones), self.assertRaises(ValueError):
                render(pixels=128, exclusion_zones=zones)

    def test_cli_exports_zone_metadata_and_grayscale(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            zones_file = path / 'zones.json'
            zones_file.write_text(json.dumps([dict(shape='circle', x_mm=0, y_mm=0,
                                                    width_mm=3, level=.6)]))
            output = path / 'dial.png'
            command = [sys.executable, 'dial_patterns.py', '--cli', '--pixels', '128',
                       '--exclusion-zones-file', str(zones_file), '--output', str(output)]
            subprocess.run(command, check=True, capture_output=True)
            meta = json.loads(output.with_suffix('.json').read_text())
            self.assertEqual(meta['exclusion_zones'][0]['level'], .6)
            with Image.open(output) as image:
                self.assertEqual(np.asarray(image)[64, 64], round(.6 * 65535))
            with Image.open(path / 'dial_8bit.png') as image:
                self.assertEqual(image.getpixel((64, 64)), 153)
            zones_file.write_text('not json')
            failed = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(failed.returncode, 0)
            self.assertIn('Cannot load exclusion zones', failed.stderr)


if __name__ == '__main__':
    unittest.main()
