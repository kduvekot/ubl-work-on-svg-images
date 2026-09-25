#!/usr/bin/env bash
# Hold a new run's SVGs against a saved baseline's, diagram by diagram.
#
#   tools/compare-to-baseline.sh <baseline-dir> <new-dir> <out-dir> [names-file]
#
# <baseline-dir> is a baseline's diagrams/ directory (baselines/<date>/diagrams),
# <new-dir> a directory the pipeline has just written. For each basename, both
# SVGs are rendered here, now, with the same renderer and at the original PNG's
# own pixel width (read off the baseline's -render.png, which was made at that
# width), so a difference in the environment cannot pass for a difference in the
# drawing. Then:
#
#   - the two renders are differenced at radius 0 with no alignment: red is ink
#     only the baseline has, blue is ink only the new SVG has, and the ink both
#     share is drawn faintly grey so a blank panel still shows which drawing it is
#   - every pixel is compared exactly as well, because the red/blue picture is
#     drawn from ink thresholded at mid-grey and a change of shade below that
#     would not show in it
#   - the SVG, the .drawio and the spec are compared byte for byte
#
# Writes, into <out-dir>, <name>-base.png, <name>-new.png, <name>-basediff.png and
# <name>-compare.json per diagram, and summary.json over them all. Prints one line
# per diagram and a tally, and exits non-zero if any render differs by a pixel.
#
# JOBS diagrams run at a time (default: one per core).
set -uo pipefail

HERE=$(cd "$(dirname "$0")" && pwd)

# ---- one diagram ------------------------------------------------------------
if [ "${1:-}" = "--one" ]; then
  BASE=$2; NEW=$3; OUT=$4; n=$5
  w=$(python3 -c "import sys;from PIL import Image;Image.MAX_IMAGE_PIXELS=None;print(Image.open(sys.argv[1]).width)" \
      "$BASE/$n-render.png" 2>/dev/null) || { printf '%-52s %s\n' "$n" "NO BASELINE RENDER" | tee "$OUT/$n-compare.line"; exit 0; }
  [ -f "$NEW/$n.svg" ] || { printf '%-52s %s\n' "$n" "NO NEW SVG" | tee "$OUT/$n-compare.line"; exit 0; }
  node "$HERE/render-svg.js" "$BASE/$n.svg" "$OUT/$n-base.png" "$w" 600 > /dev/null 2> "$OUT/$n-compare.err" &&
  node "$HERE/render-svg.js" "$NEW/$n.svg"  "$OUT/$n-new.png"  "$w" 600 > /dev/null 2>> "$OUT/$n-compare.err" ||
    { printf '%-52s %s\n' "$n" "RENDER FAILED" | tee "$OUT/$n-compare.line"; exit 0; }
  java -cp "$HERE" VisualDiff "$OUT/$n-base.png" "$OUT/$n-new.png" "$OUT/$n-basediff.png" \
      0 --no-align --ghost > "$OUT/$n-visualdiff.log" 2>&1
  python3 - "$BASE" "$NEW" "$OUT" "$n" <<'PY'
import filecmp, json, os, re, sys
from PIL import Image, ImageChops
Image.MAX_IMAGE_PIXELS = None
base, new, out, n = sys.argv[1:]
a = Image.open(os.path.join(out, n + "-base.png")).convert("RGB")
b = Image.open(os.path.join(out, n + "-new.png")).convert("RGB")
if a.size != b.size:
    differ = a.width * a.height
else:
    d = ImageChops.difference(a, b).convert("L").point(lambda v: 255 if v else 0)
    differ = d.histogram()[255]
log = open(os.path.join(out, n + "-visualdiff.log")).read()
grab = lambda pat: int((re.search(pat, log) or [0, 0])[1])
def same(suffix):
    p, q = os.path.join(base, n + suffix), os.path.join(new, n + suffix)
    if not (os.path.exists(p) and os.path.exists(q)):
        return None
    return filecmp.cmp(p, q, shallow=False)
