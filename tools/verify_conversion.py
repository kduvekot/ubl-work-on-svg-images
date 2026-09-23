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


def structural(diff, other_linework, glyph_h, span=15):
    """Split residual ink into placement error and genuinely absent content.

    A redraw never lands every line exactly, so *some* residue is unavoidable and
    demanding none of it is demanding the impossible. What is not acceptable is a
    missing element. The two are distinguishable, and the distinction was noted in
    the very first session and then dropped: red paired with ink nearby means the
    element is there and displaced; red with nothing near it means the element is
    not there at all.

    So: residue that lies within `span` of line-work on the other side is a
    placement error and is tolerated; anything else is a candidate loss, and
    counts as structural when it is at least as long as a letter is tall -
    nothing shorter than a glyph is a node, a connector or an arrowhead."""
    free = diff & ~near(other_linework, span)
    out = []
    for f in components(free, min_area=max(MIN_FINDING_AREA, int(0.25 * glyph_h))):
        # element-sized means a letter's worth of ink, or a line long enough to be
        # a connector. A 33x15 sliver is neither, however it is oriented.
        if f["area"] >= 0.5 * glyph_h * glyph_h or max(f["w"], f["h"]) >= 3 * glyph_h:
            out.append(f)
    return out


def check_text_complete(bg_orig, graph, boxes, findings, glyph_h):
    """Every word the original shows must be somewhere in the model, saying the
    same thing, in the same place. Read off the original, so the model cannot
    grade its own homework by simply not extracting a label."""
    import difflib
    placed = []
    for n in graph.get("nodes", []):
        for ln in n.get("labelLines") or []:
            placed.append((ln, ln.get("text", ""), "label of %s" % n["id"]))
    for t in graph.get("text", []):
        for ln in t.get("lines") or [t]:
            placed.append((ln, ln.get("text", ""), "text block"))
    for p in graph.get("partitions", []):
        b = p.get("titleBox")
        if b:
            placed.append((dict(x=b[0], y=b[1], w=b[2], h=b[3]), p.get("title", ""),
                           "title of %s %s" % (p.get("axis"), p.get("index"))))
    for x, y, w, h, label in boxes:
        want = norm(label[6:].strip("'\"") if label.startswith("text ") else label)
        # tesseract boxes are per word, the model holds whole lines, so the test is
        # whether the word appears in the line covering it - not whether the word
        # equals the line. Single marks are OCR reading the line-work ("|" off a
        # divider) and are not text at all.
        if len(re.sub(r"[^0-9A-Za-z]", "", want)) < 2:
            continue
        cx, cy = x + w / 2.0, y + h / 2.0
        # every line whose box covers this word, not just the first: a label wraps,
        # and the word may be on its second line
        hits = [(txt, where) for ln, txt, where in placed
                if ln["x"] - w <= cx <= ln["x"] + ln["w"] + w and
                ln["y"] - h <= cy <= ln["y"] + ln["h"] + h]
        hit = hits[0] if hits else None
        if hit is None:
            findings.append(dict(kind="text-absent", x=x, y=y, w=w, h=h, expected=want,
                                 detail="the original says %r here and the model has "
                                        "nothing there" % want[:40]))
            continue
        tokens = [t for txt, _ in hits for t in norm(txt).replace("\n", " ").split()]
        if not any(difflib.SequenceMatcher(None, want.lower(), t.lower()).ratio() >= 0.8
                   for t in tokens):
            findings.append(dict(kind="text-differs", x=x, y=y, w=w, h=h, expected=want,
                                 got=norm(hit[0]),
                                 detail="original says %r, model has %r (%s)"
                                        % (want[:24], norm(hit[0])[:30], hit[1])))


def check_arrow_directions(a, b, graph, glyph_h, findings, ratio=1.25):
    """An arrowhead sitting a few pixels off, or drawn at a slightly different
    angle, is placement error and is tolerated like any other. An arrowhead
    pointing the *other way* is not: that is a reversed edge, and the diagram then
    says something the artwork does not.

    Which end carries the head is read the same way in both images - the head is
    the end with markedly more ink around it - so the test compares what the
    original shows against what the SVG drew, never against what the model claims.
    Where either image is ambiguous the edge is left alone; those are the ones the
    extractor already flags as LOW direction confidence for a person to settle."""
    H, W = a.shape
    r = max(20, int(2.0 * glyph_h))

    def mass(img, p):
        y0, y1 = max(0, p[1] - r), min(H, p[1] + r)
        x0, x1 = max(0, p[0] - r), min(W, p[0] + r)
        return int(img[y0:y1, x0:x1].sum())

    for e in graph.get("edges", []):
        p, q = e.get("fromPoint"), e.get("toPoint")
        if not p or not q:
            continue

        def head(img):
            f, t = mass(img, p), mass(img, q)
            if t > f * ratio:
                return "to"
            if f > t * ratio:
                return "from"
            return None

        ho, hr = head(a), head(b)
        if ho and hr and ho != hr:
            tip = q if ho == "to" else p
            findings.append(dict(kind="arrow-reversed", x=tip[0] - r, y=tip[1] - r,
                                 w=2 * r, h=2 * r,
                                 detail="edge %s->%s: the original points %s %s, the SVG "
                                        "points the other way"
                                        % (e.get("from"), e.get("to"),
                                           "towards" if ho == "to" else "back from",
                                           e.get("to") if ho == "to" else e.get("from"))))


