#!/usr/bin/env bash
# Convert and judge a whole set of diagrams, hardest first.
#
#   tools/verdict-sweep.sh <art-dir> <out-dir> <names-file> [radius]
#
# For each basename in <names-file>: run the pipeline, then verify the result.
# Prints one line per diagram and a tally, and leaves a -verify.json beside each
# conversion. Ordering is the caller's: feed it a list sorted by complexity so
# the hard cases are met first, while there is still room to change the approach.
#
# A diagram is CORRECT only when the line-work diff is blank at the honest radius
# and every label reads back correctly. Never widen the radius to get there.
set -uo pipefail
ART=${1:?art directory}
OUT=${2:?output directory}
LIST=${3:?file of basenames, one per line}
RADIUS=${4:-3}

HERE=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$OUT"
[ -f "$HERE/VisualDiff.class" ] || javac -d "$HERE" "$HERE/VisualDiff.java"

correct=0; improvable=0; human=0; failed=0
printf '%-52s %-12s %9s %9s %7s %6s\n' FIGURE VERDICT MISSING INVENTED FINDINGS PERSON
printf '%s\n' "--------------------------------------------------------------------------------------------------"

while read -r n; do
  [ -z "$n" ] && continue
  if ! "$HERE/run-pipeline.sh" "$ART" "$OUT" "$n" > "$OUT/$n-pipeline.log" 2>&1; then
    printf '%-52s %-12s\n' "$n" "PIPELINE-FAIL"; failed=$((failed+1)); continue
  fi
  rep="$OUT/$n-verify.json"
  if ! python3 "$HERE/verify_conversion.py" "$ART/$n.png" "$OUT/$n-render.png" \
        "$OUT/$n-graph.json" --radius "$RADIUS" --json "$rep" \
        > "$OUT/$n-verify.log" 2>&1; then
    printf '%-52s %-12s\n' "$n" "VERIFY-FAIL"; failed=$((failed+1)); continue
  fi
  read -r v m i f p < <(python3 - "$rep" <<'PY'
import json,sys
r=json.load(open(sys.argv[1]))
lw=max(1,r.get("lineWorkInk",1))
print(r["verdict"], "%.3f"%(100.0*r["missingPx"]/lw), "%.3f"%(100.0*r["inventedPx"]/lw),
      len(r["findings"])+len(r["text"]), len(r["human"]))
PY
)
  printf '%-52s %-12s %8s%% %8s%% %7s %6s\n' "$n" "$v" "$m" "$i" "$f" "$p"
  case "$v" in
    correct)     correct=$((correct+1));;
    needs-human) human=$((human+1));;
    *)           improvable=$((improvable+1));;
  esac
done < "$LIST"

printf '%s\n' "--------------------------------------------------------------------------------------------------"
printf 'correct %d   improvable %d   needs-human %d   failed %d\n' \
       "$correct" "$improvable" "$human" "$failed"
