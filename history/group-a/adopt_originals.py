"""Group A: the TC's own sources, adopted as they are (README: history/group-a/README.md).

The UBL repository has, for four of its figures, the source of the PNG it publishes (checked
2026-10-05: a render of each matches its PNG to 0.07 % of the ink or better). Three of them, its
draw.io files, are the figures' sources here too, at the place and under the name of the others:
diagrams/<figure>/<figure>.drawio. The fourth, Ordering's SVG, is not adopted any more (below).

  UBL-2.3-Pre-awardProcess, UBL-2.3-ProcurementProcess, UBL-2.4-BusinessInformation (.drawio)
      the file as the TC made it (sources/, byte for byte as the UBL repository has it), with
      only what this repository's tools need and nothing of what it shows changed:
        - uncompressed, and in the form draw.io's editor writes (tools/drawio_format.py);
          `host` and `agent` of <mxfile>, the page and the window size are the file's own;
        - one element carries `ubl-notation` (bpmn, phase-map): the sign that this figure is not a
          UML activity diagram, which tools/check_drawio.py and the export look for; Business
          Information's also `ubl-art="grey"`: its print PNG is 8 bit grey, not 1 bit (the grey
          footer of its tasks, which the UBL repository's PNG has);
        - Procurement only: a stray dashed line, 4000 px right of the figure and not in its PNG,
          is taken out: it made the export's page three times too wide.
  UBL-2.3-OrderingProcess (.svg)
      the bpmn-js SVG (bpmn.io, 2019) was adopted so too, byte for byte, until 2026-10-06; since then
      the figure's source is a draw.io BPMN diagram made from that SVG (history/group-a/build_ordering.py),
      and this script leaves it alone. The SVG stays in sources/.
"""
import base64, os, re, sys, urllib.parse, zlib
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import drawio_format  # noqa: E402

FIGURES = {   # figure: notation, a cell to take out, more properties for the marker
    'UBL-2.3-Pre-awardProcess': ('phase-map', None, {}),
    'UBL-2.3-ProcurementProcess': ('phase-map', 'H2ljDLKrGr7yGGcZbY4q-120', {}),
    # its tasks have a grey (#C0C0C0) footer, which the UBL repository's PNG shows: the print PNG is greyscale too
    'UBL-2.4-BusinessInformation': ('bpmn', None, {'ubl-art': 'grey'}),
}


def adopt(name, notation, drop, more):
    src = open(os.path.join(HERE, 'sources', name + '.drawio'), encoding='utf-8').read()
    top = ET.fromstring(src)
    diagram = top.find('diagram')
    if len(diagram) == 0:        # compressed: base64 of raw-deflated, percent-encoded XML
        model = ET.fromstring(urllib.parse.unquote(zlib.decompress(base64.b64decode(diagram.text), -15).decode()))
        diagram.text = None
        diagram.append(model)
    root = diagram.find('mxGraphModel/root')
    if drop:
        cell = [c for c in root if c.get('id') == drop]
        assert len(cell) == 1, drop
        root.remove(cell[0])
    first = next(el for el in root if el.get('id') not in ('0', '1') and el.tag in ('mxCell', 'object', 'UserObject'))
    if first.tag == 'mxCell':     # an object holds its label (value) and id; the cell keeps the rest
        obj = ET.Element('object', {'label': first.attrib.pop('value', ''), 'ubl-notation': notation, **more, 'id': first.attrib.pop('id')})
        obj.append(first)
        root.insert(list(root).index(first), obj)
        root.remove(first)
    else:
        first.set('ubl-notation', notation)
        for k, v in more.items():
            first.set(k, v)
    d = os.path.join(ROOT, 'diagrams', name)
    os.makedirs(d, exist_ok=True)
    out = os.path.join(d, name + '.drawio')
    open(out, 'w', encoding='utf-8').write(drawio_format.format_text(ET.tostring(top, encoding='unicode')))
    return out


for name, (notation, drop, more) in FIGURES.items():
    print(adopt(name, notation, drop, more))
