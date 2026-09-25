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
import os
import re
import sys

import numpy as np
import scipy.ndimage as ndi
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ocr_cache

Image.MAX_IMAGE_PIXELS = None

MIN_FINDING_AREA = 60      # ignore specks: anti-aliasing crumbs, single stray pixels
TEXT_PAD = 0.35            # pad text boxes by this fraction of the font size
OCR_MATCH = 0.90           # difflib ratio above which a label reads back as correct
TEXT_CONF = 55             # below this, tesseract is reading line-work, not words


def ink_of(path):
    im = Image.open(path)
    bg = Image.new("RGB", im.size, "white")
    bg.paste(im, mask=im.split()[-1] if im.mode in ("RGBA", "LA") else None)
    return np.asarray(bg.convert("L")) < 128, bg


def text_boxes(bg_original, min_conf=30, path=None):
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
        # Two passes, because one is not enough: "sparse text" (psm 11) is the right
        # model for labels scattered over a diagram, but it misses whole lines of
        # large bold type - on Tender-ContractInfoNotify it found 10 words where the
        # block reader (psm 6) found 23, and every word it missed was then counted
        # as line-work the SVG had failed to reproduce. The union of the two is what
        # the page says; the confidence floor still decides what is a word.
        words = list(ocr_cache.word_boxes(bg_original, path=path, config="--psm 11",
                                          min_conf=min_conf))
        seen = {(x, y, w, h) for x, y, w, h, _, _ in words}
        for it in ocr_cache.word_boxes(bg_original, path=path, config="--psm 6",
                                       min_conf=min_conf):
            if it[:4] not in seen:
                words.append(it)
    except ImportError:
        return []
    return [(x, y, w, h, "text %r" % t.strip()[:24], c) for x, y, w, h, t, c in words]


def mask_text(shape, boxes, font_px):
    """True where text lives, padded so glyph overshoot and descenders are covered"""
    m = np.zeros(shape, bool)
    pad = max(4, int(TEXT_PAD * max(font_px, 8)))
    H, W = shape
    for x, y, w, h, *_ in boxes:
        m[max(0, y - pad):min(H, y + h + pad), max(0, x - pad):min(W, x + w + pad)] = True
    return m


def near(mask, radius):
    """dilate by a square of the given radius - 'is there ink within r pixels'

    A square is separable, and a maximum filter exploits that while a dilation
    against an explicit k x k footprint does not: the results are identical
    (checked pixel for pixel on the artwork), but at the span the structural test
    uses this is two hundredths of a second instead of two seconds, and it ran
    four times per diagram."""
    return ndi.maximum_filter(mask, size=2 * radius + 1, mode="constant")


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
        got = norm(ocr_cache.image_to_string(crop, config="--psm 6"))
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


def _flat(s):
    """the letters and digits of a reading, in order - no case, no spaces, no
    punctuation: what the ink says, with how it was divided into words set aside"""
    return re.sub(r"[^0-9a-z]", "", (s or "").lower())