def check_coherent(graph, glyph_h, findings):
    """Internal consistency - cheap, and it catches nonsense the pixels cannot."""
    ids = {n["id"] for n in graph.get("nodes", [])}
    ok_for = {"rhombus": {"decision"}, "rounded": {"action"},
              "rect": {"object", "fork", "note", "action"},
              "ellipse": {"initial", "final"}, "circle": {"initial", "final"}}
    for e in graph.get("edges", []):
        for end in ("from", "to"):
            if e.get(end) not in ids:
                findings.append(dict(kind="edge-dangling",
                                     detail="edge %s->%s has no node %r"
                                            % (e.get("from"), e.get("to"), e.get(end))))
    touched = {e.get(end) for e in graph.get("edges", []) for end in ("from", "to")}
    for n in graph.get("nodes", []):
        s, k = n.get("shape"), n["kind"]
        # initial and final are a disc and a ring: the region measured is the
        # annulus inside the ring, so its outline says nothing about the node's
        # kind and comparing them raises a conflict that is not one.
        if s in ok_for and k not in ok_for[s] and k not in ("initial", "final"):
            findings.append(dict(kind="shape-kind-conflict", x=n["x"], y=n["y"],
                                 w=n["w"], h=n["h"],
                                 detail="%s is drawn as %s but typed %s" % (n["id"], s, k)))
        # a note is an annotation; UBL anchors it with a dashed leader the
        # extractor does not recover as an edge, so having none is normal
        if k == "note":
            continue
        if n["id"] not in touched:
            findings.append(dict(kind="node-isolated", x=n["x"], y=n["y"],
                                 w=n["w"], h=n["h"],
                                 detail="%s (%s %r) has no edge" % (n["id"], k, n.get("label", "")[:20])))


def verify(orig_png, render_png, graph_path, radius=3, diff_out=None):
    graph = json.load(open(graph_path))
    a, bg_orig = ink_of(orig_png)
    b, bg_render = ink_of(render_png)
    if a.shape != b.shape:
        return dict(verdict="improvable", name=graph_path,
                    findings=[dict(kind="size-mismatch", detail="original %s, render %s"
                                   % (a.shape[::-1], b.shape[::-1]))], human=[], text=[])

    # Text is masked out of the line-work comparison on BOTH sides, found by OCR in
    # each image independently. Masking only the original's text leaves every glyph
    # the SVG drew a little outside that box counted as line-work: measured over the
    # 78 diagrams, the median such "line-work" cluster was 0.95 of a glyph height -
    # one letter - and they were about half of all residual ink. The numbers were
    # partly measuring type.
    #
    # Reading the render's text from its pixels rather than from the model keeps
    # this ungameable: a model cannot widen the mask by *claiming* text, only by
    # actually drawing it, and text it draws where the original has none is caught
    # by the text-completeness clause, which compares against the original.
    boxes = text_boxes(bg_orig)
    tmask = mask_text(a.shape, boxes + text_boxes(bg_render),
                      graph.get("fontPx") or 12)
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

    # ---- the five clauses of structural completeness -----------------------
    glyph_h = max(8.0, float(graph.get("fontPx") or 0) * 0.7 or 12.0)
    lost = [dict(f, kind="element-absent",
                 detail="nothing is drawn here: " + attribute(f, graph))
            for f in structural(missing, lb, glyph_h)]                    # clause 1
    made = [dict(f, kind="element-invented",
                 detail="drawn where the original has nothing: " + attribute(f, graph))
            for f in structural(extra, la, glyph_h)]                      # clause 2
    check_text_complete(bg_orig, graph, boxes, text_findings, glyph_h)    # clause 3
    coherence = []
    check_coherent(graph, glyph_h, coherence)                             # clause 4
    check_arrow_directions(a, b, graph, glyph_h, coherence)               # clause 4b
    blocking = lost + made + coherence + \
        [t for t in text_findings if t["kind"] in ("text-absent", "text-differs",
                                                   "label-missing")]

    if diff_out:
        out = np.full(a.shape + (3,), 255, np.uint8)
        out[missing] = (212, 0, 0)
        out[extra] = (0, 96, 208)
        Image.fromarray(out).save(diff_out)

    if blocking:
        verdict = "improvable"
    elif human:                                                           # clause 5
        verdict = "needs-human"
    else:
        verdict = "correct"
    return dict(name=graph.get("source", graph_path), verdict=verdict, radius=radius,
                lineWorkInk=int(la.sum()),
                missingPx=int(missing.sum()), inventedPx=int(extra.sum()),
                structural=dict(absent=len(lost), invented=len(made),
                                coherence=len(coherence),
                                textAbsent=sum(1 for t in text_findings
                                               if t["kind"] == "text-absent"),
                                textDiffers=sum(1 for t in text_findings
                                                if t["kind"] == "text-differs")),
                blocking=blocking, findings=findings, text=text_findings,
                coherence=coherence, human=human)


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
    s = rep.get("structural") or {}
    if s:
        print("  structural: %d element(s) absent, %d invented, %d text absent, "
              "%d text differs, %d incoherent"
              % (s.get("absent", 0), s.get("invented", 0), s.get("textAbsent", 0),
                 s.get("textDiffers", 0), s.get("coherence", 0)))
        for f in (rep.get("blocking") or [])[:10]:
            where = (" at %5d,%-5d %4dx%-4d" % (f["x"], f["y"], f["w"], f["h"])) \
                if "x" in f else ""
            print("    %-20s%s  %s" % (f["kind"], where, f.get("detail", "")[:70]))
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
