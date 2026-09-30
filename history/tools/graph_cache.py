#!/usr/bin/env python3
"""A disk cache for the extractor's reading of each PNG.

    python3 graph_cache.py get <art.png> <out-graph.json> <out-extract.log>
    python3 graph_cache.py put <art.png> <graph.json> <extract.log>

Extraction is more than half of what a sweep costs, and for most rounds of work
it does not change: correcting the model, restructuring the JSON, changing how
the SVG is drawn all start from the same reading of the same unchanging `art/`
PNGs. This keeps that reading, keyed on everything it depends on:

  - the PNG's bytes
  - the extractor's own code (extract_graph.py, ocr_cache.py)
  - the fixtures it reads (reading-lexicon.json, direction-verdicts.json)
  - the tesseract version, and the versions of numpy, scipy and Pillow

so that changing any of them misses and the PNG is read again. Nothing is
approximated: a hit returns the very bytes a fresh extraction wrote, and the
extractor is deterministic (a cold and a warm run were compared byte for byte in
the reproduction test, docs/artwork-conversion-notes.md section 13).

`get` exits 0 on a hit and 1 on a miss. Set UBL_GRAPH_CACHE to choose where it
lives (default ~/.cache/ubl-graph), and UBL_NO_GRAPH_CACHE=1 to bypass it.
"""
import hashlib
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.environ.get(
    "UBL_GRAPH_CACHE", os.path.join(os.path.expanduser("~"), ".cache", "ubl-graph"))
# everything in this directory the extractor reads; add to it when that changes
DEPENDS = ("extract_graph.py", "ocr_cache.py", "reading-lexicon.json",
           "direction-verdicts.json")

_env = None


def environment():
    """what outside this repository decides the reading: tesseract and the
    numeric libraries"""
    global _env
    if _env is None:
        try:
            tv = subprocess.run(["tesseract", "--version"], capture_output=True,
                                text=True).stdout + ""
        except OSError:
            tv = "no tesseract"
        import numpy, scipy, PIL
        _env = "%s|numpy %s|scipy %s|Pillow %s" % (tv.strip(), numpy.__version__,
                                                  scipy.__version__, PIL.__version__)
    return _env


def key(png):
    h = hashlib.sha1(b"graph-cache v1\x00")
    for p in [png] + [os.path.join(HERE, d) for d in DEPENDS]:
        h.update(os.path.basename(p).encode() + b"\x00")
        with open(p, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
    h.update(environment().encode())
    return h.hexdigest()


def main(argv):
    if len(argv) != 4 or argv[0] not in ("get", "put"):
        print(__doc__)
        return 2
    if os.environ.get("UBL_NO_GRAPH_CACHE"):
        return 1 if argv[0] == "get" else 0
    op, png, graph, log = argv
    k = key(png)
    slot = os.path.join(CACHE_DIR, k)
    if op == "get":
        try:
            shutil.copyfile(slot + "-graph.json", graph)
            shutil.copyfile(slot + "-extract.log", log)
            return 0
        except OSError:
            return 1
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        for src, suffix in ((graph, "-graph.json"), (log, "-extract.log")):
            tmp = "%s%s.tmp%d" % (slot, suffix, os.getpid())
            shutil.copyfile(src, tmp)
            os.replace(tmp, slot + suffix)
    except OSError:
        pass                  # a cache that cannot be written is not an error
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
