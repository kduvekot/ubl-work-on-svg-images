"""The comparison deck: an introduction with the table of all figures, then a page
per figure (the PNG, the drawing, the diff), in the order of the UBL 2.5
specification, with its titles. For a figure that grew, the pictures are those
of cutpng.py (the same space inserted in the PNG). Writes one HTML page per
PDF page; print.js prints them, and pdfunite joins them (see run.sh).

    python3 pdf.py <out dir>                 writes <out>/pages/p-NN.html
"""
import html, json, os, subprocess, sys
from PIL import Image, ImageDraw, ImageFont
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

# the introduction: what the document is, how to read a page, why the two differ, where to look first,
# and the table of all figures. The numbers per figure are those on its page (with the space inserted in
# the PNG where some was inserted in the drawing).
nums = {n: R(n) for n in order}
med = lambda xs: sorted(xs)[len(xs) // 2]
EX = [max(res[n]['export']) for n in order if 'export' in res[n]]
WORST = sorted(order, key=lambda n: -max(nums[n]))[:8]
sw = lambda c: '<span class="sw" style="background:%s"></span>' % c
istyle = '''<style>@page { size: A4; margin: 16mm 15mm 14mm; }
body { font-family: "Liberation Sans", Helvetica, Arial, sans-serif; font-size: 9.5pt; line-height: 1.45; color: #1a1a1a; margin: 0; }
h1 { font-size: 20pt; line-height: 1.2; margin: 0 0 1.5mm; } .sub { color: #555; margin: 0 0 5mm; }
h2 { font-size: 12pt; margin: 6mm 0 2mm; padding-bottom: 1mm; border-bottom: 0.3mm solid #ccc; }
p { margin: 0 0 2.5mm; } ul, ol { margin: 0 0 2.5mm; padding-left: 6mm; } li { margin: 0 0 1.3mm; }
.sw { display: inline-block; width: 3.4mm; height: 3.4mm; border: 0.2mm solid #777; vertical-align: -0.6mm; margin: 0 1mm 0 0; }
.legend span.item { white-space: nowrap; margin-right: 4mm; }
.facts { display: flex; gap: 3mm; margin: 0 0 3mm; } .fact { flex: 1; border: 0.3mm solid #d8d8d8; border-radius: 1.5mm; padding: 2mm 3mm; }
.fact b { display: block; font-size: 15pt; line-height: 1.2; } .fact span { color: #555; font-size: 8pt; line-height: 1.3; display: block; }
.muted { color: #666; } .new { page-break-before: always; }
table { border-collapse: collapse; width: 100%; font-size: 7.6pt; line-height: 1.25; }
th { text-align: left; border-bottom: 0.4mm solid #444; padding: 1mm 1.2mm; vertical-align: bottom; }
td { border-bottom: 0.2mm solid #e4e4e4; padding: 0.8mm 1.2mm; vertical-align: top; }
td.n, th.n { text-align: right; white-space: nowrap; } td .f { color: #777; font-size: 6.6pt; }
tbody tr:nth-child(even) td { background: #f6f6f6; } thead { display: table-header-group; } tr { page-break-inside: avoid; }
</style>'''
o = ['<!doctype html><html><head><meta charset="utf-8"><title>UBL %d figures: final review</title>' % N + istyle + '</head><body>',
     '<h1>The UBL 2.5 figures: final review</h1>',
     '<div class="sub">All %d figures of UBL 2.5: the PNG published now, against the draw.io drawing that becomes its source.<br>'
     'PNGs: UBL repository, art/%s &#183; drawings: this repository, commit %s &#183; draw.io %s</div>' % (N, ' at ' + esc(U) if U else '', C, PIN),
     '<div class="facts">'
     '<div class="fact"><b>%d</b><span>figures, one page each, in the order of the specification</span></div>' % N
     + '<div class="fact"><b>%.1f&#160;%% &#183; %.1f&#160;%%</b><span>median red &#183; blue: ink only in the PNG &#183; only in the drawing</span></div>' % (med([v[0] for v in nums.values()]), med([v[1] for v in nums.values()]))
     + '<div class="fact"><b>%d</b><span>figures with space inserted for short arrows (yellow)</span></div>' % len(_ins)
     + ('<div class="fact"><b>&#8804;&#160;%.2f&#160;%%</b><span>the published PNG against the picture shown</span></div>' % max(EX) if EX else '')
     + '</div>',

     '<h2>What this document is</h2>',
     '<p>For every figure the UBL 2.5 specification shows, one page with three pictures: the PNG that OASIS publishes now, '
     'the draw.io drawing that replaces it as the figure&#8217;s source, and the difference between the two. It is for checking '
     'that every drawing still says what its figure said. Where the two differ, the page shows it in colour.</p>',

     '<h2>How to read a page</h2>',
     '<ol><li><b>The original PNG</b>, as in the UBL repository (art/), at its own pixel size (1142&#8211;3426&#160;px wide), not resampled.</li>'
     '<li><b>The draw.io drawing</b>, drawn by draw.io&#8217;s own code onto exactly the PNG&#8217;s canvas, at the scale that makes it as wide.</li>'
     '<li><b>The difference</b>, with a tolerance of 2&#160;px per 1480&#160;px of width (5&#160;px on a PNG the page&#8217;s width):<br>'
     '<span class="legend"><span class="item">%sink in both</span><span class="item">%sonly in the PNG (red)</span>'
     '<span class="item">%sonly in the drawing (blue)</span><span class="item">%sspace inserted (yellow, below)</span></span></li></ol>'
     % (sw('#b9b9b9'), sw('#dc0000'), sw('#003ce6'), sw('#ffd966')),
     '<p>Above the pictures: the figure&#8217;s number and title in the specification, its file name, and red and blue in '
     'per cent of the PNG&#8217;s ink. Pictures wider than 2000&#160;px are shown at half size, to keep the file small; '
     'the numbers are measured at full size.</p>',

     '<h2>Why some difference is expected</h2>',
     '<p>The drawings keep every element, label and flow of the figures, not their exact pixels:</p><ul>'
     '<li><b>Lines</b> have fixed weights: 1, and 2 for documents and the frame. The PNGs&#8217; vary.</li>'
     '<li><b>Text</b> is one size, draw.io&#8217;s 12&#160;pt, where the PNGs set their own; in two Tender figures, long '
     'one-line labels are broken over two lines. Text set otherwise moves every letter, so it is most of the red and blue.</li>'
     '<li><b>Flows</b> are straight: some elements moved by up to 7&#160;px (at 1480&#160;px wide) to make them so.</li>'
     '<li><b>Space inserted</b> (%d figures): every arrow is at least 3 times its head long. Where one was shorter, space was '
     'inserted across the whole figure, a band of height or a column of width, and everything beyond it moved along. On those '
     'pages the PNG gets the same space at the same places (yellow on all three pictures), so that both are compared with the '
     'same things moved: lines that cross a cut run on, and where the drawing kept a shape whole, the cut steps round it '
     '(%d times, in %d figures). The table gives both numbers: with the space inserted in the PNG, as on the pages, and without.</li>'
     % (len(_ins), KEPT, KEPTF)
     + ('<li><b>Figures drawn later</b> (%d, Groups A, B and C): drawn on their PNG&#8217;s pixels and shown at that scale; '
        'the TC&#8217;s own drawings of Group A are placed by their ink (scaled to the PNG&#8217;s ink and moved onto it).</li>' % NL if NL else '')
     + ('<li><b>Illustrations</b> (%d: the Fulfilment and CPFR step figures): pictures for the reader, drawn from their sources at '
        'the PNG&#8217;s scale, in grey. A picture drawn anew (the pallet of boxes) differs from the PNG&#8217;s photo.</li>' % NI if NI else '')
     + '</ul>',

     ('<h2>The picture shown is the one UBL will publish</h2>'
      '<p>Every page also says how far the PNG that goes to the UBL repository (to-ubl-repo/art: 600&#160;dpi, made from the '
      'exported SVG) is from the drawing shown: at most %.2f&#160;%% of its ink is in one of the two only, the median %.2f&#160;%%. '
      'What differs is where a few labels&#8217; text, made SVG text by the export, sits up to a unit from draw.io&#8217;s own.</p>'
      % (max(EX), med(EX)) if EX else ''),

     '<h2>Where to look first</h2>',
     '<p>The figures that differ most from their PNG (the larger of red and blue, as on their page). Look for a meaning that '
     'changed, not for pixels: most of it is text set in another size or over more lines.</p><ul>'
     + ''.join('<li><b>%d. %s</b> <span class="muted">(%s)</span>: red %.1f&#160;%%, blue %.1f&#160;%%%s</li>'
               % (order.index(n) + 1, esc(titles.get(n, n)), esc(n), *nums[n], ', space inserted' if cut(n) else '') for n in WORST)
     + '</ul>',

     '<h2>All figures</h2>',
     '<p class="muted">Red and blue in per cent of the PNG&#8217;s ink, as on the figure&#8217;s page. &#8220;Without&#8221;: the same '
     'with no space inserted in the PNG (everything after a band counts as moved). &#8220;Published&#8221;: the published PNG against '
     'the picture shown.</p>',
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
