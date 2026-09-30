# Builds the draw.io drawing of one Fulfilment figure from its slide in the deck
# (ShipmentConsignment-2.ppt, see README): its shapes as the slide has them,
# its pictures the parts (illustrations/parts/, or the plain greys of
# <WORK>/parts-lum/ before tones.py has run), in px at 96 per inch (a slide
# unit, 1/576 in, is 1/6 px). fit.py calls it: with the geometry found in the
# UBL PNG, and (for the drawing kept) its frame, origin and page.
#
#   python3 build.py <slide 2..5> <out.drawio>       the slide as it is
import sys, os, base64, html, json, io
from pptshapes import slides, text_style
from paths import WORK, PARTS

PIC = {5: 'supplier', 6: 'buyer', 7: 'parcel-box', 8: 'parcel-wrapped', 9: 'forwarder',
       10: 'supplier-b', 11: 'buyer-b', 3: 'document', 4: 'pallet'}     # the deck's picture number -> part
SCHEME = ['#ffffff', '#000000', '#ffb800', '#ff0000', '#ffef66', '#000000', '#00b200', '#703dff']
U = 1 / 6                                    # px per slide unit
PT = 96 / 72                                 # px per point
ARROW = 0.75                                 # the arrowhead's size, in line widths (as fitted to the PNGs)
from PIL import ImageFont
_FONT = '/usr/share/fonts/truetype/liberation/LiberationSans-%s.ttf'   # Arial's metrics
def text_width(line, px, bold=False):
    return ImageFont.truetype(_FONT % ('Bold' if bold else 'Regular'), 200).getlength(line) * px / 200

def grey(c):
    r, g, b = int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16)
    y = round(0.299 * r + 0.587 * g + 0.114 * b)
    return '#%02x%02x%02x' % (y, y, y)

def colour(v):
    if v is None: return None
    if v & 0x08000000: return SCHEME[v & 0xff]
    return '#%02x%02x%02x' % (v & 255, (v >> 8) & 255, (v >> 16) & 255)

def shapes_of(n):
    out = []
    def flat(g):
        for s in g[1:]:
            if isinstance(s, list): flat(s)
            else: out.append(s)
    flat(slides()[n - 1])
    return [s for s in out if not (s['text'] or '').startswith('(c)') and s['text'] != '*']

def part_svg(part):
    """a part's SVG: illustrations/parts/, else (the clip art, before tones.py) its plain greys"""
    for d in (PARTS, os.path.join(WORK, 'parts-lum')):
        f = os.path.join(d, part + '.svg')
        if os.path.exists(f): return open(f, 'rb').read()
    raise FileNotFoundError(part + '.svg')

def photo_png():
    """the pallet photo, grey, as a PNG: what the UBL PNGs show where a pallet is"""
    from PIL import Image
    b = io.BytesIO(); Image.open(os.path.join(WORK, 'pictures', 'pic03.png')).convert('L').save(b, 'PNG')
    return b.getvalue()

