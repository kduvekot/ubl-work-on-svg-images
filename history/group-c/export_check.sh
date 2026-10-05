#!/bin/sh
# export one figure and compare it with the UBL PNG: history/group-c/export_check.sh <figure> <ubl>/art <out>
set -e
cd "$(dirname "$0")/../.."
NODE_PATH=$(npm root -g) node tools/export_drawio.js "$3/export" diagrams/$1/$1.drawio
python3 history/group-a/compare_png.py "$2" "$3/export/art" "$3/diff" $1