r = dict(name=n, size=list(a.size),
         pixelsDiffer=differ,
         onlyInBaseline=grab(r"MISSING \(red\)\s+(\d+)"),
         onlyInNew=grab(r"EXTRA\s+\(blue\)\s+(\d+)"),
         svgIdentical=same(".svg"), drawioIdentical=same(".drawio"),
         specIdentical=same("-spec.json"))
r["verdict"] = "identical" if differ == 0 else "differs"
json.dump(r, open(os.path.join(out, n + "-compare.json"), "w"), indent=1)
yn = lambda v: "-" if v is None else ("same" if v else "DIFF")
line = "%-52s %-10s %9d %8d %8d   %-4s %-4s %-4s" % (
    n, r["verdict"], differ, r["onlyInBaseline"], r["onlyInNew"],
    yn(r["svgIdentical"]), yn(r["drawioIdentical"]), yn(r["specIdentical"]))
open(os.path.join(out, n + "-compare.line"), "w").write(line + "\n")
print(line)
PY
  exit 0
fi

# ---- the set ------------------------------------------------------------------
BASE=$(cd "${1:?baseline diagrams directory}" && pwd)
NEW=$(cd "${2:?new run directory}" && pwd)
OUT=${3:?output directory}
LIST=${4:-$HERE/uml78-bycomplexity.txt}
JOBS=${JOBS:-$(nproc 2>/dev/null || echo 4)}
export NODE_PATH="${NODE_PATH:+$NODE_PATH:}$(npm root -g 2>/dev/null)"
mkdir -p "$OUT"; OUT=$(cd "$OUT" && pwd)
[ -f "$HERE/VisualDiff.class" ] || javac -d "$HERE" "$HERE/VisualDiff.java"

names=()
while read -r n; do [ -n "$n" ] && names+=("$n"); done < "$LIST"
for n in "${names[@]}"; do rm -f "$OUT/$n-compare.line" "$OUT/$n-compare.json"; done

head='%-52s %-10s %9s %8s %8s   %-4s %-4s %-4s\n'
printf "$head" FIGURE RESULT PX-DIFFER BASE-ONLY NEW-ONLY SVG DRAW SPEC
printf "$head" "" "" "" "(red)" "(blue)" "" "IO" ""
printf '%s\n' "------------------------------------------------------------------------------------------------------"
printf '%s\0' "${names[@]}" | xargs -0 -P "$JOBS" -I{} "$0" --one "$BASE" "$NEW" "$OUT" {} > /dev/null

identical=0; differs=0; broken=0
for n in "${names[@]}"; do
  cat "$OUT/$n-compare.line" 2>/dev/null || printf '%-52s %s\n' "$n" "NO RESULT"
  case $(awk '{print $2}' "$OUT/$n-compare.line" 2>/dev/null) in
    identical) identical=$((identical+1));;
    differs)   differs=$((differs+1));;
    *)         broken=$((broken+1));;
  esac
done
printf '%s\n' "------------------------------------------------------------------------------------------------------"
printf 'identical %d   differs %d   not compared %d\n' "$identical" "$differs" "$broken"

python3 - "$BASE" "$NEW" "$OUT" "${names[@]}" <<'PY'
import json, os, sys
base, new, out, names = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:]
figs = []
for n in names:
    p = os.path.join(out, n + "-compare.json")
    figs.append(json.load(open(p)) if os.path.exists(p) else dict(name=n, verdict="not compared"))
json.dump(dict(baseline=base, new=new, figures=figs,
               identical=sum(f["verdict"] == "identical" for f in figs),
               differs=sum(f["verdict"] == "differs" for f in figs),
               notCompared=sum(f["verdict"] not in ("identical", "differs") for f in figs)),
          open(os.path.join(out, "summary.json"), "w"), indent=1)
PY
[ "$differs" -eq 0 ] && [ "$broken" -eq 0 ]
