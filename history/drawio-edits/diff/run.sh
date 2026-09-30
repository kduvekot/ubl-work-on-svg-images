#!/bin/bash
# The original PNGs against the draw.io drawings, as one PDF.
#
#   UBL=<clone of oasis-tcs/ubl, branch ubl-2.5> history/drawio-edits/diff/run.sh <out dir>
#
# Writes only to <out dir>: per figure the pictures and result.json, and
# <out dir>/png-vs-drawio.pdf. Needs Python 3 with numpy, scipy and pillow, Node
# with playwright (as history/drawio-writer/render-drawio.js), and pdfunite.
set -e
# playwright drives the renders; a global install is not on node's own path
export NODE_PATH="${NODE_PATH:+$NODE_PATH:}$(npm root -g 2>/dev/null)"
here="$(cd "$(dirname "$0")" && pwd)"
out="$(mkdir -p "$1" && cd "$1" && pwd)"
cd "$here"
python3 insertions.py "$out"
ls ../../../diagrams | xargs -P 4 -I{} python3 one.py {} "$out"
python3 -c "import json,sys; print('\n'.join(json.load(open(sys.argv[1]))))" "$out/insertions.json" | xargs -P 4 -I{} python3 cutpng.py {} "$out"
python3 pdf.py "$out"
node print.js "$out"/pages/p-*.html
pdfunite "$out"/pages/p-*.pdf "$out/png-vs-drawio.pdf"
echo "$out/png-vs-drawio.pdf"
