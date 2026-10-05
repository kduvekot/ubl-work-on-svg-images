"""Is there a newer draw.io, and would moving to it change anything?

    python3 tools/drawio_upgrade.py --check
    python3 tools/drawio_upgrade.py [--to <version>] [--out <dir>] [<figure> ...]

The export and every render use the viewer of one draw.io release, the pin in
tools/drawio-version.json. This tool asks where draw.io is now:

  pin     the release pinned here;
  tag     the newest release that can be pinned: the VERSION on jgraph/drawio's
          dev branch, if that release's tag has a viewer (the pin is a tag, so an
          export can be made again the same);
  live    what app.diagrams.net serves, the editor people edit in. It can be
          ahead of every tag.

--check stops there: exit 0 when the pin is the newest tag, 1 when a newer one
exists, 2 when it could not be found out.

Without --check, and when a newer tag exists (or --to names a release), it
exports all the drawings in diagrams/ (or the figures named) with the pin and
with the candidate, into scratch directories, and compares, per figure:

  svg      the exported SVG, but for the "(draw.io <version>)" in its comment;
  art      the 600 dpi PNG, pixel for pixel;
  htmlart  the web PNG, pixel for pixel;
  render   the drawing as draw.io's viewer draws it, at the baseline's canvas, pixel
           for pixel: drawn at scale 1 and enlarged by the browser
           (DRAWIO_RENDER_DEVICE=1 in history/drawio-writer/render-drawio.js), as zoomed
           in the viewer the versions differ in rounding, not in the drawing.

A figure is "same" when all four are, else "DIFFERENT", with what differs. Where
pixels differ, <out>/<figure>-<kind>.png shows it: grey where both have ink, red
where only the pin has, blue where only the candidate has. The verdict:

  SAFE      every figure the same: moving the pin changes no export, no render;
  REVIEW    n figures differ: look at the images, then decide (README,
            "Upgrading draw.io").

Exit 0 for SAFE, 1 for REVIEW, 2 when something could not be done. The tool
never changes the pin or the baseline.

What it cannot show is how the newer *editor* saves a drawing: that is the manual
check in the README. And where live is ahead of the candidate, it says so: what
was compared is the candidate, not what people edit in.
"""
import json, os, re, subprocess, sys, tempfile, urllib.request, concurrent.futures as cf
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PIN_FILE = os.path.join(HERE, 'drawio-version.json')
EXPORT = os.path.join(HERE, 'export_drawio.js')
RENDER = os.path.join(ROOT, 'history', 'drawio-writer', 'render-drawio.js')
BASELINE = os.path.join(ROOT, 'baselines', '2026-10-05')   # canvas and scale of each figure's render
RAW = 'https://raw.githubusercontent.com/jgraph/drawio/%s/'
VIEWER = 'src/main/webapp/js/viewer-static.min.js'
LIVE = 'https://viewer.diagrams.net/js/viewer-static.min.js'
VER = re.compile(r'^\d+\.\d+\.\d+$')

_g = subprocess.run(['npm', 'root', '-g'], capture_output=True, text=True).stdout.strip()
NODE = dict(os.environ, NODE_PATH=os.pathsep.join(p for p in (os.environ.get('NODE_PATH'), _g) if p))


def get(url, limit=None):
    req = urllib.request.Request(url, headers={'User-Agent': 'ubl-drawio-upgrade'})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read(limit) if limit else r.read()


def exists(url):
    try:
        req = urllib.request.Request(url, method='HEAD', headers={'User-Agent': 'ubl-drawio-upgrade'})
        return urllib.request.urlopen(req, timeout=60).status == 200
    except Exception:
        return False


def pinned():
    return json.load(open(PIN_FILE))['version']


def where_is_draw_io():
    """(pin, newest pinnable tag or None, live or None) and a note for each."""
    pin, tag, live, notes = pinned(), None, None, []
    try:
        dev = get(RAW % 'dev' + 'VERSION').decode().strip()
        if not VER.match(dev):
            raise ValueError(repr(dev))
        if exists(RAW % ('v' + dev) + VIEWER):
            tag = dev
        else:
            notes.append('dev says %s, but the tag v%s has no viewer (yet)' % (dev, dev))
    except Exception as e:
        notes.append('newest tag: could not be read (%s)' % e)
    try:
        m = re.search(rb'EditorUi\.VERSION="(\d+\.\d+\.\d+)"', get(LIVE))
        live = m.group(1).decode() if m else None
        if not live:
            notes.append('live: no version in %s' % LIVE)
    except Exception as e:
        notes.append('live: could not be read (%s)' % e)
    return pin, tag, live, notes


def newer(a, b):
    return tuple(map(int, a.split('.'))) > tuple(map(int, b.split('.')))


def run_export(version, out, files, scratch):
    env = dict(NODE, DRAWIO_VERSION=version)
    r = subprocess.run(['node', EXPORT, out] + files, capture_output=True, text=True, env=env)
    if r.returncode:
        raise RuntimeError('export with %s failed: %s' % (version, (r.stderr or r.stdout).strip()[-600:]))


def render(version, path, canvas, scale, out):
    # draw.io draws at scale 1 and the browser enlarges: draw.io 32 rounds label and edge positions in model
    # units, 31.5.3 in device pixels, so a view zoomed to the render scale differs between them for no reason
    # of the drawing (README, "Upgrading draw.io")
    env = dict(NODE, DRAWIO_VERSION=version, DRAWIO_RENDER_DEVICE='1')
    subprocess.run(['node', RENDER, path, out, str(canvas[0]), str(canvas[1]), str(scale)], check=True, capture_output=True, env=env)
    return out


