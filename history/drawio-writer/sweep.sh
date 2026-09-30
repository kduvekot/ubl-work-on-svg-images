#!/bin/bash
# Draw every figure as a native draw.io model and hold each against its SVG.
#
#   history/drawio-writer/sweep.sh <out-dir> [<figure> ...]     (default: all of tools/uml78-bycomplexity.txt)
#
# For each figure, <out-dir>/<figure>/ gets what run.sh writes (the
# .drawio, both renders, the overlay, the comparison), and <out-dir>/sweep.md
# gets one row per figure: the ink each render lacks, and the kinds of element
# the writer does not draw yet. Nothing in diagrams/, tools/ or baselines/ is
# written. JOBS figures are done at a time (default 4).
set -e
here="$(cd "$(dirname "$0")" && pwd)"
root="$(cd "$here/.." && pwd)"
out="$1"; shift || true
[ -n "$out" ] || { echo "usage: $0 <out-dir> [<figure> ...]" >&2; exit 2; }
[ $# -gt 0 ] || set -- $(cat "$root/tools/uml78-bycomplexity.txt")
mkdir -p "$out"
one() {
  n="$1"; d="$out/$n"; mkdir -p "$d"
  # built at its natural scale, as run.sh; compared at 1480px wide
  python3 "$root/tools/spec_from_model.py" "$root/diagrams/$n/$n-diagram.json" "$d/$n-spec.json" 1480 > /dev/null
  nat=$(python3 -c "import json,statistics,sys; s=json.load(open(sys.argv[1])); z=[l['size'] for x in s['nodes'] if x['kind'] in ('action','object') for l in x.get('labelLines',[])]; print(round(1480*12/statistics.median(z),2) if z else 1480)" "$d/$n-spec.json")
  python3 "$root/tools/spec_from_model.py" "$root/diagrams/$n/$n-diagram.json" "$d/$n-natural-spec.json" "$nat" > /dev/null
  python3 "$here/drawio_from_spec.py" "$d/$n-natural-spec.json" "$d/$n.drawio" "$root/diagrams/$n/$n-diagram.json" > /dev/null 2> "$d/$n-missing.txt"
  read W H < <(python3 -c "import json,sys; c=json.load(open(sys.argv[1]))['canvas']; print(c['w'], c['h'])" "$d/$n-spec.json")
  read NW NH < <(python3 -c "import json,sys; c=json.load(open(sys.argv[1]))['canvas']; print(c['w'], c['h'])" "$d/$n-natural-spec.json")
  node "$root/tools/render-svg.js" "$root/diagrams/$n/$n.svg" "$d/$n-svg.png" "$W" > /dev/null
  # the drawing is rendered onto the SVG render's own canvas
  read PW PH < <(python3 -c "import sys; from PIL import Image; print(*Image.open(sys.argv[1]).size)" "$d/$n-svg.png")
  node "$here/render-drawio.js" "$d/$n.drawio" "$d/$n-drawio.png" "$PW" "$PH" "$(python3 -c "print($PW / $NW)")" > /dev/null
  python3 "$here/compare.py" "$d/$n-svg.png" "$d/$n-drawio.png" "$d/$n-spec.json" "$d/$n-overlay.png" > "$d/$n-compare.txt"
  echo "  $n"
}
export -f one; export out here root
printf '%s\n' "$@" | xargs -P "${JOBS:-4}" -I{} bash -c 'one {}'
python3 "$here/sweep_table.py" "$out" "$@" > "$out/sweep.md"
tail -n +1 "$out/sweep.md" | head -8
