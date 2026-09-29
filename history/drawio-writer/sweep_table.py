#!/usr/bin/env python3
"""The sweep's table: one row per figure, worst first.

    python3 sweep_table.py <out-dir> <figure> ...

Reads <out-dir>/<figure>/<figure>-compare.txt and -missing.txt (sweep.sh)."""
import os, re, sys


def row(out, n):
    d = os.path.join(out, n, n)
    txt = open(d + "-compare.txt").read()
    if "lacks (red)" not in txt:
        err = open(d + "-missing.txt").read().strip().splitlines()
        return n, 999.0, 999.0, "FAILED", err[-1] if err else "no comparison"
    red = float(re.search(r"lacks \(red\):\s+\d+ px\s+([\d.]+)%", txt).group(1))
    blue = float(re.search(r"lacks \(blue\):\s+\d+ px\s+([\d.]+)%", txt).group(1))
    kinds = re.findall(r"^    (.+?)\s{2,}(\d+) /\s+(\d+)$", txt, re.M)
    worst = max(kinds, key=lambda k: int(k[1]) + int(k[2]))[0] if kinds else ""
    miss = open(d + "-missing.txt").read().strip()
    miss = miss.split(": ", 1)[1] if ": " in miss else ""
    return n, red, blue, worst, miss


def main(out, figures):
    rows = sorted((row(out, n) for n in figures), key=lambda r: -(r[1] + r[2]))
    print("# draw.io sweep: each figure's draw.io render against its SVG\n")
    print("%d figures. Red: the SVG's ink draw.io lacks; blue: draw.io's ink the SVG lacks;"
          " both as a share of the SVG's ink, within 2 px. Worst first.\n" % len(rows))
    done = [r for r in rows if not r[4] and r[3] != "FAILED"]
    print("Figures with nothing left undrawn: %d. Their red: at most %.2f %%, mean %.2f %%.\n"
          % (len(done), max((r[1] for r in done), default=0),
             sum(r[1] for r in done) / max(1, len(done))))
    print("| figure | red % | blue % | most difference in | not drawn yet |")
    print("|---|---:|---:|---|---|")
    for n, red, blue, worst, miss in rows:
        print("| %s | %.2f | %.2f | %s | %s |" % (n, red, blue, worst, miss))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
