#!/bin/bash
# Draw a figure as a native draw.io model and hold it against its SVG.
#
#   poc-drawio/run-poc.sh [<figure> ...]      (default: UBL-2.5-BillingwithDebitNoteProcess)
#
# Reads diagrams/<figure>/ (the JSONs and the committed SVG) and writes only to
# poc-drawio/<figure>/: the .drawio, both renders, the overlay and the
# comparison. Nothing in diagrams/, tools/ or baselines/ is written.
# Needs Python 3 with jsonschema, numpy, scipy and pillow, and Node with
# playwright (as tools/render-svg.js); the draw.io viewer is fetched once.
set -e
here="$(cd "$(dirname "$0")" && pwd)"
root="$(cd "$here/.." && pwd)"
[ $# -gt 0 ] || set -- UBL-2.5-BillingwithDebitNoteProcess
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
for n in "$@"; do
  src="$root/diagrams/$n"
  out="$here/$n"; mkdir -p "$out"
  python3 "$root/tools/spec_from_model.py" "$src/$n-diagram.json" "$tmp/$n-spec.json" 1480 > /dev/null
  python3 "$here/drawio_from_spec.py" "$tmp/$n-spec.json" "$out/$n.drawio"
  read W H < <(python3 -c "import json,sys; c=json.load(open(sys.argv[1]))['canvas']; print(c['w'], c['h'])" "$tmp/$n-spec.json")
  node "$root/tools/render-svg.js" "$src/$n.svg" "$out/$n-svg.png" "$W" > /dev/null
  node "$here/render-drawio.js" "$out/$n.drawio" "$out/$n-drawio.png" "$W" "$H"
  python3 "$here/compare.py" "$out/$n-svg.png" "$out/$n-drawio.png" "$tmp/$n-spec.json" \
      "$out/$n-overlay.png" | tee "$out/$n-compare.txt"
done
