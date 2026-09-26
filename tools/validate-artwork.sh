#!/usr/bin/env bash
# Validate candidate SVG artwork against the original PNGs in art/.
#
#   ./validate-artwork.sh <art-dir> <svg-dir> <out-dir> [radius]
#
# For every <name>.svg in <svg-dir> that has a matching art/<name>.png, the SVG is
# rendered at the PNG's exact pixel width and diffed against it. A blank (all-white)
# diff means the candidate reproduces the original. Red = ink the candidate lost,
# blue = ink it invented.
#
# Exits non-zero if any diagram differs, so it can gate a build.
set -uo pipefail

ART=${1:?art directory}          # e.g. oasis-tcs/ubl/art
SVG=${2:?svg directory}          # e.g. ubl-work-on-svg-images/svg-images
OUT=${3:?output directory}
RADIUS=${4:-2}

HERE=$(cd "$(dirname "$0")" && pwd)
# playwright drives the headless render, and a global install is not on node's
# default search path. run-pipeline.sh sets this; this script did not, so every
# render failed with "Cannot find module 'playwright'" and the table said only
# RENDER FAILED.
export NODE_PATH="${NODE_PATH:+$NODE_PATH:}$(npm root -g 2>/dev/null)"
mkdir -p "$OUT"
[ "$HERE/VisualDiff.class" -nt "$HERE/VisualDiff.java" ] || javac -d "$HERE" "$HERE/VisualDiff.java"

pass=0; fail=0; skip=0
printf '%-52s %10s %10s  %s\n' FIGURE MISSING EXTRA RESULT
printf '%s\n' "----------------------------------------------------------------------------------------"

for svgfile in "$SVG"/*.svg; do
  name=$(basename "$svgfile" .svg)
  png="$ART/$name.png"
  if [ ! -f "$png" ]; then skip=$((skip+1)); continue; fi

  width=$(python3 -c "import struct,sys;d=open(sys.argv[1],'rb').read(24);print(struct.unpack('>I',d[16:20])[0])" "$png")
  node "$HERE/render-svg.js" "$svgfile" "$OUT/$name.render.png" "$width" \
      >/dev/null 2>"$OUT/$name.render.err" || {
    sed 's/^/      /' "$OUT/$name.render.err" >&2
    printf '%-52s %10s %10s  %s\n' "$name" - - "RENDER FAILED"; fail=$((fail+1)); continue; }

  report=$(java -cp "$HERE" VisualDiff "$png" "$OUT/$name.render.png" "$OUT/$name.diff.png" "$RADIUS" 2>&1)
  rc=$?
  miss=$(sed -n 's/.*MISSING (red) *\([0-9]*\).*/\1/p' <<<"$report")
  extr=$(sed -n 's/.*EXTRA   (blue) *\([0-9]*\).*/\1/p' <<<"$report")
  if [ $rc -eq 0 ]; then
    printf '%-52s %10s %10s  %s\n' "$name" "${miss:-0}" "${extr:-0}" "CLEAN"; pass=$((pass+1))
    rm -f "$OUT/$name.diff.png"
  else
    printf '%-52s %10s %10s  %s\n' "$name" "${miss:-?}" "${extr:-?}" "DIFF -> $name.diff.png"; fail=$((fail+1))
  fi
done

printf '%s\n' "----------------------------------------------------------------------------------------"
printf 'clean %d   differing %d   no original %d\n' "$pass" "$fail" "$skip"
[ "$fail" -eq 0 ]
