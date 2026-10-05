"""The Group B drawings (phase and overview figures drawn from the UBL repository's PNGs): the writer of
history/group-a/redrawn/lib.py, writing the drawing where the figure's source is, diagrams/<figure>/."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'history', 'group-a', 'redrawn'))
from lib import Fig as _Fig, n, q  # noqa: E402,F401
import drawio_format  # noqa: E402


class Fig(_Fig):
    def write(self):
        d = os.path.join(ROOT, 'diagrams', self.name)
        os.makedirs(d, exist_ok=True)
        path = os.path.join(d, self.name + '.drawio')
        open(path, 'w', encoding='utf-8').write(drawio_format.format_text(self.text()))
        return path


import base64, urllib.parse, zlib


def stencil(points, w, h, name='arrow'):
    """A style `shape=stencil(...)` that draws the closed polygon `points` (in the shape's own units, w x h),
    filled: draw.io's own way to keep a custom outline (Edit Style / Edit Shape in the editor shows it)."""
    path = '<move x="%s" y="%s"/>' % (n(points[0][0]), n(points[0][1])) + ''.join(
        '<line x="%s" y="%s"/>' % (n(x), n(y)) for x, y in points[1:]) + '<close/>'
    xml = ('<shape name="%s" h="%s" w="%s" aspect="variable" strokewidth="inherit"><connections/>'
           '<background><path>%s</path></background><foreground><fillstroke/></foreground></shape>' % (name, n(h), n(w), path))
    c = zlib.compressobj(9, zlib.DEFLATED, -15)
    raw = c.compress(urllib.parse.quote(xml, safe="-_.!~*'()").encode()) + c.flush()
    return 'shape=stencil(%s);' % base64.b64encode(raw).decode()
