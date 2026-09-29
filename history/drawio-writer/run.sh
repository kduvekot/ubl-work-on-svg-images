#!/bin/bash
# Draw a figure as a native draw.io model and hold it against its SVG.
#
#   history/drawio-writer/run.sh [<figure> ...]      (default: UBL-2.5-BillingwithDebitNoteProcess)
#
# Reads diagrams/<figure>/ (the JSONs and the committed SVG) and writes only to
# history/drawio-writer/<figure>/: the .drawio, both renders, the overlay and the
# comparison. Nothing in diagrams/, tools/ or baselines/ is written.
# Needs Python 3 with jsonschema, numpy, scipy and pillow, and Node with
# playwright (as tools/render-svg.js); the draw.io viewer is fetched once.
set -e
here="$(cd "$(dirname "$0")" && pwd)"
root="$(cd "$here/.." && pwd)"
[ $# -gt 0 ] || set -- UBL-2.5-BillingwithDebitNoteProcess
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
NATURAL() { python3 -c "import json,statistics,sys; s=json.load(open(sys.argv[1])); z=[l['size'] for x in s['nodes'] if x['kind'] in ('action','object') for l in x.get('labelLines',[])]; print(round(1480*12/statistics.median(z),2) if z else 1480)" "$1"; }
for n in "$@"; do
  src="$root/diagrams/$n"
  out="$here/$n"; mkdir -p "$out"
  # the drawing is built at its natural scale: the size at which its actions'
  # and documents' labels (their median) are 12px, draw.io's own font size -
  # the scale the artwork was drawn at before it was scaled up. The SVG and
  # the comparison stay at 1480px wide; the drawing is rendered at that width.
  python3 "$root/tools/spec_from_model.py" "$src/$n-diagram.json" "$tmp/$n-spec.json" 1480 > /dev/null
  NAT=$(NATURAL "$tmp/$n-spec.json")
  python3 "$root/tools/spec_from_model.py" "$src/$n-diagram.json" "$tmp/$n-natural-spec.json" "$NAT" > /dev/null
  python3 "$here/drawio_from_spec.py" "$tmp/$n-natural-spec.json" "$out/$n.drawio" "$src/$n-diagram.json"
  read W H < <(python3 -c "import json,sys; c=json.load(open(sys.argv[1]))['canvas']; print(c['w'], c['h'])" "$tmp/$n-spec.json")
  read NW NH < <(python3 -c "import json,sys; c=json.load(open(sys.argv[1]))['canvas']; print(c['w'], c['h'])" "$tmp/$n-natural-spec.json")
  node "$root/tools/render-svg.js" "$src/$n.svg" "$out/$n-svg.png" "$W" > /dev/null
  # the drawing is rendered onto the SVG render's own canvas
  read PW PH < <(python3 -c "import sys; from PIL import Image; print(*Image.open(sys.argv[1]).size)" "$out/$n-svg.png")
  node "$here/render-drawio.js" "$out/$n.drawio" "$out/$n-drawio.png" "$PW" "$PH" "$(python3 -c "print($PW / $NW)")"
  python3 "$here/compare.py" "$out/$n-svg.png" "$out/$n-drawio.png" "$tmp/$n-spec.json" \
      "$out/$n-overlay.png" | tee "$out/$n-compare.txt"
done
