"""A baseline of the draw.io drawings, and the drawings held against it.

    python3 tools/drawio_baseline.py make <baseline dir> <diff dir> [<figure> ...]
    python3 tools/drawio_baseline.py compare <baseline dir> [--out <dir>] [<figure> ...]

make copies the drawings (the 78 diagrams, and the illustrations) into <baseline dir>/diagrams/, with each one's
render in <baseline dir>/renders/ and the table of how it compares with the
original PNG (summary.json, summary.txt). The renders and numbers come from
<diff dir>, a run of history/drawio-edits/diff/run.sh on the same drawings.
With figures named, only those are added (or replaced) in the baseline, the
others kept as they are (a run of history/drawio-edits/diff/one.py on those
figures is enough).

compare holds every drawing in diagrams/ against its baseline copy, and prints
one line per figure:

  same            the file is the baseline's, byte for byte
  same-drawing    the file differs, but not the model it holds, and not a pixel
                  of its render
  model           the model differs (listed below the line), not a pixel
  DRAWING         pixels differ (and the model, where listed)
  new             not in the baseline (the figures of Group A and B were made after it): not compared,
                  and not a difference

Both drawings are rendered the same way, on the baseline render's canvas (grown
by what the drawing grew), and compared pixel for pixel, with no tolerance. The
baseline copy is rendered again, not taken from renders/, so a change of
renderer cannot pass for a change of drawing; where the fresh render of the
baseline differs from the stored one, the line says so ("renderer changed").
With --out, <dir>/<figure>.png shows a differing drawing: grey where both have
ink, red where only the baseline has, blue where only the drawing has.
Exits 1 when any figure differs.
"""
import json, os, re, shutil, subprocess, sys, tempfile
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RENDER = os.path.join(ROOT, 'history', 'drawio-writer', 'render-drawio.js')
sys.path.insert(0, HERE)
import check_drawio  # noqa: E402

_g = subprocess.run(['npm', 'root', '-g'], capture_output=True, text=True).stdout.strip()
# the renders are drawn by draw.io at scale 1 and enlarged by the browser (render-drawio.js): zoomed in draw.io's own
# view, 31.5.3 and 32.x round label and edge positions differently, so a render would change with the version
NODE = dict(os.environ, NODE_PATH=os.pathsep.join(p for p in (os.environ.get('NODE_PATH'), _g) if p), DRAWIO_RENDER_DEVICE='1')


def page(path):
    return [int(v) for v in re.search(r'pageWidth="(\d+)" pageHeight="(\d+)"', open(path).read()).groups()]


def render(path, canvas, scale, out):
    subprocess.run(['node', RENDER, path, out, str(canvas[0]), str(canvas[1]), str(scale)], check=True, capture_output=True, env=NODE)
    return np.asarray(Image.open(out).convert('L'))


def model(path):
    if check_drawio.is_illustration(path):     # a picture, no model: its pixels are compared
        return {}
    cells, order = check_drawio.read(path)
    return check_drawio.model_of(cells, order)


def model_diff(base, now):
    out = []
    for group in sorted(set(base) | set(now)):
        b, n = base.get(group), now.get(group)
        if isinstance(b, list) and isinstance(n, list) and all(isinstance(x, dict) and 'id' in x for x in b + n):
            bi, ni = {x['id']: x for x in b}, {x['id']: x for x in n}
            for i in bi.keys() - ni.keys():
                out.append('%s %s: removed' % (group, i))
            for i in ni.keys() - bi.keys():
                out.append('%s %s: added' % (group, i))
            for i in sorted(bi.keys() & ni.keys()):
                for k in sorted(set(bi[i]) | set(ni[i])):
                    if bi[i].get(k) != ni[i].get(k):
                        out.append('%s %s: %s was %r, is %r' % (group, i, k, bi[i].get(k), ni[i].get(k)))
        elif b != n:
            out.append('%s differs' % group)
    return out