def grey(path):
    return np.asarray(Image.open(path).convert('L'))


def pixels(a, b, out=None):
    """How many pixels differ between two images (a size difference counts as all); the diff image written."""
    A, B = grey(a), grey(b)
    if A.shape != B.shape:
        return 'size %s vs %s' % (A.shape[::-1], B.shape[::-1])
    d = A != B
    if not d.any():
        return 0
    if out:
        ia, ib = A < 128, B < 128
        o = np.full(A.shape + (3,), 255, np.uint8)
        o[ia | ib] = (185, 185, 185); o[ia & ~ib] = (220, 0, 0); o[ib & ~ia] = (0, 60, 230)
        Image.fromarray(o).save(out)
    return int(d.sum())


def svg_text(path):
    return re.sub(r'\(draw\.io \d+\.\d+\.\d+\)', '(draw.io X)', open(path, encoding='utf8').read())


def svg_diff(a, b):
    """How the two SVGs differ, in elements (the file split at '>'): None when they do not."""
    ta, tb = svg_text(a), svg_text(b)
    if ta == tb:
        return None
    ea, eb = ta.split('>'), tb.split('>')
    from difflib import SequenceMatcher
    n = sum(max(i2 - i1, j2 - j1) for op, i1, i2, j1, j2 in SequenceMatcher(None, ea, eb, autojunk=False).get_opcodes() if op != 'equal')
    return '%d of %d elements' % (n, len(ea))


def compare(pin, cand, figs, outdir):
    summary = json.load(open(os.path.join(BASELINE, 'summary.json')))
    files = [os.path.join(ROOT, 'diagrams', n, n + '.drawio') for n in figs]
    os.makedirs(outdir, exist_ok=True)
    with tempfile.TemporaryDirectory() as t:
        ex = {v: os.path.join(t, v) for v in (pin, cand)}
        print('exporting %d figures with draw.io %s and %s ...' % (len(figs), pin, cand), flush=True)
        with cf.ThreadPoolExecutor(2) as pool:
            for f in [pool.submit(run_export, v, ex[v], files, t) for v in ex]:
                f.result()

        def one(n):
            diffs = []
            a, b = (os.path.join(ex[v], 'images', n + '.svg') for v in (pin, cand))
            d = svg_diff(a, b)
            if d:
                diffs.append('svg: ' + d)
            for kind in ('art', 'htmlart'):
                a, b = (os.path.join(ex[v], kind, n + '.png') for v in (pin, cand))
                d = pixels(a, b, os.path.join(outdir, '%s-%s.png' % (n, kind)))
                if d:
                    diffs.append('%s: %s pixels differ' % (kind, d) if isinstance(d, int) else '%s: %s' % (kind, d))
            s = summary.get(n)
            if s:
                ra, rb = (render(v, os.path.join(ROOT, 'diagrams', n, n + '.drawio'), s['canvas'], s['scale'], os.path.join(t, '%s-%s.png' % (n, v))) for v in (pin, cand))
                d = pixels(ra, rb, os.path.join(outdir, n + '-render.png'))
                if d:
                    diffs.append('render: %s pixels differ' % d if isinstance(d, int) else 'render: %s' % d)
            else:
                diffs.append('render: not in the baseline, not compared')
            return n, diffs

        with cf.ThreadPoolExecutor(4) as pool:
            return list(pool.map(one, figs))


def main(a):
    check = '--check' in a
    out, to = None, None
    if '--out' in a:
        i = a.index('--out'); out = a[i + 1]; del a[i:i + 2]
    if '--to' in a:
        i = a.index('--to'); to = a[i + 1]; del a[i:i + 2]
    figs = [x for x in a if not x.startswith('--')]

    pin, tag, live, notes = where_is_draw_io()
    print('pin   %s   (tools/drawio-version.json)' % pin)
    print('tag   %s   (newest release that can be pinned)' % (tag or '?'))
    print('live  %s   (what app.diagrams.net serves: the editor people use)' % (live or '?'))
    for x in notes:
        print('note: ' + x)
    cand = to or (tag if tag and newer(tag, pin) else None)
    if live and newer(live, tag or pin):
        print('note: live is ahead of the newest tag: any comparison is of the tag, not of what people edit in')
    if check or not cand:
        if tag is None and not to:
            print('could not find out the newest tag'); return 2
        print('the pin is the newest tag' if not cand else 'a newer release can be pinned: %s' % cand)
        return 1 if (cand and check) else 0
    if not VER.match(cand) or cand == pin:
        print('nothing to compare: %s' % cand); return 2
    if not exists(RAW % ('v' + cand) + VIEWER):
        print('v%s has no viewer to fetch' % cand); return 2

    figs = figs or sorted(os.listdir(os.path.join(ROOT, 'diagrams')))
    out = out or tempfile.mkdtemp(prefix='drawio-upgrade-')
    try:
        res = compare(pin, cand, figs, out)
    except Exception as e:
        print('could not compare: %s' % e); return 2
    bad = [(n, d) for n, d in res if d]
    for n, d in bad:
        print('DIFFERENT %s' % n)
        for x in d:
            print('    ' + x)
    print('\n%d figures: %d same, %d different (draw.io %s -> %s)' % (len(res), len(res) - len(bad), len(bad), pin, cand))
    if bad:
        print('diff images (red: only %s has ink, blue: only %s): %s' % (pin, cand, out))
        print('VERDICT: REVIEW')
        return 1
    print('VERDICT: SAFE: no export and no render changes')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]) if sys.argv[1:] != ['-h'] else sys.exit(__doc__))
