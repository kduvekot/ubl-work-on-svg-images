#!/usr/bin/env python3
"""Decide whether a converted diagram is correct, improvable, or needs a person.

    verify_conversion.py <original.png> <render.png> <graph.json>
                         [--radius 3] [--json report.json] [--diff diff.png]

The original PNG is the source of truth. The artwork holds two kinds of content
and they are checked differently, because one of them can reach pixel-perfect
and the other never can:

  line-work  boxes, arrows, partition rules, frames. Compared as pixels with the
             text masked out of BOTH images, at a radius that absorbs
             anti-aliasing and nothing else (2-3). Blank is achievable, so blank
             is the gate.

  text       compared AS TEXT: every label must be present, in the right place,
             and read back correctly. A pixel comparison cannot do this - a
             redrawn label in a different typeface differs everywhere even when
             it is perfectly correct, and, worse, a pixel test at any tolerance
             wide enough to forgive that will also forgive "Send ..." rendered
             as "end ...".

Do not widen the radius to make a diagram pass. A wide radius stops measuring:
at r=40 an entire node box displaced 20px scores identically to one in the right
place. If the diff shows a difference, fix the SVG.

The verdict is one of:

  correct     nothing left to do
  improvable  a defect the toolchain can fix, each one located and named
  needs-human something in the original could not be read with confidence, so a
              person has to look at a named region

Findings carry coordinates in the original PNG's pixel space, and are attributed
to the graph element they touch, so "what is wrong" is answerable without
opening the diff by eye.
"""
import json
import re
import sys

import numpy as np
import scipy.ndimage as ndi
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

MIN_FINDING_AREA = 60      # ignore specks: anti-aliasing crumbs, single stray pixels
TEXT_PAD = 0.35            # pad text boxes by this fraction of the font size
OCR_MATCH = 0.90           # difflib ratio above which a label reads back as correct


def ink_of(path):
    im = Image.open(path)
    bg = Image.new("RGB", im.size, "white")
    bg.paste(im, mask=im.split()[-1] if im.mode in ("RGBA", "LA") else None)
    return np.asarray(bg.convert("L")) < 128, bg


def text_boxes(bg_original, min_conf=30):
    """Every rectangle that holds text **in the original**, found independently of
    the model being judged.

    Deriving this from the model's own label boxes looks tempting - they are
    already measured - but it makes the referee corruptible: a model that
    hallucinates label lines masks more of the canvas, hides the line-work
    underneath, and therefore scores better than a model that reads the same
    diagram correctly. That is the same failure as widening the diff radius,
    arrived at from the other end. The original cannot be gamed, so the mask
    comes from the original and is identical for every candidate."""
    try:
        import pytesseract
    except ImportError:
        return []
    d = pytesseract.image_to_data(bg_original, config="--psm 11",
                                  output_type=pytesseract.Output.DICT)
    out = []
    for i, txt in enumerate(d["text"]):
        try:
            conf = float(d["conf"][i])
        except (TypeError, ValueError):
            continue
        if txt.strip() and conf >= min_conf:
            out.append((d["left"][i], d["top"][i], d["width"][i], d["height"][i],
                        "text %r" % txt.strip()[:24]))
    return out


def mask_text(shape, boxes, font_px):
    """True where text lives, padded so glyph overshoot and descenders are covered"""
    m = np.zeros(shape, bool)
    pad = max(4, int(TEXT_PAD * max(font_px, 8)))
    H, W = shape
    for x, y, w, h, _ in boxes:
        m[max(0, y - pad):min(H, y + h + pad), max(0, x - pad):min(W, x + w + pad)] = True
    return m


def near(mask, radius):
    """dilate by a square of the given radius - 'is there ink within r pixels'"""
    k = 2 * radius + 1
    return ndi.binary_dilation(mask, np.ones((k, k), bool))


def components(diff, min_area=MIN_FINDING_AREA):
    lab, n = ndi.label(diff)
    out = []
    for i, sl in enumerate(ndi.find_objects(lab), start=1):
        if sl is None:
            continue
        area = int((lab[sl] == i).sum())
        if area < min_area:
            continue
        out.append(dict(x=int(sl[1].start), y=int(sl[0].start),
                        w=int(sl[1].stop - sl[1].start), h=int(sl[0].stop - sl[0].start),
                        area=area))
    out.sort(key=lambda r: -r["area"])
    return out


def attribute(f, graph):
    """name the graph element a finding sits on, so the report is readable"""
    cx, cy = f["x"] + f["w"] / 2.0, f["y"] + f["h"] / 2.0
    for n in graph.get("nodes", []):
        if n["x"] - 8 <= cx <= n["x"] + n["w"] + 8 and n["y"] - 8 <= cy <= n["y"] + n["h"] + 8:
            return "on node %s (%s%s)" % (n["id"], n["kind"],
                                          " %r" % n["label"][:20] if n.get("label") else "")
    best, bd = None, 1e18
    for e in graph.get("edges", []):
        for p in (e.get("fromPoint"), e.get("toPoint")):
            if not p:
                continue
            d = (p[0] - cx) ** 2 + (p[1] - cy) ** 2
            if d < bd:
                best, bd = e, d
    if best is not None and bd < 300 ** 2:
        return "near edge %s -> %s" % (best.get("from"), best.get("to"))
    return "unattributed"


