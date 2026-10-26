"""Dimension, style, stagger and CLI/export regression tests for brick relief."""
import tempfile
import subprocess
import sys
import unittest
from pathlib import Path
import numpy as np
from PIL import Image
from dial_patterns import render, FIELD_SPECS, PATTERN_FIELDS

class BrickTests(unittest.TestCase):
    def test_controls(self):
        self.assertIn('brick_style', PATTERN_FIELDS['brick'])
        self.assertIn('brick_layout', PATTERN_FIELDS['brick'])
        self.assertIn('brick_layout', FIELD_SPECS)
        for k in ('brick_width_mm','brick_height_mm','brick_joint_mm','brick_bevel_mm','brick_row_offset'):
            self.assertIn(k, FIELD_SPECS)

    def test_three_styles(self):
        maps = [render(pattern='brick',pixels=512,size_mm=8,brick_style=style)[0]
                for style in ('engraved','faceted','rounded')]
        self.assertTrue(set(np.unique(maps[0])).issubset({0,65535}))
        self.assertGreater(len(np.unique(maps[1])), 10)
        self.assertGreater(len(np.unique(maps[2])), 100)
        self.assertFalse(np.array_equal(maps[0],maps[1]))
        self.assertFalse(np.array_equal(maps[1],maps[2]))

    def test_row_stagger_and_pitch(self):
        # A boundary at x=0 is present in row 0, but shifted in row 1.
        import dial_patterns as app
        x=np.array([[0.0,0.6,1.2]],dtype=np.float32)
        y0=np.array([[0.30]],dtype=np.float32)
        y1=np.array([[0.90]],dtype=np.float32)
        first=app._brick_height(x,y0,1.2,.6,.1,.08,.5,'engraved')
        second=app._brick_height(x,y1,1.2,.6,.1,.08,.5,'engraved')
        self.assertEqual(first[0,0],0)
        self.assertEqual(second[0,0],1)
        self.assertEqual(first[0,1],1)
        self.assertEqual(second[0,1],0)

    def test_joint_and_bevel_change_geometry(self):
        a,_=render(pattern='brick',pixels=384,size_mm=8,brick_joint_mm=.05)
        b,_=render(pattern='brick',pixels=384,size_mm=8,brick_joint_mm=.2)
        c,_=render(pattern='brick',pixels=384,size_mm=8,brick_bevel_mm=.15)
        self.assertGreater(np.mean(b<1000),np.mean(a<1000))
        self.assertFalse(np.array_equal(a,c))

    def test_invalid_dimensions(self):
        options=[{'brick_width_mm':0},{'brick_height_mm':0},{'brick_joint_mm':-.01},
                 {'brick_joint_mm':.6},{'brick_row_offset':1.5},
                 {'brick_bevel_mm':.4},{'brick_style':'unknown'}, {'brick_layout':'unknown'}]
        for kw in options:
            with self.subTest(kw=kw),self.assertRaises(ValueError):
                render(pattern='brick',pixels=128,**kw)

    def test_herringbone_matches_perpendicular_rectangles(self):
        import dial_patterns as app
        rng = np.random.default_rng(42)
        x, y = rng.uniform(-3, 3, (2, 3000))
        for length, thickness in ((1.2, .6), (1.7, .6), (.6, 1.7), (.6, .6)):
            with self.subTest(dimensions=(length, thickness)):
                # Independent geometry oracle: place finite rectangles using
                # lattice translations, then inset all four sides for joints.
                xx, yy = (x, y) if length >= thickness else (y, x)
                long, short = max(length, thickness), min(length, thickness)
                for style in ('engraved', 'faceted', 'rounded'):
                    expected = np.zeros(x.shape)
                    for n in range(-8, 9):
                        for m in range(-8, 9):
                            ox, oy = n * long - m * short, n * long + m * short
                            for lx, ly in ((xx - ox, yy - oy),
                                           (yy - oy, xx - ox - long)):
                                ex = np.minimum(lx, long - lx)
                                ey = np.minimum(ly, short - ly)
                                d = np.minimum(ex, ey) - .05
                                if style == 'engraved':
                                    relief = d >= 0
                                elif style == 'faceted':
                                    relief = np.clip(d / .08, 0, 1)
                                else:
                                    rx = np.clip((ex - .05) / ((long - .1) / 2), 0, 1)
                                    ry = np.clip((ey - .05) / ((short - .1) / 2), 0, 1)
                                    relief = np.sin(np.pi * rx / 2) * np.sin(np.pi * ry / 2)
                                expected = np.maximum(expected, relief)
                    actual = app._brick_height(x, y, length, thickness, .1, .08,
                                               .5, style, 'herringbone')
                    np.testing.assert_allclose(actual, expected, atol=1e-6)

    def test_herringbone_render_controls(self):
        options = dict(pattern='brick', pixels=256, size_mm=6, brick_layout='herringbone')
        a, meta = render(**options)
        self.assertEqual(a.dtype, np.uint16)
        self.assertEqual(meta['brick_layout'], 'herringbone')
        self.assertFalse(np.array_equal(a, render(pattern='brick', pixels=256, size_mm=6)[0]))
        np.testing.assert_array_equal(a, render(**options, brick_row_offset=0)[0])
        for change in ({'rotation':45}, {'phase':.25}, {'brick_joint_mm':.2},
                       {'brick_bevel_mm':.15}, {'brick_width_mm':1.7},
                       {'brick_height_mm':.8}):
            with self.subTest(change=change):
                self.assertFalse(np.array_equal(a, render(**options, **change)[0]))

    def test_herringbone_cli_export(self):
        with tempfile.TemporaryDirectory() as t:
            path = Path(t) / 'herringbone.png'
            subprocess.run([sys.executable, 'dial_patterns.py', '--cli', '--pattern', 'brick',
                            '--brick-layout', 'herringbone', '--rotation', '45',
                            '--pixels', '128', '--output', str(path)],
                           check=True, capture_output=True)
            import json
            meta = json.loads(path.with_suffix('.json').read_text())
            actual, _ = render(**{k: v for k, v in meta.items()
                                 if k in __import__('inspect').signature(render).parameters})
            with Image.open(path) as image:
                np.testing.assert_array_equal(np.asarray(image), actual)
            self.assertEqual(meta['brick_layout'], 'herringbone')
            self.assertTrue(path.with_name('herringbone_8bit.png').exists())

    def test_cli_export_and_metadata(self):
        with tempfile.TemporaryDirectory() as t:
            path=Path(t)/'brick.png'
            subprocess.run([sys.executable, 'dial_patterns.py','--cli','--pattern','brick',
                            '--pixels','256','--brick-style','rounded','--brick-row-offset','.25',
                            '--output',str(path)],check=True,capture_output=True)
            with Image.open(path) as im:
                self.assertEqual(im.size,(256,256))
                self.assertIn(im.mode,('I;16','I;16B','I'))
            self.assertTrue(path.with_name('brick_8bit.png').exists())
            import json
            meta=json.loads(path.with_suffix('.json').read_text())
            self.assertEqual(meta['brick_style'],'rounded')
            self.assertEqual(meta['brick_row_offset'],.25)

if __name__=='__main__':unittest.main()
