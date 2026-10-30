"""Rebuild the exclusion-zone comparison from the example settings."""
import json
from pathlib import Path
import sys

from PIL import Image, ImageDraw, ImageFont
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from dial_patterns import render


def main():
    zones = json.loads((ROOT / 'examples/exclusion_zones.json').read_text())
    soft = [dict(zone, feather_mm=.6) for zone in zones]
    canvas = Image.new('RGB', (1544, 628), '#191d24')
    draw = ImageDraw.Draw(canvas)
    font_path = '/System/Library/Fonts/Supplemental/Arial.ttf'
    try:
        title_font = ImageFont.truetype(font_path, 26)
        label_font = ImageFont.truetype(font_path, 20)
        small_font = ImageFont.truetype(font_path, 17)
    except OSError:
        title_font = ImageFont.load_default(size=26)
        label_font = ImageFont.load_default(size=20)
        small_font = ImageFont.load_default(size=17)
    draw.text((24, 16), 'Exclusion zones / Ribs & Posts', font=title_font, fill='white')
    for index, (label, settings) in enumerate((('Original pattern', []),
                                              ('Sharp boundaries', zones),
                                              ('Feathered edges / 0.6 mm', soft))):
        x = 24 + index * 508
        array, _ = render(pattern='ingenieur', pixels=1440, pitch_mm=1.6,
                          ingenieur_feature_width_mm=.14, circular=True,
                          exclusion_zones=settings)
        image = Image.fromarray((array / 257).astype(np.uint8)).resize((480, 480), Image.Resampling.LANCZOS)
        canvas.paste(image, (x, 100))
        draw.text((x, 66), label, font=label_font, fill='#e2e6ec')
    draw.text((24, 599), 'Reserved areas: logo at 12 / date at 3 / center hole footprint. White = highest surface.',
              font=small_font, fill='#b6bfcc')
    target = ROOT / 'images/exclusion_zones_preview.png'
    canvas.save(target)
    print(target)


if __name__ == '__main__':
    main()
