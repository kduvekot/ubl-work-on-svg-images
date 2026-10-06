"""Where space was inserted for short arrows: replays insert_space.py on the
drawings as they were before it (commit f438cc7) and records every insertion
(axis, cut, extra) and the shapes it ran through that kept their size (their
extent across and along, and whether they moved whole past the cut).

    python3 insertions.py <out dir>          writes <out>/insertions.json
"""
import collections, json, os, subprocess, sys, tempfile
from common import BEFORE_SPACE, ROOT, drawn_later, illustration
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import insert_space as m

out = sys.argv[1]; os.makedirs(out, exist_ok=True)
rec = collections.defaultdict(list)
SKIP = m.FIXED + ('band-divider', 'band-title', 'lane-divider', None)
plain = m.Figure.insert


def insert(self, axis, cut, extra):
    b0 = self.boxes(); plain(self, axis, cut, extra); b1 = self.boxes()
    kept = []
    for i, b in b0.items():
        if self.kind(i) in SKIP or not b[axis] < cut < b[axis + 2]:
            continue
        a = b1[i]
        if round(a[axis + 2] - a[axis]) == round(b[axis + 2] - b[axis]):
            kept.append([b[1 - axis], b[3 - axis], b[axis], b[axis + 2], int(a[axis] != b[axis]), i])
    rec[os.path.basename(self.path)[:-7]].append([axis, cut, extra, kept])


m.Figure.insert = insert
with tempfile.TemporaryDirectory() as t:
    for n in sorted(os.listdir(os.path.join(ROOT, 'diagrams'))):
        if illustration(n) or drawn_later(n):      # made after, no space inserted
            continue
        os.makedirs(f'{t}/{n}')
        open(f'{t}/{n}/{n}.drawio', 'w').write(subprocess.run(['git', '-C', ROOT, 'show', f'{BEFORE_SPACE}:diagrams/{n}/{n}.drawio'], capture_output=True, text=True, check=True).stdout)
        m.fix(f'{t}/{n}/{n}.drawio', [])
json.dump(dict(rec), open(os.path.join(out, 'insertions.json'), 'w'))
print('%d insertions in %d figures' % (sum(map(len, rec.values())), len(rec)))