def build(n, title_pt=32, frame=None, hide=(), only=None, geom=None, sizes=None, photo=False, text_left=None, extra=(),
          origin=(0, 0), name='Page-1', page=None, scale=None):
    """origin: added to every coordinate; frame: [x0, y0, x1, y1, stroke width];
    scale: the PNG's px per the drawing's px (on the frame, ubl-png-scale)"""
    ox, oy = origin
    text_left = text_left or {}
    geom = geom or {}; sizes = sizes or {}
    cells = []
    uid = [1]
    def nid():
        uid[0] += 1; return 'c%d' % uid[0]
    for k, s in enumerate(shapes_of(n) + list(extra)):
        if k in hide: continue
        if only is not None and k not in only: continue
        top, left, right, bottom = s['anchor']
        x, y, w, h = left * U, top * U, (right - left) * U, (bottom - top) * U
        if k in geom and s.get('type') != 20: x, y, w, h = geom[k]
        x, y = x + ox, y + oy
        pr = s['props']; t = s.get('type')
        if t == 75:        # a picture
            part = PIC[pr[0x104]]
            if photo and part == 'pallet':   # to find it: the photo the PNGs were made from
                img = 'data:image/png,' + base64.b64encode(photo_png()).decode()
            else:
                img = 'data:image/svg+xml,' + base64.b64encode(part_svg(part)).decode()
            bg = ''
            if part == 'pallet':   # the photo is opaque: white where it has no pallet
                cells.append(('<mxCell id="%s" value="" style="rounded=0;fillColor=#ffffff;strokeColor=none;" vertex="1" parent="1">'
                              '<mxGeometry x="%.2f" y="%.2f" width="%.2f" height="%.2f" as="geometry"/></mxCell>') % (nid(), x, y, w, h))
            # the part it is (Edit Data: ubl-part), for tools/embed_parts.py
            cells.append(('<object id="%s" label="" ubl-part="%s"><mxCell style="shape=image;imageAspect=0;verticalLabelPosition=bottom;%simage=%s;" vertex="1" parent="1">'
                          '<mxGeometry x="%.2f" y="%.2f" width="%.2f" height="%.2f" as="geometry"/></mxCell></object>')
                         % (nid(), part, bg, img, x, y, w, h))
        elif t == 20:      # a line: its arrowhead at its start (0x1d0)
            fl = s['flags']
            sx, ex = (right, left) if fl & 0x40 else (left, right)
            sy, ey = (bottom, top) if fl & 0x80 else (top, bottom)
            if k in geom and geom[k][0] == 'ends':     # the ends as found in the PNG
                (sx, sy), (ex, ey) = [(p[0] / U, p[1] / U) for p in geom[k][1:]]
            elif k in geom:
                mx, my = geom[k]; sx += mx / U; ex += mx / U; sy += my / U; ey += my / U
            wpx = pr.get(0x1cb, 9525) / 12700 * PT
            dash = 'dashed=1;dashPattern=1 1;' if pr.get(0x1ce, 0) == 2 else ''
            cells.append(('<mxCell id="%s" value="" style="startArrow=block;startFill=1;startSize=%.1f;endArrow=none;html=1;rounded=0;strokeWidth=%.2f;%s" edge="1" parent="1">'
                          '<mxGeometry relative="1" as="geometry"><mxPoint x="%.2f" y="%.2f" as="sourcePoint"/><mxPoint x="%.2f" y="%.2f" as="targetPoint"/></mxGeometry></mxCell>')
                         % (nid(), ARROW * wpx, wpx, dash, sx * U + ox, sy * U + oy, ex * U + ox, ey * U + oy))
        elif s['text']:    # a text box, or the title
            paras, chars = text_style(s.get('style', b''), s['text']) if s.get('style') else ([], [])
            size = sizes.get(k) or next((c[1] for c in chars if c[1]), None) or title_pt
            bold = any(c[2] for c in chars)
            filled = pr.get(0x1bf, 0) & 0x10
            lined = pr.get(0x1ff, 0) & 0x8
            st = 'text;html=1;whiteSpace=nowrap;overflow=visible;'
            if s.get('type') == 1:   # the title placeholder: centred in its box
                st += 'align=center;verticalAlign=middle;'
            else:
                st += 'align=left;verticalAlign=top;spacingLeft=%.1f;spacingRight=%.1f;spacingTop=%.1f;spacingBottom=0;spacing=0;' % (9.6, 9.6, 4.8)
            if lined and k in text_left:   # a label box: its text where the PNG has it in the box
                st = st.replace('align=left;verticalAlign=top;', 'align=left;verticalAlign=middle;')
                st = st.replace('spacingLeft=9.6;spacingRight=9.6;spacingTop=4.8;', 'spacingLeft=%.2f;' % text_left[k])
            elif lined:   # a label box: sized to its text, so its text is centred in it
                st = st.replace('align=left;verticalAlign=top;', 'align=center;verticalAlign=middle;')
                st = st.replace('spacingLeft=9.6;spacingRight=9.6;spacingTop=4.8;', '')
            st += 'fontSize=%.2f;%s' % (size * PT, 'fontStyle=1;' if bold else '')
            if filled: st += 'fillColor=%s;' % grey(colour(pr.get(0x181, 0x08000004)))
            if lined:
                st += 'strokeColor=#000000;strokeWidth=%.2f;' % (pr.get(0x1cb, 9525) / 12700 * PT)
                if pr.get(0x1ce, 0) == 2: st += 'dashed=1;dashPattern=1 1;'
            if s.get('type') != 1 and pr.get(0x85, 0) == 2:
                # a text box that does not wrap: PowerPoint sizes it to its text
                lines = s['text'].split('\r')
                w = max(text_width(l, size * PT, bold) for l in lines) + 2 * 9.6
                h2 = len(lines) * 1.2 * size * PT + 2 * 4.8
                if k in geom and lined:        # a box placed on its border in the PNG
                    w, h = geom[k][2], geom[k][3]
                else:
                    h = h2
            if s.get('type') == 1:
                # the title's box, as wide as its words, about the same middle (the
                # slide's box is nearly slide-wide: it would reach past the frame)
                tw = max(text_width(l, size * PT, bold) for l in s['text'].split('\r')) + 2 * 9.6
                x, w = x + (w - tw) / 2, tw
            val = '<br>'.join(html.escape(l) for l in s['text'].replace('–', '—').split('\r'))
            cells.append(('<mxCell id="%s" value="%s" style="%s" vertex="1" parent="1">'
                          '<mxGeometry x="%.2f" y="%.2f" width="%.2f" height="%.2f" as="geometry"/></mxCell>')
                         % (nid(), html.escape(val), st, x, y, w, h))
    if frame:
        # the frame, and what makes the drawing an illustration (not a UML
        # diagram): ubl-kind, and the scale it matches its PNG in UBL at
        x0, y0, x1, y1 = frame[:4]
        cells.insert(0, ('<object id="frame" label="" ubl-kind="illustration"%s><mxCell style="rounded=0;whiteSpace=wrap;html=1;fillColor=none;strokeColor=#000000;strokeWidth=%.2f;" vertex="1" parent="1">'
                         '<mxGeometry x="%.2f" y="%.2f" width="%.2f" height="%.2f" as="geometry"/></mxCell></object>')
                     % (' ubl-png-scale="%.4f"' % scale if scale else '', frame[4] if len(frame) > 4 else 1.5, x0 + ox, y0 + oy, x1 - x0, y1 - y0))
    pg = ' page="1" pageScale="1" pageWidth="%d" pageHeight="%d"' % page if page else ' page="0"'
    return ('<mxfile host="UBL-TC" agent="UBL artwork pipeline, the Fulfilment illustrations (history/illustrations)" type="device">'
            '<diagram id="%s" name="%s"><mxGraphModel grid="0" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1"%s math="0" shadow="0">'
            '<root><mxCell id="0"/><mxCell id="1" parent="0"/>' % (name, name, pg)
            + ''.join(cells) + '</root></mxGraphModel></diagram></mxfile>')

if __name__ == '__main__':
    n, out = int(sys.argv[1]), sys.argv[2]
    a = sys.argv[3:]
    kw = {}
    if '--frame' in a: kw['frame'] = [float(v) for v in a[a.index('--frame') + 1].split(',')]
    if '--hide' in a: kw['hide'] = {int(v) for v in a[a.index('--hide') + 1].split(',') if v}
    if '--title-pt' in a: kw['title_pt'] = float(a[a.index('--title-pt') + 1])
    open(out, 'w').write(build(n, **kw))
