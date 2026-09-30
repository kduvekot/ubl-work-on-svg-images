"""The deck's clip art in plain greys (each colour its luminance), for the first
fit (fit.py): <WORK>/parts-lum/<part>.svg. The parts kept, in
illustrations/parts/, have the UBL PNGs' own greys instead (tones.py).

    python3 parts_grey.py
"""
import os, re
from paths import WORK, work

CLIPART = {'supplier': 'pic04', 'buyer': 'pic05', 'parcel-box': 'pic06', 'parcel-wrapped': 'pic07',
           'forwarder': 'pic08', 'supplier-b': 'pic09', 'buyer-b': 'pic10'}   # part -> the deck's picture


def lum(c):
    r, g, b = (int(c[i:i + 2], 16) for i in (1, 3, 5))
    return round(0.299 * r + 0.587 * g + 0.114 * b)


if __name__ == '__main__':
    for part, pic in CLIPART.items():
        svg = open(os.path.join(WORK, 'svg', pic + '.svg')).read()
        svg = re.sub(r'#[0-9a-fA-F]{6}\b', lambda m: '#%02x%02x%02x' % ((lum(m.group(0)),) * 3), svg)
        open(work('parts-lum', part + '.svg'), 'w').write(svg)
        print(part)
