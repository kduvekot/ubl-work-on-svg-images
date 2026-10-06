"""Put the parts (illustrations/parts/*.svg) into the illustrations that use them.

    python3 tools/embed_parts.py [<figure>.drawio ...]      default: every drawing in diagrams/

An illustration (the Fulfilment and the CPFR step figures) is made of pictures: each an SVG part,
embedded in the drawing as an image, the element's `ubl-part` (draw.io's Edit
Data) naming the part. The parts are kept as files, to be edited with an SVG
editor (Inkscape, say); after an edit, this puts the part as it now is into
every drawing that uses it, where it was, at the same size. A drawing whose
parts are already the files' is left as it is, byte for byte.

Prints, per drawing that uses parts, how many pictures it has and how many it
changed. Exits 1 when a drawing names a part that is not there.
"""
import base64, glob, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARTS = os.path.join(ROOT, 'illustrations', 'parts')
# a picture: <object ... ubl-part="X" ...><mxCell style="...image=data:image/svg+xml,BASE64;..."
PICTURE = re.compile(r'(<object\b[^>]*\bubl-part="([^"]+)"[^>]*>\s*<mxCell\b[^>]*\bstyle="[^"]*?image=data:image/svg\+xml,)([A-Za-z0-9+/=]+)')


def main(argv):
    files = argv or sorted(glob.glob(os.path.join(ROOT, 'diagrams', '*', '*.drawio')))
    bad = 0
    for path in files:
        text = open(path, encoding='utf-8').read()
        seen, changed, missing = 0, 0, []

        def put(m):
            nonlocal seen, changed
            seen += 1
            f = os.path.join(PARTS, m.group(2) + '.svg')
            if not os.path.exists(f):
                missing.append(m.group(2))
                return m.group(0)
            now = base64.b64encode(open(f, 'rb').read()).decode()
            if now != m.group(3):
                changed += 1
            return m.group(1) + now
        new = PICTURE.sub(put, text)
        if not seen:
            continue
        if new != text:
            open(path, 'w', encoding='utf-8').write(new)
        name = os.path.basename(path)[:-len('.drawio')]
        print('%-55s %d pictures, %d changed%s' % (name, seen, changed,
                                                   '; no part ' + ', '.join(sorted(set(missing))) if missing else ''))
        bad += bool(missing)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
