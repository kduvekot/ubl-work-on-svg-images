#!/usr/bin/env bash
# Convert and judge a whole set of diagrams, hardest first.
#
#   tools/verdict-sweep.sh <art-dir> <out-dir> <names-file> [radius]
#
# For each basename in <names-file>: run the pipeline, then verify the result.
# Prints one line per diagram as it finishes, then the same lines in the order the
# list gave them, and a tally. Leaves a -struct.json beside each conversion.
# Ordering of the list is the caller's: feed it a list sorted by complexity so the
# hard cases are met first, while there is still room to change the approach.
#
# Diagrams are independent, so they run JOBS at a time (default: one per core).
# Set JOBS=1 to get the old strictly serial behaviour, which is easier to read
# when a single diagram is being debugged.
#
# A diagram is CORRECT only when the line-work diff is blank at the honest radius
# and every label reads back correctly. Never widen the radius to get there.
set -uo pipefail

HERE=$(cd "$(dirname "$0")" && pwd)

# ---- one diagram, run as a child of the sweep below ------------------------
if [ "${1:-}" = "--one" ]; then
  ART=$2; OUT=$3; RADIUS=$4; n=$5
  line() { printf '%-52s %-12s %8s%% %8s%% %7s %6s\n' "$@"; }
  fail() { printf '%-52s %-12s\n' "$n" "$1" | tee "$OUT/$n-verdict.line"; exit 0; }

  "$HERE/run-pipeline.sh" "$ART" "$OUT" "$n" > "$OUT/$n-pipeline.log" 2>&1 \
      || fail PIPELINE-FAIL
  rep="$OUT/$n-struct.json"
  python3 "$HERE/verify_conversion.py" "$ART/$n.png" "$OUT/$n-render.png" \
      "$OUT/$n-graph.json" --radius "$RADIUS" --json "$rep" \
      --diff "$OUT/$n-lwdiff.png" \
      > "$OUT/$n-verify.log" 2>&1 || fail VERIFY-FAIL

  # number each finding on a copy of the difference image, and write the same
  # numbering back into the report, so the review deck's list and its picture
  # cannot disagree
  python3 "$HERE/mark_findings.py" "$OUT/$n-diff-r2.png" "$rep" "$OUT/$n-marked.png" \
      "$OUT/$n-lwdiff.png" \
      >> "$OUT/$n-verify.log" 2>&1 || true

  read -r v m i f p < <(python3 - "$rep" <<'PY'
import json,sys
r=json.load(open(sys.argv[1]))
lw=max(1,r.get("lineWorkInk",1))
print(r["verdict"], "%.3f"%(100.0*r["missingPx"]/lw), "%.3f"%(100.0*r["inventedPx"]/lw),
      len(r["findings"])+len(r["text"]), len(r["human"]))
PY
)
  # one printf, so a line never interleaves with another worker's
  line "$n" "$v" "$m" "$i" "$f" "$p" | tee "$OUT/$n-verdict.line"
  exit 0
fi

# ---- the sweep ------------------------------------------------------------
ART=${1:?art directory}
OUT=${2:?output directory}
LIST=${3:?file of basenames, one per line}
RADIUS=${4:-3}
JOBS=${JOBS:-$(nproc 2>/dev/null || echo 4)}

mkdir -p "$OUT"
[ -f "$HERE/VisualDiff.class" ] || javac -d "$HERE" "$HERE/VisualDiff.java"

names=()
while read -r n; do [ -n "$n" ] && names+=("$n"); done < "$LIST"
for n in "${names[@]}"; do rm -f "$OUT/$n-verdict.line"; done

rule='--------------------------------------------------------------------------------------------------'
printf 'sweeping %d diagram(s), %s at a time\n\n' "${#names[@]}" "$JOBS"
printf '%-52s %-12s %9s %9s %7s %6s\n' FIGURE VERDICT MISSING INVENTED FINDINGS PERSON
printf '%s\n' "$rule"

printf '%s\0' "${names[@]}" \
  | xargs -0 -P "$JOBS" -I{} "$0" --one "$ART" "$OUT" "$RADIUS" {}

# The streamed lines above arrive in completion order; repeat them in list order so
# a complex-to-simple sweep still reads as one, and tally the verdicts.
printf '\n%-52s %-12s %9s %9s %7s %6s\n' FIGURE VERDICT MISSING INVENTED FINDINGS PERSON
printf '%s\n' "$rule"
correct=0; improvable=0; human=0; failed=0
for n in "${names[@]}"; do
  f="$OUT/$n-verdict.line"
  [ -f "$f" ] || { printf '%-52s %-12s\n' "$n" "NO-RESULT"; failed=$((failed+1)); continue; }
  cat "$f"
  case $(awk '{print $2}' "$f") in
    correct)     correct=$((correct+1));;
    needs-human) human=$((human+1));;
    *-FAIL)      failed=$((failed+1));;
    *)           improvable=$((improvable+1));;
  esac
done
printf '%s\n' "$rule"
printf 'correct %d   improvable %d   needs-human %d   failed %d\n' \
       "$correct" "$improvable" "$human" "$failed"