def norm(s):
    return re.sub(r"\s+", " ", (s or "")).strip()


def check_text(bg_render, graph, findings, human):
    """every label present, in its place, and reading back as what it should say"""
    try:
        import pytesseract
    except ImportError:
        human.append(dict(kind="text-unchecked",
                          reason="pytesseract not installed, so no label was read back",
                          check="install pytesseract to verify label text"))
        return
    for n in graph.get("nodes", []):
        want = norm(n.get("label"))
        lines = n.get("labelLines") or []
        if not want or not lines:
            continue
        x0 = min(l["x"] for l in lines); y0 = min(l["y"] for l in lines)
        x1 = max(l["x"] + l["w"] for l in lines); y1 = max(l["y"] + l["h"] for l in lines)
        pad = 10
        crop = bg_render.crop((max(0, x0 - pad), max(0, y0 - pad), x1 + pad, y1 + pad))
        got = norm(pytesseract.image_to_string(crop, config="--psm 6"))
        if not got:
            findings.append(dict(kind="label-missing", node=n["id"], x=x0, y=y0,
                                 w=x1 - x0, h=y1 - y0, expected=want, got="",
                                 detail="nothing renders where %s's label should be" % n["id"]))
            continue
        import difflib
        r = difflib.SequenceMatcher(None, want.lower(), got.lower()).ratio()
        if r < OCR_MATCH:
            findings.append(dict(kind="label-mismatch", node=n["id"], x=x0, y=y0,
                                 w=x1 - x0, h=y1 - y0, expected=want, got=got,
                                 ratio=round(r, 3),
                                 detail="%s renders as %r, model says %r" % (n["id"], got, want)))


def verify(orig_png, render_png, graph_path, radius=3, diff_out=None):
    graph = json.load(open(graph_path))
    a, bg_orig = ink_of(orig_png)
    b, bg_render = ink_of(render_png)
    if a.shape != b.shape:
        return dict(verdict="improvable", name=graph_path,
                    findings=[dict(kind="size-mismatch", detail="original %s, render %s"
                                   % (a.shape[::-1], b.shape[::-1]))], human=[], text=[])

    boxes = text_boxes(bg_orig)
    tmask = mask_text(a.shape, boxes, graph.get("fontPx") or 12)
    la, lb = a & ~tmask, b & ~tmask                      # line-work only, both sides

    missing = la & ~near(lb, radius)
    extra = lb & ~near(la, radius)

    findings = []
    for f in components(missing):
        findings.append(dict(kind="line-work-missing", detail=attribute(f, graph), **f))
    for f in components(extra):
        findings.append(dict(kind="line-work-invented", detail=attribute(f, graph), **f))

    human = list(graph.get("uncertain", []))
    text_findings = []
    check_text(bg_render, graph, text_findings, human)

    if diff_out:
        out = np.full(a.shape + (3,), 255, np.uint8)
        out[missing] = (212, 0, 0)
        out[extra] = (0, 96, 208)
        Image.fromarray(out).save(diff_out)

    all_f = findings + text_findings
    verdict = "correct" if not all_f else "improvable"
    if verdict == "correct" and human:
        verdict = "needs-human"
    return dict(name=graph.get("source", graph_path), verdict=verdict, radius=radius,
                lineWorkInk=int(la.sum()),
                missingPx=int(missing.sum()), inventedPx=int(extra.sum()),
                findings=findings, text=text_findings, human=human)


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 2
    radius = int(argv[argv.index("--radius") + 1]) if "--radius" in argv else 3
    oj = argv[argv.index("--json") + 1] if "--json" in argv else None
    od = argv[argv.index("--diff") + 1] if "--diff" in argv else None
    pos = [x for i, x in enumerate(argv)
           if not x.startswith("--") and (i == 0 or not argv[i - 1].startswith("--"))]
    rep = verify(pos[0], pos[1], pos[2], radius, od)

    lw = max(1, rep.get("lineWorkInk", 1))
    print("  verdict: %s" % rep["verdict"].upper())
    print("  line-work  missing %d px (%.3f%%)   invented %d px (%.3f%%)   radius %d"
          % (rep["missingPx"], 100.0 * rep["missingPx"] / lw,
             rep["inventedPx"], 100.0 * rep["inventedPx"] / lw, rep["radius"]))
    for f in rep["findings"][:12]:
        print("    %-20s %5d px at %5d,%-5d %4dx%-4d  %s"
              % (f["kind"], f["area"], f["x"], f["y"], f["w"], f["h"], f["detail"]))
    if len(rep["findings"]) > 12:
        print("    ... and %d more line-work findings" % (len(rep["findings"]) - 12))
    for t in rep["text"][:10]:
        print("    %-20s %s" % (t["kind"], t["detail"]))
    if rep["human"]:
        print("  needs a person (%d):" % len(rep["human"]))
        for h in rep["human"][:8]:
            where = (" at %s,%s" % (h.get("x"), h.get("y"))) if "x" in h else ""
            print("    %-18s%s  %s" % (h.get("kind"), where, h.get("check", h.get("reason", ""))))
    if oj:
        json.dump(rep, open(oj, "w"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