def check_text_complete(bg_orig, graph, boxes, findings, glyph_h, orig_ink=None):
    """Every word the original shows must be somewhere in the model, saying the
    same thing, in the same place. Read off the original, so the model cannot
    grade its own homework by simply not extracting a label."""
    import difflib
    heads = [tuple(e["toPoint"]) for e in graph.get("edges", []) if e.get("toPoint")]
    heads += [tuple(e["fromPoint"]) for e in graph.get("edges", [])
              if e.get("fromPoint") and e.get("arrowBoth")]
    placed = []
    for n in graph.get("nodes", []):
        lines = n.get("labelLines") or []
        if not lines and (n.get("label") or "").strip():
            # a label the extractor could not split into its lines is still a
            # label, and the rebuild still draws it - centred in the node's own
            # box. Counting it as absent said every decision diamond's words were
            # missing from diagrams that draw them plainly inside it.
            lines = [dict(x=n["x"], y=n["y"], w=n["w"], h=n["h"],
                          text=" ".join(n["label"].split()))]
        for ln in lines:
            placed.append((ln, ln.get("text", ""), "label of %s" % n["id"]))
    for t in graph.get("text", []):
        for ln in t.get("lines") or [t]:
            placed.append((ln, ln.get("text", ""), "text block"))
    for p in graph.get("partitions", []):
        b = p.get("titleBox")
        if b:
            placed.append((dict(x=b[0], y=b[1], w=b[2], h=b[3]), p.get("title", ""),
                           "title of %s %s" % (p.get("axis"), p.get("index"))))
    for x, y, w, h, label, conf in boxes:
        # A word the referee is not sure it read is not evidence of anything. The
        # dashed dividers of CPFR-EstablishingCollaborativeRelationships read as
        # "ee" 84 times, at confidence 31-49, and those 84 phantom words were a
        # third of every missing label counted across the 78 diagrams. Real words
        # on this artwork come back at 59 and above. The mask still covers the
        # low-confidence boxes - masking generously costs nothing and hides no
        # line-work defect, since the mask is built from the original either way.
        if conf < TEXT_CONF:
            continue
        want = norm(label[6:].strip("'\"") if label.startswith("text ") else label)
        # tesseract boxes are per word, the model holds whole lines, so the test is
        # whether the word appears in the line covering it - not whether the word
        # equals the line. Single marks are OCR reading the line-work ("|" off a
        # divider) and are not text at all.
        if len(re.sub(r"[^0-9A-Za-z]", "", want)) < 2:
            continue
        # Tesseract is confident about shapes that are not letters, and on this
        # artwork it names line-work: the solid arrowhead into "Application
        # response" on the Import and Transit declaration diagrams comes back as
        # 'mM' at 75, and the folded corner of a note on IMFM-Intermodal as 'IN'
        # at 93 and 78. Four of the twelve differences left in the set are that,
        # every one of them against a drawing with nothing wrong with it. The ink
        # settles it, by the same test the extractor uses on its own blocks and
        # read off the original alone: a word is a row of small marks, a stroke of
        # line-work is one long thin one.
        if orig_ink is not None:
            import extract_graph as _E
            if _E.line_like(orig_ink, dict(x=x, y=y, w=w, h=h),
                            graph.get("fontPx") or glyph_h):
                continue
        # line_like above catches a stroke read as letters, by its shape. It cannot
        # catch a solid arrowhead, which is a blob and not a stroke: the head beside
        # "Application response" on the Import and Transit declarations comes back
        # as 'mM' at 75, the folded note corner on FulfilmentReceiptAdvice as 'ZT',
        # the head on CPFR-ExceptionMonitor as 'Ft'. Four of the differences left in
        # the set, every one against a drawing with nothing wrong with it.
        #
        # Shape will not separate those from words - measured over the 78, real text
        # runs to 9.7 type heights in one connected component where the head is 2.0,
        # and to 0.53 of a type height thick where the head is 0.18, because the
        # reversed lane titles are heavier than any arrowhead. What does separate
        # them is that the model already knows where it put each head. A reading
        # whose box encloses one is that head read as letters.
        #
        # The head has to fall inside the box, not merely near it: these boxes reach
        # along the shaft, so their centres sit well off the head, and a tolerance
        # wide enough to reach from the centre also swallows the guard labels that
        # sit at the same node boundaries - nine of them across the 78, "No" and
        # "Resolve" among them. Enclosure needs no tolerance at all.
        if any(x <= hx <= x + w and y <= hy <= y + h for hx, hy in heads):
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
        if any(difflib.SequenceMatcher(None, want.lower(), t.lower()).ratio() >= 0.8
               for t in tokens):
            continue

        # The reading itself has to be worth believing before it can accuse the
        # model, and on this artwork it often is not: tesseract reads the same ink
        # twice over, in overlapping boxes, and the confidence floor then keeps the
        # pieces and drops the whole. "Receive tender withdrawal request" comes
        # back as 'tend' at 96, 'ithd' at 92, 'wi' at 65 and 'rawal' at 74, with
        # the correct 'tender' at 36 below the floor - four boxes over one line,
        # three of which matched no whole word of a label that is right, and so
        # three text errors against a model with nothing wrong with it. Of the 36
        # differences reported over the 78 diagrams, 19 are this.
        #
        # Two ways a reading stops being evidence, both saying the same thing -
        # that the ink here is already accounted for.
        #
        # One: the model's line does contain it, once the word division is set
        # aside. A reading that is a run of characters inside the line is a piece
        # of a word the line has in full, or two of its words run together where
        # the space was missed - 'rawal' inside "withdrawal", 'tf' across
        # "request for". The cost of setting the division aside is that a label
        # split where the original joins it - "Way bill" for "Waybill" - reads as
        # correct here; that is a deviation in the division and not in the words,
        # and the letters are all present and in order.
        flat, line_flat = _flat(want), _flat(" ".join(t for t, _ in hits))
        if flat and flat in line_flat:
            continue

        # Two: another reading covering the same ink does match. Boxes overlap
        # only where they read the same glyphs, so two of them are one thing read
        # twice, and if either reading is the model's the ink is accounted for -
        # 'tor' over the 'for' that the other pass read at 96, 'raise' over a
        # 'False' read at 96 against its own 59.
        rival = False
        for bx, by, bw, bh, blabel, bconf in boxes:
            if (bx, by, bw, bh) == (x, y, w, h):
                continue
            if bx + bw <= x or bx >= x + w or by + bh <= y or by >= y + h:
                continue
            other = norm(blabel[6:].strip("'\"") if blabel.startswith("text ")
                         else blabel)
            if any(difflib.SequenceMatcher(None, other.lower(), t.lower()).ratio() >= 0.8
                   for t in tokens):
                rival = True
                break
        if rival:
            continue

        findings.append(dict(kind="text-differs", x=x, y=y, w=w, h=h, expected=want,
                             got=norm(hit[0]),
                             detail="original says %r, model has %r (%s)"
                                    % (want[:24], norm(hit[0])[:30], hit[1])))


