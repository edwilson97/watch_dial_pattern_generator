"""Geometry and export checks for the staggered three-face Y blocks."""
import inspect
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import numpy as np
from PIL import Image

from dial_patterns import _interlocking_y_height, render
from inspection import inspection_samples


class InterlockingYTests(unittest.TestCase):
    def test_three_faces_and_recessed_seams_and_notch(self):
        # Samples are inside the top chevron and both sides of the vertical arm.
        x = np.array([0, -.06, .06, 0, 0, 0])
        y = np.array([-.07, .2, .2, .2, 0, -.2])
        h = _interlocking_y_height(x, y, 1, .01, .22)
        np.testing.assert_allclose(h, [1, .56, .78, 0, 0, 0], atol=1e-6)

    def test_staggered_repeat_without_row_seams(self):
        rng = np.random.default_rng(24)
        x, y = rng.uniform(-2, 2, (2, 1000))
        base = _interlocking_y_height(x, y, 1, .01, .22)
        for dx, dy in ((1, 0), (.5, 1/(2*np.sqrt(3))), (0, 1/np.sqrt(3))):
            with self.subTest(dx=dx, dy=dy):
                moved = _interlocking_y_height(x + dx, y + dy, 1, .01, .22)
                np.testing.assert_allclose(base, moved, atol=2e-6)
        # A nearby repeat crosses the candidate-row indexing boundary. Relief
        # on the interior of this arm must not acquire a horizontal reset seam.
        y = 1/(2*np.sqrt(3)) + np.array([-1e-7, 1e-7])
        np.testing.assert_allclose(_interlocking_y_height(-.06, y, 1, .01, .22), .56)

    def test_joint_width_and_relief_step_change_geometry(self):
        options = dict(pattern='interlockingy', pixels=512, size_mm=8, pitch_mm=2)
        narrow, _ = render(**options, y_block_gap_mm=.01)
        wide, _ = render(**options, y_block_gap_mm=.10)
        self.assertGreater(np.count_nonzero(wide == 0), np.count_nonzero(narrow == 0))
        for level in (1, .78, .56):
            self.assertGreater(np.mean(np.abs(narrow.astype(int) - round(level*65535)) <= 1), .1)
        changed, _ = render(**options, y_block_step_fraction=.4)
        self.assertFalse(np.array_equal(narrow, changed))
        cubes, _ = render(pattern='isometriccubes', pixels=512, size_mm=8, pitch_mm=2)
        self.assertGreater(np.mean(np.abs(narrow.astype(float) - cubes)) / 65535, .15)

    def test_shared_transforms_and_physical_scale(self):
        options = dict(pattern='interlockingy', pixels=256, size_mm=8, pitch_mm=2)
        base, _ = render(**options)
        for change in ({'rotation': 23}, {'phase': .2}, {'dome': .8}):
            with self.subTest(change=change):
                self.assertFalse(np.array_equal(base, render(**options, **change)[0]))
        inverted, _ = render(**options, invert=True)
        np.testing.assert_allclose(base.astype(int) + inverted.astype(int), 65535, atol=1)
        scaled, _ = render(pattern='interlockingy', pixels=256, size_mm=16, pitch_mm=4,
                           y_block_gap_mm=.08)
        np.testing.assert_array_equal(base, scaled)

    def test_parameter_validation(self):
        for field, invalid in {
            'y_block_gap_mm': (-.01, .25, float('inf'), float('nan')),
            'y_block_step_fraction': (0, -.01, .5, float('inf'), float('nan')),
        }.items():
            for value in invalid:
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    render(pattern='interlockingy', pixels=128, **{field: value})
        render(pattern='interlockingy', pixels=128, y_block_gap_mm=0)

    def test_auto_mesh_respects_y_block_joint_width(self):
        self.assertEqual(inspection_samples({'pattern': 'interlockingy', 'y_block_gap_mm': .04}, 28.5), 1601)
        self.assertEqual(inspection_samples({'pattern': 'interlockingy', 'y_block_gap_mm': 0}, 28.5), 401)

    def test_cli_height_samples_and_settings_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'y_blocks.png'
            subprocess.run([sys.executable, 'dial_patterns.py', '--cli', '--pattern', 'interlockingy',
                            '--pixels', '256', '--y-block-gap-mm', '.03',
                            '--y-block-step-fraction', '.3', '--rotation', '17', '--dome', '.7',
                            '--circular', '--output', str(path)], check=True, capture_output=True)
            meta = json.loads(path.with_suffix('.json').read_text())
            self.assertEqual(meta['pattern_name'], 'Interlocking Y Blocks')
            self.assertEqual(meta['y_block_gap_mm'], .03)
            self.assertEqual(meta['y_block_step_fraction'], .3)
            options = {key: value for key, value in meta.items() if key in inspect.signature(render).parameters}
            expected, _ = render(**options)
            with Image.open(path) as image:
                self.assertIn(image.mode, ('I;16', 'I;16B', 'I'))
                np.testing.assert_array_equal(np.asarray(image), expected)
            with Image.open(path.with_name('y_blocks_8bit.png')) as image:
                np.testing.assert_array_equal(np.asarray(image), (expected/257).astype(np.uint8))


if __name__ == '__main__':
    unittest.main()
