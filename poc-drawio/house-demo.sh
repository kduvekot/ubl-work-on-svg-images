#!/bin/bash
# The house-style demonstration for the TC, as a PDF.
#
#   poc-drawio/house-demo.sh <out.pdf> [<figure> ...]
#
# Draws each figure in the house style (house_style.py, drawio_from_spec.py),
# renders it with draw.io's own code, and prints house_demo.py's page to PDF
# in Chromium. Default: five figures from the simplest to the most complex.
set -e
here="$(cd "$(dirname "$0")" && pwd)"
root="$(cd "$here/.." && pwd)"
pdf="$1"; shift || true
[ -n "$pdf" ] || { echo "usage: $0 <out.pdf> [<figure> ...]" >&2; exit 2; }
[ $# -gt 0 ] || set -- UBL-2.2-Tender-GuaranteeDeposit UBL-2.5-BillingwithDebitNoteProcess \
  UBL-2.2-CPFR-CreateOrderForecast UBL-1.0-ProcurementProcess UBL-2.2-IMFM-IntermodalFreightManagementProcess
work="$(mktemp -d)"; trap 'rm -rf "$work"' EXIT
# the figures shown three ways, and the extra pages: routing (Procurement
# three ways) and making space (before and after)
ROUTING=${ROUTING:-UBL-1.0-ProcurementProcess}
SPACE=${SPACE:-"UBL-2.2-Tender-QualificationApplication UBL-2.3-GoodsCertificateExportProcess"}
export ROUTING SPACE
draw() {   # <figure> <variant> [house_style.py options]
  n="$1"; v="$2"; shift 2
  src="$root/diagrams/$n"
  [ -f "$work/$n-faithful-spec.json" ] || \
    python3 "$root/tools/spec_from_model.py" "$src/$n-diagram.json" "$work/$n-faithful-spec.json" 1480 > /dev/null
  python3 "$here/house_style.py" "$work/$n-faithful-spec.json" "$work/$n-$v-spec.json" "$@" > /dev/null
  python3 "$here/drawio_from_spec.py" "$work/$n-$v-spec.json" "$work/$n-$v.drawio" "$src/$n-diagram.json" > /dev/null
  read W H < <(python3 -c "import json,sys; c=json.load(open(sys.argv[1]))['canvas']; print(c['w'], c['h'])" "$work/$n-$v-spec.json")
  node "$here/render-drawio.js" "$work/$n-$v.drawio" "$work/$n-$v.png" "$W" "$H" 4 > /dev/null
}
# the house style: boxes lined up, room made, flows routed across and down
# (libavoid, avoid_route.mjs: run `npm install` in poc-drawio/ once)
for n in "$@"; do
  draw "$n" house --avoid
  cp "$work/$n-house-spec.json" "$work/$n-spec.json"
done
for n in $ROUTING; do
  draw "$n" house --avoid; draw "$n" angled --no-grid
done
for n in $SPACE; do
  draw "$n" house --avoid; draw "$n" nospace --no-space --avoid
done
python3 "$here/house_demo.py" "$work" "$work/demo.html" "$@"
node -e '
const { chromium } = require("playwright");
(async () => {
  const b = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH || "/opt/pw-browsers/chromium-1194/chrome-linux/chrome" });
  const p = await b.newPage();
  await p.goto("file://" + process.argv[1], { waitUntil: "load" });
  await p.pdf({ path: process.argv[2], preferCSSPageSize: true, printBackground: true });
  await b.close();
})().catch(e => { console.error(e); process.exit(1); });' "$work/demo.html" "$pdf"
echo "  $pdf"
