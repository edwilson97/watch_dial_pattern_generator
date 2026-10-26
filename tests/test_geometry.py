"""Regression tests for v0.1 geometric controls and validation."""
import unittest
import numpy as np
from PIL import Image
from dial_patterns import render, render_preview, PATTERN_FIELDS, FIELD_SPECS

class GeometryTests(unittest.TestCase):
    def test_lattice_previews_preserve_export_appearance(self):
        for pattern in ('asanoha', 'isometriccubes'):
            with self.subTest(pattern=pattern):
                exported, _ = render(pattern=pattern, pixels=2048)
                reference = Image.fromarray((exported / 257).astype(np.uint8))
                reference.thumbnail((480, 480), Image.Resampling.LANCZOS)
                reference = np.asarray(reference, dtype=float)
                preview, _ = render_preview(pattern=pattern, pixels=2048)
                coarse, _ = render(pattern=pattern, pixels=480)
                coarse_error = np.mean(np.abs(coarse / 257 - reference))
                preview_error = np.mean(np.abs(np.asarray(preview, dtype=float) - reference))
                self.assertEqual(preview.size, (480, 480))
                self.assertLess(preview_error, coarse_error * .1)

    def test_preview_respects_small_output_resolution(self):
        params = dict(pattern='asanoha', pixels=256)
        original = params.copy()
        preview, meta = render_preview(**params)
        output, _ = render(**params)
        self.assertEqual(params, original)
        self.assertEqual(meta['pixels'], 256)
        np.testing.assert_array_equal(np.asarray(preview), (output / 257).astype(np.uint8))

    def test_controls_are_registered(self):
        expected = {'hobnail':'top_width_mm','wave':'wave_meander_mm',
                    'annularwave':'ridge_height_fraction','graindorge':'grain_aspect',
                    'flamme':'flame_taper','panier':'ribbon_curvature',
                    'rosette':'rosette_harmonics','asanoha':'asanoha_style','fishscales':'fishscales_style'}
        for pattern, field in expected.items():
            self.assertIn(field, PATTERN_FIELDS[pattern])
            self.assertIn(field, FIELD_SPECS)

    def test_hobnail_plateau_width(self):
        base, _ = render(pattern='hobnail', pixels=512, pitch_mm=1, size_mm=8)
        flat, meta = render(pattern='hobnail', pixels=512, pitch_mm=1, size_mm=8, top_width_mm=.5)
        self.assertGreater(np.count_nonzero(flat == 65535), np.count_nonzero(base == 65535))
        self.assertEqual(meta['top_width_mm'], .5)

    def test_wave_independent_controls(self):
        a,_=render(pattern='wave',pixels=256,size_mm=8,pitch_mm=1)
        b,_=render(pattern='wave',pixels=256,size_mm=8,pitch_mm=1,wave_meander_mm=.3)
        c,_=render(pattern='wave',pixels=256,size_mm=8,pitch_mm=1,ridge_height_fraction=.4)
        self.assertFalse(np.array_equal(a,b))
        self.assertLess(int(c.max())-int(c.min()), int(a.max())-int(a.min()))
        ann,_=render(pattern='annularwave',pixels=256,ridge_height_fraction=0)
        self.assertTrue(np.all(ann==65535))

    def test_refined_patterns_change_with_controls(self):
        pairs=[('graindorge','grain_aspect',3),('flamme','flame_taper',1),
               ('panier','ribbon_curvature',1),('rosette','rosette_harmonics',.8)]
        for pattern,key,value in pairs:
            with self.subTest(pattern=pattern):
                a,_=render(pattern=pattern,pixels=256)
                b,meta=render(pattern=pattern,pixels=256,**{key:value})
                self.assertFalse(np.array_equal(a,b))
                self.assertEqual(meta[key],value)



    def test_fishscales_styles_are_distinct(self):
        engraved,_ = render(pattern='fishscales', pixels=256, fishscales_style='engraved')
        faceted,_ = render(pattern='fishscales', pixels=256, fishscales_style='faceted')
        rounded,_ = render(pattern='fishscales', pixels=256, fishscales_style='rounded')
        self.assertFalse(np.array_equal(engraved, faceted))
        self.assertFalse(np.array_equal(faceted, rounded))
        self.assertFalse(np.array_equal(engraved, rounded))

    def test_fishscales_relief_is_not_just_lines(self):
        a,_ = render(pattern='fishscales', pixels=256, size_mm=8, pitch_mm=.8, fishscales_style='rounded')
        vals = a.astype(np.int32)
        mids = vals[(vals > 8000) & (vals < 56000)]
        self.assertGreater(mids.size, vals.size * 0.12)
        self.assertGreater(float(np.std(mids)), 5000.0)

    def test_asanoha_relief_is_not_just_flat_between_lines(self):
        a,_ = render(pattern='asanoha', pixels=256, size_mm=8, pitch_mm=.8, line_width_mm=.055)
        vals = a.astype(np.int32)
        mids = vals[(vals > 8000) & (vals < 56000)]
        self.assertGreater(mids.size, vals.size * 0.15)
        self.assertGreater(float(np.std(mids)), 6000.0)


    def test_asanoha_styles_are_distinct(self):
        engraved,_ = render(pattern='asanoha', pixels=256, asanoha_style='engraved')
        faceted,_ = render(pattern='asanoha', pixels=256, asanoha_style='faceted')
        rounded,_ = render(pattern='asanoha', pixels=256, asanoha_style='rounded')
        self.assertFalse(np.array_equal(engraved, faceted))
        self.assertFalse(np.array_equal(faceted, rounded))
        self.assertFalse(np.array_equal(engraved, rounded))

    def test_invalid_ranges(self):
        cases=[('hobnail',{'top_width_mm':1.0}),('hobnail',{'top_width_mm':-.1}),
               ('wave',{'wave_meander_mm':-.1}),('wave',{'ridge_height_fraction':1.1}),
               ('graindorge',{'grain_aspect':.5}),('flamme',{'flame_taper':-1}),
               ('panier',{'ribbon_curvature':2.1}),('rosette',{'rosette_harmonics':1.1}),
               ('asanoha',{'asanoha_style':'badstyle'}),('fishscales',{'fishscales_style':'badstyle'})]
        for pattern,kwargs in cases:
            with self.subTest(pattern=pattern, kwargs=kwargs), self.assertRaises(ValueError):
                render(pattern=pattern,pixels=128,**kwargs)

if __name__=='__main__': unittest.main()
