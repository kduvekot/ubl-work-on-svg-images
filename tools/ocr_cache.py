#!/usr/bin/env python3
"""A disk cache for page-level OCR.

Reading a 3425px page with tesseract costs seconds, and both the extractor and
the verifier do it on every run - on the *same* unchanging `art/` PNGs, sweep
after sweep. Measured over the 78 UML diagrams, that OCR was most of the ~14s
each diagram took, while the whole render-and-diff chain was under 2s.

The cache is keyed on the file's *contents* and the tesseract configuration, so
editing a file misses and it is read again, while a file merely rewritten
unchanged - which is what a re-rendered SVG usually is - still hits. Nothing is
approximated: the cached value is exactly what `image_to_data` returned, so a run
against a warm cache produces byte-identical results to a cold one.

Set UBL_OCR_CACHE to choose where it lives; the default is under ~/.cache, so it
survives between sweeps, never lands in the repository, and can be deleted at any
time at the cost of one slow run.
"""
import hashlib
import json
import os

CACHE_DIR = os.environ.get(
    "UBL_OCR_CACHE", os.path.join(os.path.expanduser("~"), ".cache", "ubl-ocr"))

# Tesseract parallelises a single page with OpenMP, and OpenMP busy-waits. One
# page per core is the useful parallelism here, not one page across all cores, and
# with several pages in flight the spinning threads fight each other: measured,
# three concurrent reads of one diagram took fifteen seconds each where one alone
# took a quarter of a second. Importing this module pins tesseract to one thread,
# which costs a serial run nothing and makes a parallel sweep possible.
os.environ.setdefault("OMP_THREAD_LIMIT", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")


def _key(path, config):
    """Content hash of the file, plus the configuration it would be read with.

    Hashing the bytes costs milliseconds against the seconds tesseract costs, and
    it buys correctness in both directions: a touched-but-unchanged file still
    hits, and an edited one cannot hit a stale entry however the timestamps fall."""
    # "v2" marks what the entry holds: every box tesseract returned, with the
    # confidence floor applied on the way out rather than on the way in. Entries
    # written before that were filtered before they were stored, so they cannot be
    # told apart from a page that genuinely has no faint marks on it.
    h = hashlib.sha1(("v2\x00" + config).encode("utf-8"))
    try:
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
    except OSError:
        return None
    return h.hexdigest()


def word_boxes(image, path=None, config="--psm 11", min_conf=30):
    """[(left, top, width, height, text, conf), ...] for one page.

    `path` is the file the image came from and is what makes the result
    cacheable; without it the OCR still runs, just uncached.

    The cache is keyed on the page and the tesseract configuration, and not on
    `min_conf` - so the floor is applied to what comes back, never to what goes
    in. Filtering first made the entry depend on whichever caller happened to
    write it: `glyph_height` asks for a word it can trust and was handed a list
    built for someone else, which on CPFR-EstablishingCollaborativeRelationships
    meant eighty-odd readings of its dashed phase boxes carrying the median down
    to 4px against type that measures 33. Every size derived from that collapsed
    with it."""
    key = _key(path, config) if path else None
    if key:
        hit = os.path.join(CACHE_DIR, key + ".json")
        try:
            with open(hit) as fh:
                return [tuple(r) for r in json.load(fh)
                        if float(r[5]) >= min_conf]
        except (OSError, ValueError):
            pass

    import pytesseract
    d = pytesseract.image_to_data(image, config=config,
                                  output_type=pytesseract.Output.DICT)
    out = []
    for i, txt in enumerate(d["text"]):
        try:
            conf = float(d["conf"][i])
        except (TypeError, ValueError):
            continue
        if txt.strip():
            out.append((int(d["left"][i]), int(d["top"][i]), int(d["width"][i]),
                        int(d["height"][i]), txt, conf))

    if key:
        try:
            os.makedirs(CACHE_DIR, exist_ok=True)
            tmp = os.path.join(CACHE_DIR, key + ".tmp%d" % os.getpid())
            with open(tmp, "w") as fh:
                json.dump(out, fh)
            os.replace(tmp, os.path.join(CACHE_DIR, key + ".json"))
        except OSError:
            pass          # a cache that cannot be written is not an error
    return [r for r in out if r[5] >= min_conf]
