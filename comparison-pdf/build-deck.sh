#!/usr/bin/env bash
# Build the figure-by-figure review deck from a sweep directory.
#
#   comparison-pdf/build-deck.sh <ubl-clone> <sweep-dir> <out.pdf> [names-file]
#
# One landscape page per figure: the original artwork, the conversion, and the
# difference between them with red for ink the SVG lost and blue for ink it
# invented, with that figure's findings listed beside it. Figures come out in the
# order the specification numbers them, whatever order the names file is in.
#
# Needs Saxon (an XSLT 2 processor) and Apache FOP, neither of which ships here:
#   SAXON_JAR   saxon .jar, plus xmlresolver on the same path if your build needs
#               it (default: ./jars/saxon.jar:./jars/xmlresolver.jar)
#   FOP         the fop executable            (default: fop on PATH)
set -euo pipefail

HERE=$(cd "$(dirname "$0")" && pwd)
# The stylesheet writes these into the .fo as they are given, and FOP resolves
# what it finds there against the filesystem root - so a relative directory ends
# up as file://r128/... and every image is silently missing from the PDF.
UBL=$(cd "${1:?the oasis-tcs/ubl clone}" && pwd)
SWEEP=$(cd "${2:?a directory written by verdict-sweep.sh}" && pwd)
OUT=${3:?output .pdf}
NAMES=$(cd "$(dirname "${4:-$HERE/../tools/uml78-bycomplexity.txt}")" && pwd)/$(basename "${4:-uml78-bycomplexity.txt}")
SAXON_JAR=${SAXON_JAR:-$PWD/jars/saxon.jar:$PWD/jars/xmlresolver.jar}
FOP=${FOP:-fop}

work=$(mktemp -d); trap 'rm -rf "$work"' EXIT

# FOP will not read a 1-bit PNG and three of the 97 are 1-bit, so those three are
# re-saved as RGB. The pixels are untouched: the deck shows the artwork as it is.
mkdir -p "$work/art"
python3 - "$UBL/art" "$work/art" <<'PY'
import glob, os, sys
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
src, dst = sys.argv[1], sys.argv[2]
for p in glob.glob(os.path.join(src, "*.png")):
    out = os.path.join(dst, os.path.basename(p))
    im = Image.open(p)
    if im.mode in ("1", "L", "P"):
        im.convert("RGB").save(out)
    else:
        os.symlink(os.path.abspath(p), out)
PY

# The spec source drives the page order and the captions. Its DOCTYPE names the
# DocBook DTD by public identifier, which the transform does not need and cannot
# fetch offline; the internal subset is kept, so the copy lives in the clone for
# its entity references to resolve.
LOCAL=$UBL/UBL-deck-local.xml
trap 'rm -rf "$work"; rm -f "$LOCAL"' EXIT
python3 - "$UBL/UBL.xml" "$LOCAL" <<'PY'
import re, sys
x = open(sys.argv[1], encoding="utf-8").read()
x = re.sub(r'<!DOCTYPE\s+article\s+PUBLIC\s+"[^"]*"\s*"[^"]*"', "<!DOCTYPE article", x, count=1)
open(sys.argv[2], "w", encoding="utf-8").write(x)
PY

java -cp "$SAXON_JAR" net.sf.saxon.Transform \
  -s:"$LOCAL" -xsl:"$HERE/imageTriptych.xsl" -o:"$work/deck.fo" \
  art-dir="$work/art" svg-dir="$SWEEP" diff-dir="$SWEEP" verdict-dir="$SWEEP" \
  include="$(tr '\n' ' ' < "$NAMES")" \
  diff-suffix=-marked.png \
  diff-caption="Difference: red lost from the SVG, blue invented by it"

"$FOP" -fo "$work/deck.fo" -pdf "$OUT"
echo "wrote $OUT"
