#!/bin/bash
# One artwork, end to end:
#
#   original PNG -> graph -> model + layout + extraction report -> build spec
#                -> draw.io-editable SVG
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
  # the reading is reused when nothing it depends on has changed (graph_cache.py)
  if ! python3 "$here/graph_cache.py" get "$art/$n.png" "$out/$n-graph.json" "$out/$n-extract.log"; then
    python3 "$here/extract_graph.py"   "$art/$n.png" --json "$out/$n-graph.json" > "$out/$n-extract.log"
    python3 "$here/graph_cache.py"     put "$art/$n.png" "$out/$n-graph.json" "$out/$n-extract.log"
  fi
  # the graph split into what the diagram says, where it is drawn and how the
  # reading went; split refuses a graph that does not join back exactly
  python3 "$here/model_io.py"          split "$out/$n-graph.json" "$out"
  python3 "$here/model_io.py"          validate "$out/$n-diagram.json" > "$out/$n-validate.log" \
      || { cat "$out/$n-validate.log"; exit 1; }
  python3 "$here/spec_from_model.py"   "$out/$n-diagram.json" "$out/$n-spec.json" 1480
  python3 "$here/build_diagram.py"     "$out/$n-spec.json"  "$out/$n"
  # a sweep renders every SVG in one browser afterwards, and diffs them then
  [ -n "${RENDER_LATER:-}" ] && continue
  w=$(python3 -c "from PIL import Image;Image.MAX_IMAGE_PIXELS=None;print(Image.open('$art/$n.png').width)")
  node "$here/render-svg.js" "$out/$n.svg" "$out/$n-render.png" "$w" 600
  # radius 2 counts every displaced pixel, which is the point. The radius-40 pass
  # this used to run alongside it is gone: at that width a node box displaced 20px
  # scores exactly as one in the right place, so it measured nothing (see
  # docs/artwork-conversion-notes.md). verify_conversion.py is what separates a
  # genuinely absent element from a displaced one, and it does it by looking for
  # ink nearby rather than by blurring the whole page.
  java -cp "$here" VisualDiff "$art/$n.png" "$out/$n-render.png" "$out/$n-diff-r2.png"     2 2>/dev/null | grep -Ev '^Picked up'
done
