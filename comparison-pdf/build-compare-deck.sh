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

# The renders are at the original's 600 dpi, three to a page, and the deck came
# to 43 MB. Each panel is 122mm across, so a copy DECK_PX wide (default 1800, about
# 375 dpi on the page) loses nothing the page can show. The difference is reduced
# so that nothing can vanish in it: a block is red if any pixel in it is red,
# else blue if any is blue, else grey if any is grey - a one-pixel difference
# stays visible at any size.
mkdir -p "$work/cmp"
python3 - "$CMP" "$work/cmp" "${DECK_PX:-1800}" <<'PY'
import glob, os, shutil, sys
import numpy as np
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
src, dst, px = sys.argv[1], sys.argv[2], int(sys.argv[3])
for p in glob.glob(os.path.join(src, "*.json")):
    shutil.copy(p, dst)
for p in glob.glob(os.path.join(src, "*-base.png")) + glob.glob(os.path.join(src, "*-new.png")):
    # the drawings are black on white, so grey loses nothing and is a third the size
    im = Image.open(p).convert("L")
    if im.width > px:
        im = im.resize((px, round(im.height * px / im.width)), Image.LANCZOS)
    im.save(os.path.join(dst, os.path.basename(p)), optimize=True)
for p in glob.glob(os.path.join(src, "*-basediff.png")):
    a = np.asarray(Image.open(p).convert("RGB"))
    f = max(1, -(-a.shape[1] // px))                       # block size, rounded up
    h, w = -(-a.shape[0] // f) * f, -(-a.shape[1] // f) * f
    pad = np.full((h, w, 3), 255, np.uint8); pad[:a.shape[0], :a.shape[1]] = a
    blocks = pad.reshape(h // f, f, w // f, f, 3)
    col = lambda c: (blocks == np.array(c, np.uint8)).all(-1).any((1, 3))
    out = np.full((h // f, w // f, 3), 255, np.uint8)
    out[col((0xED, 0xED, 0xED))] = (0xED, 0xED, 0xED)
    out[col((0x00, 0x60, 0xD0))] = (0x00, 0x60, 0xD0)
    out[col((0xD4, 0x00, 0x00))] = (0xD4, 0x00, 0x00)
    # four colours exactly, as a palette image
    Image.fromarray(out).quantize(colors=4, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE) \
        .save(os.path.join(dst, os.path.basename(p)), optimize=True)
PY

java -cp "$SAXON_JAR" net.sf.saxon.Transform \
  -s:"$LOCAL" -xsl:"$HERE/baselineCompare.xsl" -o:"$work/compare.fo" \
  compare-dir="$work/cmp" include="$(tr '\n' ' ' < "$NAMES")" \
  baseline-label="$BLABEL" new-label="$NLABEL"

"$FOP" -fo "$work/compare.fo" -pdf "$OUT"
echo "wrote $OUT"
