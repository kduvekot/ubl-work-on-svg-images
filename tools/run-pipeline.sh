#!/bin/bash
# One artwork, end to end:
#
#   original PNG -> semantic graph -> build spec -> draw.io-editable SVG
#                -> PNG rendered at the original's own pixel size -> pixel diff
#
#   tools/run-pipeline.sh <art-dir> <out-dir> <basename> [<basename> ...]
#
# The PNG in <art-dir> is the source of truth throughout; the diff at the end is
# the acceptance test. A blank (all-white) diff means the SVG reproduces the PNG.
# Red = present in the original and missing from the SVG, blue = invented.
set -e
here="$(cd "$(dirname "$0")" && pwd)"
art="$1"; out="$2"; shift 2
mkdir -p "$out"
[ -f "$here/VisualDiff.class" ] || javac -d "$here" "$here/VisualDiff.java"
# playwright drives the headless render; a global install is fine
export NODE_PATH="${NODE_PATH:+$NODE_PATH:}$(npm root -g 2>/dev/null)"

for n in "$@"; do
  echo "== $n"
  python3 "$here/extract_graph.py"     "$art/$n.png" --json "$out/$n-graph.json" > "$out/$n-extract.log"
  python3 "$here/spec_from_extract.py" "$out/$n-graph.json" "$out/$n-spec.json" 1480
  python3 "$here/build_diagram.py"     "$out/$n-spec.json"  "$out/$n"
  w=$(python3 -c "from PIL import Image;Image.MAX_IMAGE_PIXELS=None;print(Image.open('$art/$n.png').width)")
  node "$here/render-svg.js" "$out/$n.svg" "$out/$n-render.png" "$w" 600
  # radius 2 counts every displaced pixel; radius 40 ignores glyph shape and
  # sub-pixel placement, so what stays red there is genuinely absent line-work
  java -cp "$here" VisualDiff "$art/$n.png" "$out/$n-render.png" "$out/$n-diff-r2.png"     2 2>/dev/null | grep -Ev '^Picked up'
  java -cp "$here" VisualDiff "$art/$n.png" "$out/$n-render.png" "$out/$n-diff-r40.png"   40 2>/dev/null | grep -Ev '^Picked up'
done
