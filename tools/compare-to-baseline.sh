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
#   - the SVG, the .drawio and the spec are compared byte for byte, and where the
#     SVG differs, compared again with the ids put back: the elements of the two
#     SVGs are paired in document order, the pairing must be a consistent one-to-
#     one renaming, and with the baseline's ids written back into the new SVG and
#     .drawio they must then be byte-identical. That is what "the same drawing,
#     with its elements renamed" means, and nothing looser passes for it.
#
# Writes, into <out-dir>, <name>-base.png, <name>-new.png, <name>-basediff.png and
# <name>-compare.json per diagram, and summary.json over them all. Prints one line
# per diagram and a tally - "same" for a byte-identical file, "ids" for one that is
# identical once renamed back, "DIFF" for anything else - and exits non-zero unless
# every diagram is identical: not a pixel different, and its SVG the baseline's,
# byte for byte or once renamed back.
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
def renamed():
    """(svg, drawio) identical once the new SVG's ids are mapped back, or None
    where there is nothing to map"""
    p, q = os.path.join(base, n + ".svg"), os.path.join(new, n + ".svg")
    old_svg, new_svg = open(p, encoding="utf-8").read(), open(q, encoding="utf-8").read()
    ids = lambda t: re.findall(r'<g id="([^"]+)"', t)
    a_ids, b_ids = ids(old_svg), ids(new_svg)
    if len(a_ids) != len(b_ids):
        return False, False
    back = {}
    for o, nw in zip(a_ids, b_ids):
        if back.setdefault(nw, o) != o:
            return False, False
    if len(set(back.values())) != len(back):
        return False, False
    back = {k: v for k, v in back.items() if k != v}
    if not back:
        return None, None
    pat = re.compile(r"(?<![A-Za-z0-9_-])(%s)(?![A-Za-z0-9_-])"
                     % "|".join(re.escape(k) for k in sorted(back, key=len, reverse=True)))
    put_back = lambda t: pat.sub(lambda m: back[m.group(1)], t)
    svg_ok = put_back(new_svg) == old_svg
    pd, qd = os.path.join(base, n + ".drawio"), os.path.join(new, n + ".drawio")
    drawio_ok = (put_back(open(qd, encoding="utf-8").read()) == open(pd, encoding="utf-8").read()
                 if os.path.exists(pd) and os.path.exists(qd) else None)
    return svg_ok, drawio_ok

r = dict(name=n, size=list(a.size),
         pixelsDiffer=differ,
         onlyInBaseline=grab(r"MISSING \(red\)\s+(\d+)"),
         onlyInNew=grab(r"EXTRA\s+\(blue\)\s+(\d+)"),
         svgIdentical=same(".svg"), drawioIdentical=same(".drawio"),
         specIdentical=same("-spec.json"))
if r["svgIdentical"] is False:
    r["svgIdenticalUpToIds"], r["drawioIdenticalUpToIds"] = renamed()

def spec_renamed():
    """The spec carries the model's ids where the baseline's had none. Equal once
    those ids are taken out and the node ids mapped back through the new run's
    formerIds, or None where there is no such map."""
    rep = os.path.join(new, n + "-extraction.json")
    ps, qs = os.path.join(base, n + "-spec.json"), os.path.join(new, n + "-spec.json")
    if not (os.path.exists(rep) and os.path.exists(ps) and os.path.exists(qs)):
        return None
    back = json.load(open(rep)).get("formerIds")
    if not back:
        return None
    def strip(o):
        if isinstance(o, dict):   # a node keeps its id (it has a kind); nothing else had one
            return {k: strip(v) for k, v in o.items() if k != "id" or "kind" in o}
        if isinstance(o, list):
            return [strip(x) for x in o]
        return back.get(o, o) if isinstance(o, str) else o
    return strip(json.load(open(qs))) == json.load(open(ps))
if r["specIdentical"] is False:
    r["specIdenticalUpToIds"] = spec_renamed()
# identical: not one pixel differs, and the SVG is the baseline's, byte for byte
# or once its elements are renamed back
r["verdict"] = ("identical" if differ == 0 and (r["svgIdentical"] is not False
                                               or r.get("svgIdenticalUpToIds"))
                else "differs")
json.dump(r, open(os.path.join(out, n + "-compare.json"), "w"), indent=1)
yn = lambda v: "-" if v is None else ("same" if v else "DIFF")
# "ids" where a file differs only by the renaming checked above
ya = lambda v, up: "ids" if (v is False and up) else yn(v)
line = "%-52s %-10s %9d %8d %8d   %-4s %-4s %-4s" % (
    n, r["verdict"], differ, r["onlyInBaseline"], r["onlyInNew"],
    ya(r["svgIdentical"], r.get("svgIdenticalUpToIds")),
    ya(r["drawioIdentical"], r.get("drawioIdenticalUpToIds")),
    ya(r["specIdentical"], r.get("specIdenticalUpToIds")))
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
