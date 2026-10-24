"""Manufacturing geometry regressions and inspection-source fidelity."""
import tempfile
import unittest
from pathlib import Path
import numpy as np
from PIL import Image
from dial_patterns import render, save_map, _hex_cell_coordinates, _perlage_height
from inspection import crop_map, relief_mesh


class ReliefInspectionTests(unittest.TestCase):
    def test_horizontal_row_seams_converge(self):
        # v=0 used to reset these patterns abruptly. Compare adjacent pixel centers
        # as spacing shrinks; a genuine cliff would retain a nonzero jump.
        for pattern in ('basketweave', 'panier', 'fishscales', 'fanscallop', 'perlage'):
            differences=[]
            for pixels in (256, 1024):
                a,_=render(pattern=pattern, size_mm=2, pitch_mm=1,pixels=pixels)
                a=a.astype(float)/65535
                differences.append(np.max(np.abs(a[pixels//2]-a[pixels//2-1])))
            with self.subTest(pattern=pattern):
                self.assertLess(differences[1], .025)
                self.assertLess(differences[1], differences[0]*.4+2/65535)

    def test_woven_boundaries_match_in_both_directions(self):
        from dial_patterns import _woven_height
        t=np.linspace(-2,2,401)
        for boundary in (-1,0,1):
            for base in (.15,.22):
                a=_woven_height(t,np.full_like(t,boundary-1e-7),base)
                b=_woven_height(t,np.full_like(t,boundary+1e-7),base)
                c=_woven_height(np.full_like(t,boundary-1e-7),t,base)
                d=_woven_height(np.full_like(t,boundary+1e-7),t,base)
                self.assertLess(np.max(np.abs(a-b)),1e-5)
                self.assertLess(np.max(np.abs(c-d)),1e-5)

    def test_fish_scale_arc_boundaries_are_recessed(self):
        from dial_patterns import _fishscales_height
        x=np.linspace(-.49,.49,300)
        boundary=1-np.sqrt(.95**2-x*x)
        u=x+.5
        for style in ('engraved','faceted','rounded'):
            below=_fishscales_height(u,boundary-1e-7,style)
            above=_fishscales_height(u,boundary+1e-7,style)
            self.assertLess(np.max(np.abs(above-below)),1e-4)
            self.assertLess(np.max(above),1e-4)

    def test_honeycomb_edges_have_uniform_deep_joints(self):
        a,_=render(pattern='honeycomb',size_mm=2,pitch_mm=1,pixels=1024)
        xy=(np.arange(1024)+.5)/512-1
        x,y=np.meshgrid(xy,xy)
        xx,yy=_hex_cell_coordinates(x,y)
        edge=.5-np.maximum.reduce([np.abs(xx),np.abs(.5*xx+np.sqrt(3)/2*yy),np.abs(-.5*xx+np.sqrt(3)/2*yy)])
        self.assertTrue(np.all(a[edge<.024]==0))
        self.assertTrue(np.all(a[edge>.126]==65535))

    def test_perlage_ring_spacing_and_overlap_affect_relief(self):
        u,v=np.meshgrid(np.linspace(-1,1,201),np.linspace(-1,1,201))
        h=_perlage_height(u,v,1,.06,.25)
        self.assertGreaterEqual(h.min(),.78-1e-6)
        self.assertLessEqual(h.max(),1)
        self.assertFalse(np.allclose(h,_perlage_height(u,v,1,.1,.25)))
        self.assertFalse(np.allclose(h,_perlage_height(u,v,1,.06,.4)))
        eps=1e-7
        for boundary in (0,1):
            self.assertLess(np.max(np.abs(_perlage_height(u,np.full_like(u,boundary-eps),1,.06,.25)-_perlage_height(u,np.full_like(u,boundary+eps),1,.06,.25))),1e-4)

    def test_crop_retains_original_samples_and_clamps_edges(self):
        a=np.arange(256*256,dtype=np.uint16).reshape(256,256)
        crop,span=crop_map(a,{'size_mm':8},2,100,-100)
        np.testing.assert_array_equal(crop,a[:64,-64:])
        self.assertEqual(span,2)

    def test_inspection_is_separate_from_depth_export(self):
        a,m=render(pattern='brick',size_mm=4,pixels=256)
        original=a.copy()
        mesh=relief_mesh(a,4,.15)
        self.assertAlmostEqual(mesh.points[:,2].min(),-.15)
        np.testing.assert_allclose(mesh['Depth (mm)'], -mesh.points[:,2])
        np.testing.assert_array_equal(a,original)
        with tempfile.TemporaryDirectory() as directory:
            p=save_map(a,m,Path(directory)/'depth.png')
            np.testing.assert_array_equal(np.asarray(Image.open(p)),original)

if __name__=='__main__':
    unittest.main()
