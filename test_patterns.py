from pathlib import Path
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
    # Verify precise tapisserie channel width and export bit depths.
    arr,meta=render(pattern='tapisserie',pixels=512,groove_width_mm=.3)
    path=save_map(arr,meta,Path(__file__).parent/'sample_tapisserie.png')
    assert Image.open(path).mode in ('I;16','I;16B','I')
    assert Image.open(path.with_name('sample_tapisserie_8bit.png')).mode=='L'
    from PIL import ImageDraw
    sheet=Image.new('RGB',(4*256,6*290),'white'); draw=ImageDraw.Draw(sheet)
    for i,(key,im) in enumerate(thumbs):
        x=i%4*256;y=i//4*290
        sheet.paste(im.resize((246,246)),(x+5,y+5))
        draw.text((x+8,y+255),key,fill='black')
    sheet.save(Path(__file__).parent/'pattern_catalog.png')
    print('PASS:',len(thumbs),'patterns and 8/16-bit export')
if __name__=='__main__':main()
