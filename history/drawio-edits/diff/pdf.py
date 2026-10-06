"""The comparison deck: an introduction with the table of all figures, then a page
per figure (the PNG, the drawing, the diff), in the order of the UBL 2.5
specification, with its titles. For a figure that grew, the pictures are those
of cutpng.py (the same space inserted in the PNG). Writes one HTML page per
PDF page; print.js prints them, and pdfunite joins them (see run.sh).

    python3 pdf.py <out dir>                 writes <out>/pages/p-NN.html
"""
import html, json, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage
from common import ROOT, UBL, drawn_later, figures, illustration
d = sys.argv[1]; out = d + '/pages/p'; os.makedirs(d + '/pages', exist_ok=True)
C = subprocess.run(['git', '-C', ROOT, 'rev-parse', '--short', 'HEAD'], capture_output=True, text=True).stdout.strip()
U = subprocess.run(['git', '-C', UBL, 'log', '-1', '--format=%h, %cs'], capture_output=True, text=True).stdout.strip()
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
N = len(order); NI = sum(1 for n in order if illustration(n)); NL = sum(1 for n in order if drawn_later(n))
PIN = json.load(open(ROOT + '/tools/drawio-version.json'))['version']

nums = {n: R(n) for n in order}
med = lambda xs: sorted(xs)[len(xs) // 2]
EX = [max(res[n]['export']) for n in order if 'export' in res[n]]
WORST = sorted(order, key=lambda n: -max(nums[n]))[:8]
sw = lambda c: '<span class="sw" style="background:%s"></span>' % c


# two examples for the introduction, found in this run's own pictures, so that they show what the pages show
def _colours(path):
    a = np.asarray(Image.open(path).convert('RGB')).astype(int)
    red = (a[..., 0] > 180) & (a[..., 1] < 80) & (a[..., 2] < 80)
    blue = (a[..., 2] > 150) & (a[..., 0] < 120)
    yellow = (a[..., 0] > 240) & (a[..., 2] < 225) & (a[..., 1] > 180)
    grey = ((abs(a[..., 0] - a[..., 1]) < 25) & (a[..., 0] > 80) & (a[..., 0] < 215)) | ((a[..., 0] > 150) & (a[..., 0] < 215) & (a[..., 2] < 160))
    return red, blue, yellow, grey


def _best(score, win):
    """the window of size win with the highest sum of score: (y, x, sum)"""
    ii = np.pad(score, ((1, 0), (1, 0))).cumsum(0).cumsum(1); h, w = win
    s = ii[h:, w:] - ii[:-h, w:] - ii[h:, :-w] + ii[:-h, :-w]
    y, x = np.unravel_index(np.argmax(s), s.shape)
    return y, x, s[y, x] / (h * w)


def example_text():
    """a label set otherwise: the place in a UML diagram (no space inserted) where red and blue lie closest together"""
    found = []
    for n in order:
        r = res[n]
        if cut(n) or r.get('placed') != 'natural' or not 3 < r['red'] < 8:
            continue
        red, blue, _, _ = _colours(f'{d}/{n}/overlay.png'); W = red.shape[1]; win = (int(W * 0.06), int(W * 0.2))
        found.append(_best(np.minimum(ndimage.uniform_filter(red.astype(float), 15), ndimage.uniform_filter(blue.astype(float), 15)), win) + (n, win))
    y, x, _, n, (h, w) = max(found, key=lambda f: f[2])
    Image.open(f'{d}/{n}/overlay.png').convert('RGB').crop((x, y, x + w, y + h)).save(d + '/pages/ex-text.png')
    return n


def example_space():
    """space inserted: a band crossed by ink that runs on, with the least red and blue near it; the PNG with the space,
    the drawing and the comparison side by side, cut below the first band"""
    found = []
    for n in order:
        if not cut(n):
            continue
        red, blue, yellow, grey = _colours(f'{d}/{n}/overlay_cut_b.png'); W = red.shape[1]; win = (int(W * 0.14), int(W * 0.22))
        score = (ndimage.binary_dilation(yellow, iterations=6) & grey) * 3.0 + yellow * 0.02 + grey * 0.3 - 6 * ndimage.binary_dilation(red | blue, iterations=2)
        found.append(_best(score, win) + (n, win))
    y, x, _, n, (h, w) = max(found, key=lambda f: f[2])
    _, _, yellow, _ = _colours(f'{d}/{n}/overlay_cut_b.png')
    rows = np.nonzero(yellow[y:y + h, x:x + w].mean(1) > 0.5)[0]
    if len(rows):
        end = np.argmax(np.diff(np.append(rows, 10 ** 6)) > 1)       # the first band's last row, in rows
        h = min(h, rows[end] + 2 * (rows[end] - rows[0] + 1))
    parts = [Image.open(f'{d}/{n}/{k}.png').convert('RGB').crop((x, y, x + w, y + h)) for k in ('png_cut_b', 'drawio_cut_b', 'overlay_cut_b')]
    lab, gap = 40, 30
    c = Image.new('RGB', (3 * w + 2 * gap, h + lab), 'white'); g = ImageDraw.Draw(c)
    for k, (im, t) in enumerate(zip(parts, ('1. the PNG, with the space', '2. the drawing', '3. the comparison'))):
        g.text((k * (w + gap) + 4, 6), t, fill=(40, 40, 40), font=font); c.paste(im, (k * (w + gap), lab))
        g.rectangle([k * (w + gap), lab, k * (w + gap) + w - 1, lab + h - 1], outline=(170, 170, 170), width=2)
    c.save(d + '/pages/ex-space.png')
    return n


EXT, EXS = example_text(), (example_space() if _ins else None)
num = lambda n: order.index(n) + 1
istyle = '''<style>@page { size: A4; margin: 16mm 16mm 14mm; }
body { font-family: "Liberation Sans", Helvetica, Arial, sans-serif; font-size: 9.5pt; line-height: 1.45; color: #1a1a1a; margin: 0; }
h1 { font-size: 19pt; line-height: 1.2; margin: 0 0 1.5mm; } .sub { color: #555; margin: 0 0 5mm; }
h2 { font-size: 12pt; margin: 6mm 0 2mm; padding-bottom: 1mm; border-bottom: 0.3mm solid #ccc; page-break-after: avoid; }
p { margin: 0 0 2.5mm; } ul { margin: 0 0 2.5mm; padding-left: 6mm; } li { margin: 0 0 1.4mm; }
ul.dash { list-style: none; padding-left: 5mm; } ul.dash > li::before { content: "\\2014\\00a0"; margin-left: -5mm; }
.sw { display: inline-block; width: 3.4mm; height: 3.4mm; border: 0.2mm solid #777; vertical-align: -0.6mm; margin: 0 1mm 0 0; }
.legend { display: block; margin: 1mm 0 0; } .legend span.item { white-space: nowrap; margin-right: 4mm; }
.facts { display: flex; gap: 3mm; margin: 0 0 2mm; } .fact { flex: 1; border: 0.3mm solid #d8d8d8; border-radius: 1.5mm; padding: 2mm 3mm; }
.fact b { display: block; font-size: 15pt; line-height: 1.2; } .fact span { color: #555; font-size: 8pt; line-height: 1.3; display: block; }
figure { margin: 2mm 0 4mm; page-break-inside: avoid; } figure img { display: block; border: 0.2mm solid #ccc; }
figcaption { font-size: 8.5pt; color: #444; margin-top: 1.2mm; } .muted { color: #666; }
table { border-collapse: collapse; width: 100%; font-size: 7.6pt; line-height: 1.25; }
th { text-align: left; border-bottom: 0.4mm solid #444; padding: 1mm 1.2mm; vertical-align: bottom; }
td { border-bottom: 0.2mm solid #e4e4e4; padding: 0.8mm 1.2mm; vertical-align: top; }
td.n, th.n { text-align: right; white-space: nowrap; } td .f { color: #777; font-size: 6.6pt; }
tbody tr:nth-child(even) td { background: #f6f6f6; } thead { display: table-header-group; } tr { page-break-inside: avoid; }
</style>'''
o = ['<!doctype html><html><head><meta charset="utf-8"><title>UBL 2.5 figures: review of the draw.io sources</title>' + istyle + '</head><body>',
     '<h1>UBL 2.5 Figures: Review of the draw.io Sources</h1>',
     '<div class="sub">Each figure as published in UBL 2.5, compared with the draw.io drawing that is to become its source.<br>'
     'PNGs: UBL repository, art/%s &#183; drawings: this repository, commit %s &#183; draw.io %s</div>' % (' at ' + esc(U) if U else '', C, PIN),
     '<div class="facts">'
     '<div class="fact"><b>%d</b><span>figures, one page each, in the order of the specification</span></div>' % N
     + '<div class="fact"><b>%.1f&#160;%% &#183; %.1f&#160;%%</b><span>median red &#183; blue (section 3)</span></div>' % (med([v[0] for v in nums.values()]), med([v[1] for v in nums.values()]))
     + '<div class="fact"><b>%d</b><span>figures with space inserted (section 4)</span></div>' % len(_ins)
     + ('<div class="fact"><b>&#8804;&#160;%.2f&#160;%%</b><span>difference with the images UBL will publish (section 5)</span></div>' % max(EX) if EX else '')
     + '</div>',

     '<h2>1 Introduction</h2>',
     '<p>UBL 2.5 contains %d figures: the diagrams of its business processes, the illustrations of fulfilment and of '
     'collaborative planning, and a number of reference figures. They are published as PNG images. For most of them the '
     'original sources are no longer available, so a figure could not be corrected or extended without first being drawn again.</p>' % N,
     '<p>Each figure has therefore been redrawn in draw.io, an open-source diagram editor. Once committed to the UBL repository, '
     'the drawing (a <i>.drawio</i> file) is the figure&#8217;s source: the build renders from it the SVG and PNG images that the '
     'specification uses, so that no image has to be exported by hand. The redrawing does not change what any figure says; '
     'corrections to the content of the figures are left for their next revision.</p>',
     '<p>This document allows the Technical Committee to verify that each drawing conveys the same content as the figure '
     'published today. Specifically, it provides the following:</p>'
     '<ul class="dash"><li>A page for every figure, in the order of the specification, with the published PNG, the drawing, '
     'and the two laid on top of each other.</li>'
     '<li>For every figure, the share of each picture that the other does not have, as a guide to where to look.</li>'
     '<li>A list of the figures that differ most (section 6) and a table of all figures (section 7).</li></ul>',

     '<h2>2 What each page shows</h2>',
     '<p>Each page is headed with the figure&#8217;s number and title in the specification, its file name, and two numbers, '
     'red and blue (section 3). It shows three pictures of the figure, at the same size, so that one can be laid on the other:</p>'
     '<ul class="dash"><li><b>1. The published PNG</b>: the image in the UBL repository (art/), as published with UBL 2.5, '
     'at its own pixel size and not resampled.</li>'
     '<li><b>2. The draw.io drawing</b>: the new source, drawn by draw.io&#8217;s own drawing code onto exactly the canvas of the '
     'PNG, at the scale that makes it as wide.</li>'
     '<li><b>3. The comparison</b>: the two laid on top of each other.'
     '<span class="legend"><span class="item">%sink in both</span><span class="item">%sonly in the PNG: red</span>'
     '<span class="item">%sonly in the drawing: blue</span><span class="item">%sspace inserted: yellow (section 4)</span></span></li></ul>'
     % (sw('#b9b9b9'), sw('#dc0000'), sw('#003ce6'), sw('#fdeeb6')),
     '<p>Ink in the two pictures counts as the same when it lies within 2 pixels per 1480 pixels of width (5 pixels in a PNG '
     'the width of the page). Pictures wider than 2000 pixels are shown at half size, to keep this document small; the numbers '
     'are measured at full size.</p>',

     '<h2>3 Reading red and blue</h2>',
     '<p>Red is the ink of the PNG that the drawing does not have; blue is the ink of the drawing that the PNG does not have. '
     'Both are given in per cent of the PNG&#8217;s ink. Red and blue are expected on every page, and do not of themselves '
     'indicate an error: the drawings keep every element, label and flow of the figures, but not every pixel.</p>'
     '<ul class="dash"><li><b>Text.</b> All labels are set in one size, draw.io&#8217;s 12 point, where the PNGs use several. '
     'A label set in another size, or slightly to one side, appears twice: in red where the PNG has it and in blue where the '
     'drawing has it (Example 1). In two Tender figures, long one-line labels are broken over two lines. Text accounts for '
     'most of the red and blue.</li>'
     '<li><b>Lines</b> are drawn with fixed weights: 1, and 2 for documents and the frame. The PNGs&#8217; weights vary.</li>'
     '<li><b>Flows</b> are made straight: some elements were moved by up to 7 pixels (at 1480 pixels wide) to do so.</li>'
     + ('<li><b>Figures drawn later</b> (%d, of Groups A, B and C) were drawn on the pixels of their PNG and are shown at that '
        'scale; the TC&#8217;s own drawings of Group A are placed by their ink (scaled to the width of the PNG&#8217;s ink and '
        'moved onto it).</li>' % NL if NL else '')
     + ('<li><b>Illustrations</b> (%d: the Fulfilment and the CPFR step figures) are pictures for the reader, drawn from their '
        'sources at the scale of the PNG, in grey. A picture drawn anew, such as the pallet of boxes, differs from the PNG&#8217;s '
        'photograph.</li>' % NI if NI else '')
     + '</ul>',
     '<figure><img src="%s" style="width:110mm"><figcaption>Example 1, from figure %d (%s): one label and its box, set slightly '
     'otherwise. The red is where the PNG has them, the blue where the drawing has them, the grey where the two agree.</figcaption></figure>'
     % (esc(d + '/pages/ex-text.png'), num(EXT), esc(titles.get(EXT, EXT))),
     '<p>A reviewer therefore looks for a difference in meaning: an element, label, guard or flow that is in one picture and '
     'not in the other, or a flow that joins other elements. A red word with the same word in blue beside it is one word, '
     'set otherwise.</p>',
     ]
if EXS:
    o += ['<h2>4 Inserted space (yellow)</h2>',
          '<p>In the drawings, every arrow is at least three times as long as its head. Where an arrow in the PNG was shorter, space '
          'was inserted across the whole figure, a band of height or a column of width, and everything beyond it moved along; '
          'this was so in %d figures. To compare like with like, the same space is inserted in the PNG at the same places, and '
          'marked yellow in all three pictures (Example 2). Lines that cross a band run on unbroken; where the drawing kept a '
          'shape whole, the band steps round it (%d times, in %d figures). For these figures the table gives red and blue both '
          'with the space inserted in the PNG, as on their pages, and without it, where everything after a band counts as moved.</p>'
          % (len(_ins), KEPT, KEPTF),
          '<figure><img src="%s" style="width:168mm"><figcaption>Example 2, from figure %d (%s): a band of space inserted below a '
          'box, crossed by the flow that leaves it; the PNG has the same band, and the flow runs on through it in both.</figcaption></figure>'
          % (esc(d + '/pages/ex-space.png'), num(EXS), esc(titles.get(EXS, EXS)))]
if EX:
    o += ['<h2>5 The images UBL will publish</h2>',
          '<p>The drawing shown on each page is the same picture as the PNG that will be committed to the UBL repository '
          '(to-ubl-repo/art: 600 dpi, rendered from the exported SVG). Each page states the difference between the two: at most '
          '%.2f&#160;%% of the ink, with a median of %.2f&#160;%%. What differs is only where a few labels, written as SVG text by '
          'the export, lie up to one unit from where draw.io places them.</p>' % (max(EX), med(EX))]
o += ['<h2>6 Figures that differ most</h2>',
      '<p>The figures with the most red or blue, as given on their pages. Most of it is text set in another size or over more '
      'lines; these pages are nevertheless the first to read.</p><ul class="dash">'
      + ''.join('<li><b>%d. %s</b> <span class="muted">(%s)</span>: red %.1f&#160;%%, blue %.1f&#160;%%%s</li>'
                % (num(n), esc(titles.get(n, n)), esc(n), *nums[n], '; space inserted' if cut(n) else '') for n in WORST)
      + '</ul>',
      '<h2>7 All figures</h2>',
      '<p class="muted">Red and blue in per cent of the PNG&#8217;s ink, as on the figure&#8217;s page. &#8220;Without&#8221;: red and '
      'blue with no space inserted in the PNG. &#8220;Published&#8221;: the difference with the image UBL will publish (section 5).</p>',
      '<table><thead><tr><th>#</th><th>figure</th><th class="n">PNG size</th><th class="n">red&#160;%</th><th class="n">blue&#160;%</th>'
      '<th>space inserted</th><th class="n">without: red&#160;%</th><th class="n">blue&#160;%</th><th class="n">published&#160;%</th></tr></thead><tbody>']
for i, n in enumerate(order, 1):
    r = res[n]
    o.append('<tr><td>%d</td><td>%s<br><span class="f">%s</span></td><td class="n">%d&#215;%d</td><td class="n">%.2f</td><td class="n">%.2f</td>'
             % (i, esc(titles.get(n, '')), esc(n), r['png_size'][0], r['png_size'][1], *nums[n])
             + '<td>%s</td>' % ('%d&#215;, %d&#160;px' % (len(r['bands']), sum(w for ax, w in r['bands'])) if r.get('bands') else '')
             + ('<td class="n">%.2f</td><td class="n">%.2f</td>' % (r['red'], r['blue']) if cut(n) else '<td></td><td></td>')
             + ('<td class="n">%.2f</td></tr>' % max(r['export']) if 'export' in r else '<td></td></tr>'))
o.append('</tbody></table></body></html>')
open(out + '-00.html', 'w').write('\n'.join(o))
for i, n in enumerate(order, 1):
    p, wide, mw, mh = compose(n); r = res[n]
    page = style.replace('size: A4;', 'size: A4%s;' % ('' if wide else ' landscape'))
    open('%s-%02d.html' % (out, i), 'w').write('<!doctype html><html><head><meta charset="utf-8">' + page + '</head><body>'
        + '<h2>%d. %s</h2><div style="margin:0 0 2mm">%s &#8212; PNG %d&#215;%d &#8212; red %.2f %%, blue %.2f %%%s</div><img src="%s" style="width:%.1fmm;height:%.1fmm">' % (
            i, esc(titles.get(n, n)), esc(n), r['png_size'][0], r['png_size'][1], *R(n), (' (without the space in the PNG: red %.2f %%, blue %.2f %%)' % (r['red'], r['blue']) if cut(n) else ''), esc(p), mw, mh) + ('<div style="margin:1mm 0 0">space inserted: %s</div>' % ', '.join('%d&#160;px %s' % (w, 'wide' if ax == 0 else 'high') for ax, w in r.get('bands', [])) if r.get('bands') else '')
        + ('<div style="margin:1mm 0 0">the published PNG (to-ubl-repo/art) against this render: %.2f&#160;%% of its ink in one only</div>' % max(r['export']) if 'export' in r else '') + '</body></html>')
print('ok')
