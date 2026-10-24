from pathlib import Path
import tempfile
import numpy as np
from PIL import Image
from dial_patterns import PATTERNS, render, save_map

def main():
    thumbs=[]
    for key in PATTERNS:
        arr, meta=render(pattern=key,pixels=384)
        assert arr.dtype==np.uint16 and arr.shape==(384,384)
        assert arr.max()>arr.min(),key
        thumbs.append((key,Image.fromarray((arr/257).astype('uint8')).convert('RGB')))
    # Verify all engraving PNGs retain the exact 16-bit height samples.
    with tempfile.TemporaryDirectory() as directory:
        for key in PATTERNS:
            arr,meta=render(pattern=key,pixels=384)
            path=save_map(arr,meta,Path(directory)/(key+'.png'))
            with Image.open(path) as image:
                assert image.mode in ('I;16','I;16B','I')
                np.testing.assert_array_equal(np.asarray(image),arr)
            with Image.open(path.with_name(key+'_8bit.png')) as image:
                assert image.mode=='L'
    from PIL import ImageDraw
    sheet=Image.new('RGB',(4*256,6*290),'white'); draw=ImageDraw.Draw(sheet)
    for i,(key,im) in enumerate(thumbs):
        x=i%4*256;y=i//4*290
        sheet.paste(im.resize((246,246)),(x+5,y+5))
        draw.text((x+8,y+255),key,fill='black')
    catalog = Path(__file__).resolve().parent.parent/'images'/'pattern_catalog.png'
    catalog.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(catalog)
    print('PASS:',len(thumbs),'patterns and 8/16-bit export')
if __name__=='__main__':main()