def make(base, diff, figs=()):
    sys.path.insert(0, os.path.join(ROOT, 'history', 'drawio-edits', 'diff'))
    from common import natural_width
    os.makedirs(os.path.join(base, 'diagrams'), exist_ok=True)
    os.makedirs(os.path.join(base, 'renders'), exist_ok=True)
    summary = json.load(open(os.path.join(base, 'summary.json'))) if figs else {}
    for n in figs or sorted(os.listdir(os.path.join(ROOT, 'diagrams'))):
        shutil.copyfile(os.path.join(ROOT, 'diagrams', n, n + '.drawio'), os.path.join(base, 'diagrams', n + '.drawio'))
        r = json.load(open(os.path.join(diff, n, 'result.json')))
        im = Image.open(os.path.join(diff, n, 'drawio.png')).convert('L')
        im.save(os.path.join(base, 'renders', n + '.png'), optimize=True)
        summary[n] = dict(canvas=list(im.size), scale=r['png_size'][0] / natural_width(n), page=page(os.path.join(ROOT, 'diagrams', n, n + '.drawio')),
                          png_size=r['png_size'], red=round(r['red'], 2), blue=round(r['blue'], 2),
                          **({'red_space_inserted': round(r['cut_red'], 2), 'blue_space_inserted': round(r['cut_blue'], 2)} if 'cut_red' in r else {}))
    summary = dict(sorted(summary.items()))
    json.dump(summary, open(os.path.join(base, 'summary.json'), 'w'), indent=1)
    with open(os.path.join(base, 'summary.txt'), 'w') as f:
        f.write('%-55s %11s %11s %7s %7s %9s %9s\n' % ('figure', 'PNG', 'canvas', 'red %', 'blue %', 'red % *', 'blue % *'))
        for n, s in summary.items():
            f.write('%-55s %11s %11s %7.2f %7.2f %9s %9s\n' % (n, '%dx%d' % tuple(s['png_size']), '%dx%d' % tuple(s['canvas']), s['red'], s['blue'],
                                                          '%.2f' % s['red_space_inserted'] if 'red_space_inserted' in s else '',
                                                          '%.2f' % s['blue_space_inserted'] if 'blue_space_inserted' in s else ''))
        f.write('\n* with the same space inserted in the PNG as in the drawing (history/drawio-edits/diff/cutpng.py)\n')
    print('%d drawings in %s' % (len(summary), base))


def compare(base, figs, out):
    summary = json.load(open(os.path.join(base, 'summary.json')))
    figs = figs or sorted(os.listdir(os.path.join(ROOT, 'diagrams')))
    tally, bad = {}, 0
    if out:
        os.makedirs(out, exist_ok=True)
    with tempfile.TemporaryDirectory() as t:
        for n in figs:
            b, d = os.path.join(base, 'diagrams', n + '.drawio'), os.path.join(ROOT, 'diagrams', n, n + '.drawio')
            if not os.path.exists(b):
                # drawn after the baseline (Group A, B, C: the TC's own sources and figures drawn from the
                # PNGs, which the baseline's tools - the model JSONs, the diff against the PNG - do not cover);
                # Ordering among them, whose source is an SVG, not a drawing
                state, notes = 'new', ['not in the baseline; not compared']
            elif not os.path.exists(d):
                state, notes = 'DRAWING', ['removed']
            elif open(b, 'rb').read() == open(d, 'rb').read():
                state, notes = 'same', []
            else:
                s = summary[n]
                pb, pd = s['page'], page(d)
                canvas = [s['canvas'][0] + max(0, round((pd[0] - pb[0]) * s['scale'])), s['canvas'][1] + max(0, round((pd[1] - pb[1]) * s['scale']))]
                A, B = render(b, canvas, s['scale'], t + '/b.png'), render(d, canvas, s['scale'], t + '/d.png')
                stored = np.asarray(Image.open(os.path.join(base, 'renders', n + '.png')).convert('L'))
                notes = model_diff(model(b), model(d))
                if A[:stored.shape[0], :stored.shape[1]].shape != stored.shape or (A[:stored.shape[0], :stored.shape[1]] != stored).any():
                    notes.insert(0, 'renderer changed: the baseline renders otherwise than when it was made')
                if (A != B).any():
                    state = 'DRAWING'
                    if out:
                        ia, ib = A < 128, B < 128
                        o = np.full(A.shape + (3,), 255, np.uint8); o[ia | ib] = (185, 185, 185)
                        o[ia & ~ib] = (220, 0, 0); o[ib & ~ia] = (0, 60, 230)
                        Image.fromarray(o).save(os.path.join(out, n + '.png'))
                    notes.insert(0, '%d pixels differ' % (A != B).sum())
                else:
                    state = 'model' if any(not x.startswith('renderer') for x in notes) else 'same-drawing'
            tally[state] = tally.get(state, 0) + 1
            bad += state in ('model', 'DRAWING')
            print('%-55s %s' % (n, state))
            for x in notes:
                print('    ' + x)
    print(' '.join('%s %d' % kv for kv in sorted(tally.items())))
    return 1 if bad else 0


if __name__ == '__main__':
    a = sys.argv[1:]
    if a[:1] == ['make'] and len(a) >= 3:
        make(a[1], a[2], a[3:])
    elif a[:1] == ['compare'] and len(a) >= 2:
        out = None
        if '--out' in a:
            i = a.index('--out'); out = a[i + 1]; del a[i:i + 2]
        sys.exit(compare(a[1], a[2:], out))
    else:
        sys.exit(__doc__)
