#!/bin/bash
# Makes the four Fulfilment illustrations again, from the deck and the UBL PNGs:
# their parts (illustrations/parts/) and their drawings (diagrams/UBL-2.2-Fulfilment-*/).
#
#   UBL=<clone of oasis-tcs/ubl, branch ubl-2.5> history/illustrations/run.sh
#
# Fetches the deck into WORK (default history/illustrations/work/) unless PPT
# names it, and checks it is the one the illustrations were made from. Needs
# Python 3 with numpy, scipy, opencv, pillow, olefile, potracer and shapely,
# and Node with playwright.
set -e
here="$(cd "$(dirname "$0")" && pwd)"
export NODE_PATH="${NODE_PATH:+$NODE_PATH:}$(npm root -g 2>/dev/null)"
export WORK="${WORK:-$here/work}"
export PPT="${PPT:-$WORK/ShipmentConsignment-2.ppt}"
mkdir -p "$WORK"
if [ ! -f "$PPT" ]; then
  curl -sSL -o "$PPT" 'https://groups.oasis-open.org/HigherLogic/System/DownloadDocumentFile.ashx?DocumentFileKey=f01809ee-5273-41ac-8e1d-85ac620bc43a'
fi
echo "0d5c0fd5c4a426bdd24c9fe2267c2d88d5ae361f14b241f119eb683cecff0d4c  $PPT" | sha256sum -c --quiet -
cd "$here"
python3 extract.py            # the deck's pictures
python3 wmf2svg.py            # its clip art as SVG
python3 parts_grey.py         # in plain greys, for the first fit
python3 document.py           # the document, traced          -> illustrations/parts/document.svg
python3 camera.py             # the camera of the pallet photo
python3 pallet.py             # the pallet of boxes, drawn    -> illustrations/parts/pallet.svg
for n in 2 3 4 5; do python3 fit.py $n; done       # the drawings, fitted to the PNGs
python3 tones.py              # the PNGs' greys for the clip art -> illustrations/parts/
for n in 2 3 4 5; do python3 fit.py $n; done       # the drawings again, with those parts