def check_arrowheads(a, b, graph, glyph_h, findings, nodefill, human):
    """Is there an arrowhead where the artwork has one.

    Comparing ink between the two images says nothing on its own: the artwork's
    solid triangles carry several times the ink of the open "V" the rebuild draws,
    at every arrow, right or wrong. So measure the head itself, the same way at the
    same place in both - the stretch behind the tip where the connector is wider
    than its own line - and report only where the original has one and the SVG has
    nothing. That is the defect a pixel difference cannot raise: a head is smaller
    than the "element-sized" floor the structural test uses, so a connector drawn
    without its point scores as clean."""
    import extract_graph as E
    for e in graph.get("edges", []):
        p, q = e.get("fromPoint"), e.get("toPoint")
        if not p or not q:
            continue
        back = (e.get("points") or [p])[-1]
        st = max(2.0, 0.1 * (graph.get("fontPx") or 40))
        reach = ((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2) ** 0.5
        xs, ys = E.corridor(a, nodefill, p, q, int(max(40, 10 * st)))
        if xs.size < 8:
            continue
        head = E.arrow_size(xs, ys, q, back, st, reach,
                            min_len=0.35 * (graph.get("fontPx") or 40),
                            ahead=int(max(10, 8 * st)))
        if not head:
            continue                       # nothing measurable in the original

        # How much ink each image puts where the head is. Measuring the *shape* of
        # the rendered head the same way fails on the drawing rather than on the
        # defect: the head's point sits a few pixels past the contact the model
        # recorded, the cone that keeps a crossing line out of the measurement then
        # cuts the head's own pixels, and a head that is plainly there measures as
        # absent. Mass in a fixed region does not care where exactly the point
        # lands - and the region is the head's own triangle, not a disc around it,
        # because a disc is mostly connector: at the sizes these diagrams draw, the
        # line through it carried more ink than the head did, and the reading then
        # said as much about the head's proportions as about whether it was there.
        L, Wd, front = head[0], head[1], head[3]
        # ...but only where what was read is a head at all, judged against the
        # head this diagram draws rather than against the reading's own
        # proportions: this probe reads a real head short as often as not, so a
        # third of the set measures wider than it is long without anything being
        # wrong. Too wide for the diagram's own arrowhead is the test, at the
        # 1.6 the extractor already settles the same question at - where two real
        # heads at both ends of a flow measure 1.01 and 1.04 times their diagram's
        # head across and a junction measures 3.2.
        #
        # Where two flows meet an end event side by side, as the two "No" flows do
        # on CPFR-ExceptionMonitor, the probe reads one head as 72 by 170 against
        # that diagram's own 62 by 50, and a wedge that wide takes in the
        # neighbouring head and both guard labels on the original while taking in
        # only the one head on the rebuild. The comparison is then between two
        # different things, so it is not made; a person is told instead, because
        # whether a head is drawn here is exactly what this test cannot see.
        own_w = graph.get("arrowWidthPx") or 0
        if own_w and Wd > 1.6 * own_w:
            human.append(dict(kind="arrowhead-unmeasurable", x=int(q[0] - L),
                              y=int(q[1] - L), w=int(2 * L), h=int(2 * L),
                              reason="the ink at the head end of %s->%s measures"
                                     " %.0fx%.0fpx, too wide for this diagram's own"
                                     " %.0fpx arrowhead - a junction, not a head"
                                     % (e.get("from"), e.get("to"), L, Wd, own_w),
                              check="confirm the arrowhead here is drawn and points"
                                    " the way the original does"))
            continue
        dx, dy = q[0] - back[0], q[1] - back[1]
        dL = (dx * dx + dy * dy) ** 0.5 or 1.0
        dx, dy = dx / dL, dy / dL
        apex = (q[0] + dx * front, q[1] + dy * front)
        mask, (y0, y1, x0, x1) = E.wedge(a.shape, apex, dx, dy, L, Wd,
                                         inner=max(st / 2.0, 1.0) + 1.5, outer=L)
        if mask is None or mask.sum() < 12:
            continue
        m = mask & ~nodefill[y0:y1, x0:x1]
        m_orig = int((a[y0:y1, x0:x1] & m).sum())
        m_rend = int((b[y0:y1, x0:x1] & m).sum())
        # Calibrated against a control: the same renders with every marker-end
        # stripped out, on a filled-head diagram and on two open-head ones. Where
        # the head is drawn the rebuild keeps 0.43 to 1.7 of the original's ink
        # here; where the marker was taken away it keeps at most 0.4, and 0.0 at
        # the median. The floor sits at the bottom of the first range rather than
        # in the gap: this reports heads that are absent, and a head drawn a little
        # too small is the pixel difference's to report, not this test's.
        if m_orig >= 40 and m_rend < 0.4 * m_orig:
            findings.append(dict(kind="arrowhead-missing", x=x0, y=y0,
                                 w=x1 - x0, h=y1 - y0,
                                 detail="edge %s->%s: the original has a %.0fpx arrowhead"
                                        " here (%d px of ink); the SVG has %d"
                                        % (e.get("from"), e.get("to"), head[0],
                                           m_orig, m_rend)))


def check_arrow_directions(a, b, graph, glyph_h, findings, tmask=None, ratio=2.0):
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
    # A node's own outline is inside the probe at both ends, and the two images
    # draw it at different weights - the original's object boxes are heavy, the
    # SVG's are lighter - so the border, not the arrowhead, decided which end
    # "had more ink" and edges drawn the right way round were reported reversed.
    # Leave the node boxes out of both measurements; an arrowhead sits outside the
    # box it points at.
    inside = np.zeros(a.shape, bool)
    pad = 8          # the SVG draws a box's stroke centred on a slightly larger
                     # rectangle, so a few pixels of its border fall outside the
                     # measured bbox - enough, on a 48px connector, to outweigh
                     # the arrowhead at the other end
    for n in graph.get("nodes", []):
        inside[max(0, n["y"] - pad):n["y"] + n["h"] + pad,
               max(0, n["x"] - pad):n["x"] + n["w"] + pad] = True
    # and the labels with them: a guard set beside the tail of a short connector
    # outweighs the head at its other end, and the two images do not put a label
    # in quite the same place
    if tmask is not None:
        inside |= tmask

    def mass(img, p, r):
        y0, y1 = max(0, p[1] - r), min(H, p[1] + r)
        x0, x1 = max(0, p[0] - r), min(W, p[0] + r)
        return int((img[y0:y1, x0:x1] & ~inside[y0:y1, x0:x1]).sum())

    for e in graph.get("edges", []):
        p, q = e.get("fromPoint"), e.get("toPoint")
        if not p or not q:
            continue
        # The two probes must not overlap, or both of them measure both ends and
        # the answer is whichever node border happens to be nearer. A 55px
        # connector between two boxes was read as reversed for exactly that
        # reason, in a diagram where the SVG draws it the right way round.
        span = ((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2) ** 0.5
        r = int(min(max(20, 2.0 * glyph_h), 0.4 * span))
        if r < 12:
            continue

        def head(img, r=r):
            f, t = mass(img, p, r), mass(img, q, r)
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


def check_coherent(graph, glyph_h, findings, missing=None, human=None):
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
            # A node with nothing attached is usually a connector the model lost,
            # and then the pixels say so: the line the artwork draws into it is
            # missing from the rebuild, right there at its edge. Where nothing is
            # missing, nothing was lost - the artwork itself draws the element with
            # no connector on it, as UBL does with the Awarded and Unawarded
            # Notification on Tender-AwardNotification, where the one flow runs
            # straight past both documents. That is the drawing's fault and not the
            # reading's, so it goes to a person rather than counting as incoherent.
            # The reach is the diagram's own arrowhead length, the scale at which a
            # connector meets a node, and not a number chosen here.
            reach = int(max(4.0, float(graph.get("arrowPx") or 0) or glyph_h))
            lost = None
            if missing is not None:
                y0, y1 = max(0, n["y"] - reach), n["y"] + n["h"] + reach
                x0, x1 = max(0, n["x"] - reach), n["x"] + n["w"] + reach
                lost = bool(missing[y0:y1, x0:x1].any())
            if lost is False:
                if human is not None:
                    human.append(dict(
                        kind="node-isolated-in-the-artwork", x=n["x"], y=n["y"],
                        w=n["w"], h=n["h"],
                        reason="%s (%s %r) has no flow on it, and no line-work is"
                               " missing around it, so the original draws it that"
                               " way too" % (n["id"], k, n.get("label", "")[:20]),
                        check="confirm against the artwork that nothing connects"
                              " to this element"))
                continue
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
    boxes = text_boxes(bg_orig, path=orig_png)
    tmask = mask_text(a.shape, boxes + text_boxes(bg_render, path=render_png),
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
    check_text_complete(bg_orig, graph, boxes, text_findings, glyph_h, a)  # clause 3
    coherence = []
    check_coherent(graph, glyph_h, coherence, missing, human)            # clause 4
    check_arrow_directions(a, b, graph, glyph_h, coherence, tmask)
    nodefill = np.zeros(a.shape, bool)
    for n in graph.get("nodes", []):
        nodefill[max(0, n["y"] - 2):n["y"] + n["h"] + 3,
                 max(0, n["x"] - 2):n["x"] + n["w"] + 3] = True
    check_arrowheads(a, b, graph, glyph_h, coherence, nodefill, human)        # clause 4b
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
