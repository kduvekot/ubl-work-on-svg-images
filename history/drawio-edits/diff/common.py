"""What the diff scripts share: where things are, each figure's natural width,
and the figures in the order of the UBL 2.5 specification, with its titles.

UBL is a clone of the UBL repository (https://github.com/oasis-tcs/ubl, branch
ubl-2.5), for its art/ (the PNGs) and UBL.xml (the specification); set it with
the environment variable UBL (default: ubl, beside this repository)."""
import functools, json, os, re, subprocess, tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
UBL = os.environ.get('UBL') or os.path.join(os.path.dirname(ROOT), 'ubl')
ART = os.path.join(UBL, 'art')
# playwright drives the renders; a global install is not on node's own path
_g = subprocess.run(['npm', 'root', '-g'], capture_output=True, text=True).stdout.strip()
NODE = dict(os.environ, NODE_PATH=os.pathsep.join(p for p in (os.environ.get('NODE_PATH'), _g) if p))
RENDER = os.path.join(ROOT, 'history', 'drawio-writer', 'render-drawio.js')
BEFORE_SPACE = 'f438cc7'     # the drawings before space was inserted for short arrows


@functools.lru_cache(None)
def natural_width(n):
    """the canvas width the drawing was built at (history/drawio-writer/run.sh):
    the scale at which the median action or document label is 12 px"""
    tools, src = os.path.join(ROOT, 'history', 'tools'), os.path.join(ROOT, 'history', 'diagrams', n, n + '-diagram.json')
    with tempfile.TemporaryDirectory() as t:
        def spec(w):
            subprocess.run(['python3', os.path.join(tools, 'spec_from_model.py'), src, t + '/s.json', str(w)], check=True, capture_output=True)
            return json.load(open(t + '/s.json'))
        z = sorted(l['size'] for x in spec(1480)['nodes'] if x['kind'] in ('action', 'object') for l in x.get('labelLines', []))
        import statistics
        return spec(round(1480 * 12 / statistics.median(z), 2) if z else 1480)['canvas']['w']


def figures():
    """[(figure, title)] of the 78, in the specification's order"""
    t = open(os.path.join(UBL, 'UBL.xml'), encoding='utf-8').read()
    ours = set(os.listdir(os.path.join(ROOT, 'diagrams')))
    out = {}
    for m in re.finditer(r'<figure\b.*?</figure>', t, re.S):
        ti, f = re.search(r'<title>(.*?)</title>', m.group(0), re.S), re.search(r'fileref="([^"]*)"', m.group(0))
        if ti and f:
            n = re.sub(r'^.*/|\.(png|jpg|svg)$', '', f.group(1))
            if n in ours and n not in out:
                out[n] = ' '.join(ti.group(1).split())
    return list(out.items())
