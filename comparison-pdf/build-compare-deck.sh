#!/usr/bin/env bash
# Build the baseline comparison deck from what tools/compare-to-baseline.sh wrote.
#
#   comparison-pdf/build-compare-deck.sh <ubl-clone> <compare-dir> <out.pdf> \
#       [baseline-label] [new-label] [names-file]
#
# A summary page, then one landscape page per figure: the baseline SVG and the new
# SVG, both rendered at the original PNG's size, and the difference between them
# with red for ink only the baseline has and blue for ink only the new one has.
# Figures are numbered and ordered as the specification numbers them.
#
# Needs Saxon (XSLT 3) and Apache FOP, as build-deck.sh does:
#   SAXON_JAR   default ./jars/saxon.jar:./jars/xmlresolver.jar
#   FOP         default fop on PATH
set -euo pipefail

HERE=$(cd "$(dirname "$0")" && pwd)
# absolute paths: the stylesheet writes them into the .fo as given, and FOP
# resolves them against the filesystem root (see build-deck.sh)
UBL=$(cd "${1:?the oasis-tcs/ubl clone}" && pwd)
CMP=$(cd "${2:?a directory written by compare-to-baseline.sh}" && pwd)
OUT=${3:?output .pdf}
BLABEL=${4:-baseline}
NLABEL=${5:-new run}
NAMES=$(cd "$(dirname "${6:-$HERE/../tools/uml78-bycomplexity.txt}")" && pwd)/$(basename "${6:-uml78-bycomplexity.txt}")
SAXON_JAR=${SAXON_JAR:-$PWD/jars/saxon.jar:$PWD/jars/xmlresolver.jar}
FOP=${FOP:-fop}

work=$(mktemp -d)
# the specification drives the page order and the captions; its DOCTYPE names a
# DTD the transform neither needs nor can fetch offline (see build-deck.sh)
LOCAL=$UBL/UBL-compare-local.xml
trap 'rm -rf "$work"; rm -f "$LOCAL"' EXIT
python3 - "$UBL/UBL.xml" "$LOCAL" <<'PY'
import re, sys
x = open(sys.argv[1], encoding="utf-8").read()
x = re.sub(r'<!DOCTYPE\s+article\s+PUBLIC\s+"[^"]*"\s*"[^"]*"', "<!DOCTYPE article", x, count=1)
open(sys.argv[2], "w", encoding="utf-8").write(x)
PY

java -cp "$SAXON_JAR" net.sf.saxon.Transform \
  -s:"$LOCAL" -xsl:"$HERE/baselineCompare.xsl" -o:"$work/compare.fo" \
  compare-dir="$CMP" include="$(tr '\n' ' ' < "$NAMES")" \
  baseline-label="$BLABEL" new-label="$NLABEL"

"$FOP" -fo "$work/compare.fo" -pdf "$OUT"
echo "wrote $OUT"
