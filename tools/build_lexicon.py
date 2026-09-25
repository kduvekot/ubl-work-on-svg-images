#!/usr/bin/env python3
"""Rebuild tools/reading-lexicon.json from a sweep's readings.

    python3 tools/build_lexicon.py <run-dir>

The lexicon is how often the 78 UML diagrams write each word, counted off the
graphs of one run and kept where a word appears at least twice. It is evidence
for settling a reading against the rest of the set, never a spell-checker:
extract_graph only ever replaces a reading with a variant of itself that differs
in characters the reader confuses and that the set writes more often. So a word
the set gets wrong everywhere stays wrong here too, and nothing outside the set's
own vocabulary can enter a label.

Tokens that are line-work read as characters are left out, by the same test
extract_graph uses.
"""
import sys, os, re, json, glob, collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extract_graph import strip_strokes


def main(run_dir, out_path):
    count = collections.Counter()
    graphs = sorted(glob.glob(os.path.join(run_dir, "*-graph.json")))
    if not graphs:
        sys.exit("no *-graph.json in %s" % run_dir)
    for p in graphs:
        g = json.load(open(p))
        said = [n.get("label", "") for n in g.get("nodes", [])]
        said += [t.get("text", "") for t in g.get("text", [])]
        said += [q.get("title", "") for q in g.get("partitions", [])]
        said += [e.get("guard") or "" for e in g.get("edges", [])]
        for s in said:
            for w in re.findall(r"[A-Za-z0-9]+", strip_strokes(s)):
                count[w] += 1
    words = {w: n for w, n in count.items() if n >= 2}
    json.dump({"_note": "how often each word is written across the %d UML diagrams,"
                        " counted off %s and kept where a word appears at least"
                        " twice. Rebuild with tools/build_lexicon.py."
                        % (len(graphs), os.path.basename(run_dir.rstrip("/"))),
               "words": dict(sorted(words.items()))},
              open(out_path, "w"), indent=1)
    print("%d words kept of %d, from %d diagrams -> %s"
          % (len(words), len(count), len(graphs), out_path))


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2
         else os.path.join(here, "reading-lexicon.json"))
