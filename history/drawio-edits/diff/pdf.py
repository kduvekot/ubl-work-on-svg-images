"""The comparison deck: an introduction with the table of all figures, then a page
per figure (the PNG, the drawing, the diff), in the order of the UBL 2.5
specification, with its titles. For a figure that grew, the pictures are those
of cutpng.py (the same space inserted in the PNG). Writes one HTML page per
PDF page; print.js prints them, and pdfunite joins them (see run.sh).

    python3 pdf.py <out dir>                 writes <out>/pages/p-NN.html
"""
import html, json, os, subprocess, sys
from PIL import Image, ImageDraw, ImageFont
from common import ROOT, figures, illustration
d = sys.argv[1]; out = d + '/pages/p'; os.makedirs(d + '/pages', exist_ok=True)
C = subprocess.run(['git', '-C', ROOT, 'rev-parse', '--short', 'HEAD'], capture_output=True, text=True).stdout.strip()
order, titles = [n for n, t in figures()], dict(figures())
esc = lambda s: html.escape(s, quote=True)
font = ImageFont.truetype('/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf', 26)
res = {n: json.load(open(f'{d}/{n}/result.json')) for n in order}
_ins = json.load(open(d + '/insertions.json'))
KEPT = sum(len(k) for v in _ins.values() for a, c, e, k in v); KEPTF = sum(1 for v in _ins.values() if any(k for a, c, e, k in v))
for n in order: res[n]['bands'] = [[ax, e] for ax, c, e, k in _ins.get(n, [])]
cut = lambda n: 'cut_red' in res[n]
R = lambda n: (res[n]['cut_red'], res[n]['cut_blue']) if cut(n) else (res[n]['red'], res[n]['blue'])
def compose(n):
    if cut(n):
        parts = [('1. original PNG, with the same space inserted as in the drawing (yellow)', 'png_cut_b.png'), ('2. draw.io drawing (diagrams/), on that canvas', 'drawio_cut_b.png'),
                 ('3. diff: grey both, red PNG only, blue draw.io only; yellow: space inserted', 'overlay_cut_b.png')]
    else:
      parts = [('1. original PNG (UBL art/, own size)', 'png.png'), ('2. draw.io drawing (diagrams/), on the PNG\'s canvas', 'drawio_b.png'),
             ('3. diff: grey both, red PNG only, blue draw.io only; yellow: space inserted', 'overlay_b.png')]
    if not cut(n): parts = [(l, p.replace('_b.png', '.png')) for l, p in parts]
    ims = []
    for l, p in parts:
        im = Image.open(f'{d}/{n}/{p}').convert('RGB'); f = 2 if im.width > 2000 else 1; ims.append((l, im if f == 1 else im.resize((im.width // f, im.height // f), Image.LANCZOS)))
    w, h = ims[0][1].size; wide = w / h > 1.25; lab, gap = 40, 24
    W, H = (w, 3 * (h + lab) + 2 * gap) if wide else (3 * w + 2 * gap, h + lab)
    c = Image.new('RGB', (W, H), 'white'); g = ImageDraw.Draw(c)
    for k, (l, im) in enumerate(ims):
        x, y = (0, k * (h + lab + gap)) if wide else (k * (w + gap), 0)
        g.text((x + 4, y + 6), l, fill=(40, 40, 40), font=font); c.paste(im, (x, y + lab))
        g.rectangle([x, y + lab, x + im.width - 1, y + lab + im.height - 1], outline=(170, 170, 170), width=2)
    p = f'{d}/pages/{n}.png'; c.quantize(64, method=Image.Quantize.MEDIANCUT).save(p, optimize=True)
    bw, bh = (186, 240) if wide else (273, 160)
    k = min(bw / W, bh / H); return p, wide, W * k, H * k
style = '''<style>@page { size: A4; margin: 12mm; }
body { font-family: "Liberation Sans", Helvetica, Arial, sans-serif; font-size: 9pt; color: #111; margin: 0; }
h1 { font-size: 16pt; margin: 0 0 3mm; } h2 { font-size: 11pt; margin: 0 0 2mm; } img { display: block; }
table { border-collapse: collapse; font-size: 7.5pt; } td, th { border-bottom: 0.2mm solid #ccc; padding: 0.4mm 1.5mm; text-align: left; }
td.n { text-align: right; }</style>'''
N = len(order); NI = sum(1 for n in order if illustration(n))
o = ['<!doctype html><html><head><meta charset="utf-8"><title>%d figures: original PNG vs draw.io, space inserted</title>' % N + style + '</head><body>',
     '''<h1>The '''+str(N)+''' figures: original PNG vs draw.io render</h1>
<p>Per figure: (1) the original PNG as OASIS publishes it (UBL repository, art/), at its own pixel size (1142&#8211;3426&#160;px
wide), not resampled; (2) the current draw.io drawing, the figure's source of truth (diagrams/, commit '''+C+''': natural scale, whole pixels,
fixed line weights, every label draw.io's own 12&#160;pt), rendered with draw.io&#8217;s own code (viewer 31.5.3) onto exactly the PNG&#8217;s canvas: the drawing, built at
its natural scale, is drawn at the PNG&#8217;s width / its own; the frame lines of the two agree within 1&#160;px per 1480&#160;px of width
in every figure; (3) the overlay: grey where both have ink, <b style="color:#c00">red</b> where the PNG has ink and draw.io none,
<b style="color:#00c">blue</b> where draw.io has ink and the PNG none, within 2&#160;px per 1480&#160;px of width (as in the SVG
comparison: 5&#160;px for a 3425-px PNG, 2&#160;px for the 1142-px one). Percentages are of the PNG&#8217;s ink, measured at the
PNG&#8217;s own size; in this PDF, pictures wider than 2000&#160;px are shown at half size to keep the file small. The PNG draws with its
own line weights and fonts; the drawing&#8217;s weights are fixed (1, and 2 for documents and the frame) and some elements moved up to
7&#160;px (at 1480) to make flows straight, and every label is 12&#160;pt where the PNG sets its own sizes (in two Tender figures long one-line labels are broken over two lines), all of which counts as difference. <b>Arrows at least 3 times their head long:</b> in 35 figures, where an arrow was shorter than 30&#160;px, space was inserted across the whole figure (a band of height or a column of width), and everything beyond it moved along. For those figures <b>the PNG gets the same space inserted</b>, at the same places (marked <b style="background:#ffd966">yellow</b> on all three pictures): at each cut, in order, a line of pixels next to it (the one with the least ink) is repeated to fill the inserted width, so lines that cross it (frame, lane dividers, flows) run on unbroken. Where the drawing kept a shape whole that the space ran through (it stayed, or moved whole past the space; '''+'%d times in %d figures' % (KEPT, KEPTF)+'''), the cut in the PNG steps round that shape the same way. So both pictures are compared with the same things moved, and what differs is what differed before the arrows were lengthened. The table gives both numbers: with the space inserted in the PNG (used on the pages) and without (everything after a band counts as moved). The other '''+str(N - NI - len(_ins))+''' diagrams differ as before. '''+('''<b>'''+str(NI)+''' illustrations</b> (the Fulfilment figures) are not UML diagrams but pictures for the reader (history/illustrations): drawn from the deck they come from, placed where the PNG has them, at the PNG&#8217;s own scale (not 12&#160;pt), in grey; where a picture was drawn again (the pallet of boxes), it differs from the PNG&#8217;s photo. ''' if NI else '')+'''In the order of the UBL 2.5 specification, with its titles.</p>
<table><tr><th>#</th><th>title in the specification</th><th>figure</th><th>PNG size</th><th>red %</th><th>blue %</th><th>space inserted</th><th>without: red %</th><th>blue %</th></tr>''']
for i, n in enumerate(order, 1):
    r = res[n]
    o.append('<tr><td>%d</td><td>%s</td><td>%s</td><td>%d&#215;%d</td><td class="n">%.2f</td><td class="n">%.2f</td>' % (i, esc(titles.get(n, '')), esc(n), r['png_size'][0], r['png_size'][1], *R(n)) + '<td>%s</td>' % ('%d&#215;, %d&#160;px' % (len(r.get('bands', [])), sum(w for ax, w in r.get('bands', []))) if r.get('bands') else '') + ('<td class="n">%.2f</td><td class="n">%.2f</td></tr>' % (r['red'], r['blue']) if cut(n) else '<td></td><td></td></tr>'))
o.append('</table></body></html>')
open(out + '-00.html', 'w').write('\n'.join(o))
for i, n in enumerate(order, 1):
    p, wide, mw, mh = compose(n); r = res[n]
    page = style.replace('size: A4;', 'size: A4%s;' % ('' if wide else ' landscape'))
    open('%s-%02d.html' % (out, i), 'w').write('<!doctype html><html><head><meta charset="utf-8">' + page + '</head><body>'
        + '<h2>%d. %s</h2><div style="margin:0 0 2mm">%s &#8212; PNG %d&#215;%d &#8212; red %.2f %%, blue %.2f %%%s</div><img src="%s" style="width:%.1fmm;height:%.1fmm">' % (
            i, esc(titles.get(n, n)), esc(n), r['png_size'][0], r['png_size'][1], *R(n), (' (without the space in the PNG: red %.2f %%, blue %.2f %%)' % (r['red'], r['blue']) if cut(n) else ''), esc(p), mw, mh) + ('<div style="margin:1mm 0 0">space inserted: %s</div>' % ', '.join('%d&#160;px %s' % (w, 'wide' if ax == 0 else 'high') for ax, w in r.get('bands', [])) if r.get('bands') else '') + '</body></html>')
print('ok')
