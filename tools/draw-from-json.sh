#!/bin/bash
# Draw figures from their JSONs alone - no PNG, no reading, no corrections.
#
#   tools/draw-from-json.sh [--check] <diagrams-dir> [<figure> ...]
#
# For each figure in <diagrams-dir>/<figure>/ the JSONs are validated against
# their schemas, then <figure>-diagram.json and <figure>-layout.json are drawn
# as <figure>.svg and <figure>.drawio next to them. With no figures named, every
# folder in <diagrams-dir> is drawn.
#
# The JSONs are the source; the SVG and draw.io file are generated from them
# and are never edited by hand. With --check nothing is written: each figure is
# drawn to a scratch directory and compared with the SVG and draw.io file in its
# folder, and the script fails if any differs - the proof that what is
# committed is what the JSONs give.
set -e
here="$(cd "$(dirname "$0")" && pwd)"
check=
[ "$1" = "--check" ] && { check=1; shift; }
dir="$1"; shift
[ -d "$dir" ] || { echo "usage: $0 [--check] <diagrams-dir> [<figure> ...]" >&2; exit 2; }
[ $# -gt 0 ] || set -- $(cd "$dir" && ls -d */ | tr -d /)
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
bad=0
for n in "$@"; do
  src="$dir/$n/$n-diagram.json"
  python3 "$here/model_io.py" validate "$src" > "$tmp/$n-validate.log" \
      || { echo "$n: the JSONs do not validate"; cat "$tmp/$n-validate.log"; bad=1; continue; }
  python3 "$here/spec_from_model.py" "$src" "$tmp/$n-spec.json" 1480 > /dev/null
  python3 "$here/build_diagram.py" "$tmp/$n-spec.json" "$tmp/$n" > /dev/null
  if [ -n "$check" ]; then
    for s in .svg .drawio; do
      cmp -s "$tmp/$n$s" "$dir/$n/$n$s" || { echo "$n$s differs from what its JSONs give"; bad=1; }
    done
  else
    cp "$tmp/$n.svg" "$tmp/$n.drawio" "$dir/$n/"
  fi
done
[ -n "$check" ] && [ $bad = 0 ] && echo "all $# figures: SVG and draw.io are exactly what their JSONs give"
exit $bad
