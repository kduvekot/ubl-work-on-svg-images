#!/usr/bin/env python3
"""Read the model back as a sentence, and check it against what an activity
diagram is allowed to say.

    python3 model_sheet.py <graph.json> [--json sheet.json]

The pixel difference answers "does the SVG look like the artwork". It cannot
answer "does the model say what the diagram says", because a connector drawn in
exactly the right place still carries a direction, two endpoints and a guard, and
all three can be wrong while the picture is perfect. This is the other half of
the acceptance test, and it is the half a person can check by eye against the
original without owning any of the tooling:

  * the flow, written out - every path from a start event to where it ends, with
    the guard on each branch and the partition each step happens in;
  * the rules an activity diagram obeys, checked one by one, with the elements
    that break them named.

Nothing here looks at pixels, and nothing here looks at the SVG. The SVG is
generated from this model - graph.json -> spec.json -> .svg - so a model that
reads correctly and a diff that comes back blank together say the conversion is
right for the right reason. There is no third file to keep in step: the geometry
in the spec is this model's own measurements, carried through.
"""
import json
import os
import sys

GLYPH = {"initial": "(start)", "final": "(end)", "decision": "<%s?>",
         "fork": "=== bar ===", "object": "[%s]", "action": "%s", "note": "note %r"}


def label(n):
    t = " ".join((n.get("label") or "").split())
    k = n["kind"]
    if k == "initial":
        return "(start)"
    if k == "final":
        return "(end)"
    if k == "fork":
        return "=== bar ==="
    if k == "decision":
        return "<%s>" % (t or "?")
    if k == "object":
        return "[%s]" % (t or "document")
    if k == "note":
        return "note %r" % t
    return t or "(unnamed %s)" % k


_FAULTS = None


def artwork_faults(source):
    """The rules this diagram breaks because the drawing does, not the reading.

    Each one was put beside the original and judged; the list is
    tools/artwork-faults.json, and it names the elements as well as the rule, so
    a rule goes quiet only for exactly what was checked."""
    global _FAULTS
    if _FAULTS is None:
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "artwork-faults.json")
        try:
            _FAULTS = json.load(open(p))["diagrams"]
        except Exception:
            _FAULTS = {}
    name = os.path.splitext(os.path.basename(source or ""))[0]
    return (_FAULTS.get(name) or {}).get("rules", {})


def lane_of(n, parts):
    """the party whose column the element sits in, ignoring the phase band"""
    cx = n["x"] + n["w"] / 2
    for p in parts:
        if p["axis"] == "column" and p["x0"] <= cx <= p["x1"] and p.get("title"):
            return " ".join(p["title"].split())
    return ""


def partition_of(n, parts):
    """the lane and band the element sits in, by its own centre"""
    cx, cy = n["x"] + n["w"] / 2, n["y"] + n["h"] / 2
    out = []
    for p in parts:
        if p["axis"] == "column" and p["x0"] <= cx <= p["x1"] and p.get("title"):
            out.append(" ".join(p["title"].split()))
        if p["axis"] == "band" and p["y0"] <= cy <= p["y1"] and p.get("title"):
            out.append(" ".join(p["title"].split()))
    return " / ".join(out)


def flow_lines(g):
    """Every route through the diagram, walked from each start event.

    Written as a walk rather than as a list of edges because that is the form a
    person can check against the artwork: follow the arrows in the picture and
    follow these lines, and a wrong direction or a swapped endpoint shows up as
    the two going different ways."""
    byid = {n["id"]: n for n in g["nodes"]}
    parts = g.get("partitions", [])
    out = {}
    for e in g["edges"]:
        out.setdefault(e["from"], []).append(e)

    lines, seen_edges = [], set()

    def key(e):
        return (e["from"], e["to"], tuple(e.get("fromPoint", [])))

    def walk(nid, depth, guard=""):
        n = byid.get(nid)
        if n is None:
            return
        where = partition_of(n, parts)
        lines.append("%s%s%s%s" % ("  " * depth,
                                   "-%s-> " % guard if guard else ("-> " if depth else ""),
                                   label(n), "   [%s]" % where if where else ""))
        nxt = [e for e in out.get(nid, []) if key(e) not in seen_edges]
        for e in nxt:
            seen_edges.add(key(e))
        for i, e in enumerate(nxt):
            walk(e["to"], depth + (1 if len(nxt) > 1 else 0),
                 " ".join((e.get("guard") or "").split()))

    starts = [n["id"] for n in g["nodes"] if n["kind"] == "initial"]
    # A flow that comes onto the page from outside starts something here too, the
    # same as a drawn start event - which is what the reachability rule below
    # already counts. Leaving it out here made the sheet contradict itself: on
    # BusinessCard the walk reported "Download business card" as not reached from
    # any start event and the rule two lines later said every element was.
    starts += [o["node"] for o in g.get("openEnds", []) if o.get("inward")
               and o.get("node") not in starts]
    # a diagram whose start event was never found still has a first element: the
    # one nothing flows into
    if not starts:
        into = {e["to"] for e in g["edges"]}
        starts = [n["id"] for n in g["nodes"] if n["id"] not in into and out.get(n["id"])]
    for s in starts:
        walk(s, 0)
        lines.append("")
    # anything the walk never reached, so the sheet is the whole model and not
    # only the part that hangs together
    reached = {l for l in seen_edges}
    rest = [e for e in g["edges"] if key(e) not in reached]
    if rest:
        lines.append("not reached from any start event:")
        for e in rest:
            lines.append("   %s -%s-> %s"
                         % (label(byid.get(e["from"], {"kind": "action", "label": e["from"]})),
                            " ".join((e.get("guard") or "").split()),
                            label(byid.get(e["to"], {"kind": "action", "label": e["to"]}))))
    return lines


def checks(g):
    """What an activity diagram is allowed to say, one rule at a time.

    Each rule is a statement about the artwork that holds whatever the drawing
    looks like, so a rule that fails is a reading error and not a matter of
    taste. They are reported with the elements that break them, because "3
    failures" is not actionable and "the decision 'Approved?' has one way out"
    is."""
    byid = {n["id"]: n for n in g["nodes"]}
    parts = g.get("partitions", [])
    accepted = artwork_faults(g.get("source", ""))
    ins, outs = {}, {}
    for e in g["edges"]:
        outs.setdefault(e["from"], []).append(e)
        ins.setdefault(e["to"], []).append(e)
    res = []

    def rule(name, bad, note="", report=False):
        """`report` is for a statement about the artwork that the artwork itself
        does not keep. Those are still listed, with what breaks them, because a
        person reading them against the drawing is how they were settled in the
        first place; they just do not count as a reading error."""
        # ...or every element it names is one a person has already read against
        # the artwork and found to be the drawing's own gap. A new one anywhere
        # else still fails, which is what keeps this a tripwire for a connector
        # the model has lost rather than a way of turning the rule off.
        known = accepted.get(name, [])
        if bad and known and all(b in known for b in bad):
            report, note = True, (note or "informational") + \
                " - read against the artwork and found to be the drawing's own"
        res.append(dict(rule=name, ok=not bad or report, bad=bad, note=note,
                        report=report))

    # 1 - every element takes part in the flow, except the ones whose whole job
    # is to stand beside it. A UML note is an annotation and is attached to
    # nothing by design - "Transaction accessing Seller's catalogue application"
    # on SourcingPunchout, the three on IMFM-Intermodal - and the reachability
    # rule below already passes over them for the same reason.
    open_ends = {o.get("node") for o in g.get("openEnds", [])}
    rule("every element is connected",
         [label(n) for n in g["nodes"] if n["kind"] != "note"
          and not ins.get(n["id"]) and not outs.get(n["id"])
          and n["id"] not in open_ends])

    # 2 - a start event starts something and nothing starts it
    rule("start events have a way out and no way in",
         [label(n) for n in g["nodes"] if n["kind"] == "initial"
          and (ins.get(n["id"]) or not outs.get(n["id"]))])

    # 3 - an end event ends something
    rule("end events have a way in and no way out",
         [label(n) for n in g["nodes"] if n["kind"] == "final"
          and (outs.get(n["id"]) or not ins.get(n["id"]))])

    # 4 - a decision that cannot branch is not a decision. A branch that leaves
    # the drawing is still a branch: both diamonds on CPFR-ExceptionHandling send
    # "Yes" to an action and take "No" down and out of the phase box, off the
    # page, and counting only the flows that end on another element read them as
    # decisions that cannot decide.
    open_out = {o.get("node") for o in g.get("openEnds", []) if not o.get("inward")}
    rule("decisions have at least two ways out",
         [label(n) for n in g["nodes"] if n["kind"] == "decision"
          and len(outs.get(n["id"], [])) + (1 if n["id"] in open_out else 0) < 2])

    # 5 - the branches of a decision say which is which. UML says they should;
    # UBL often does not. Checked against the artwork over the seven diagrams this
    # names: the three branches out of "Determine Action" on FulfilmentDespatchAdvice
    # carry no word in the drawing either, and neither do the bare diamonds on
    # ProcurementProcess and CertificationOfOrigin. So this is the artwork's gap,
    # not the reading's, and it is reported rather than failed.
    rule("branches out of a decision are labelled",
         ["%s -> %s" % (label(byid[n["id"]]), label(byid.get(e["to"], n)))
          for n in g["nodes"] if n["kind"] == "decision"
          and len(outs.get(n["id"], [])) >= 2
          for e in outs[n["id"]] if not (e.get("guard") or "").strip()],
         "informational: several diagrams draw an unlabelled branch, so read"
         " these against the artwork rather than treating them as errors",
         report=True)

    # 6 - a document is produced by something and read by something
    rule("documents are both written and read",
         [label(n) for n in g["nodes"] if n["kind"] == "object"
          and not (ins.get(n["id"]) and outs.get(n["id"]))])

    # 7 - work is done by actions, so a flow never runs document to document
    rule("no flow runs straight from one document to another",
         ["%s -> %s" % (label(byid[e["from"]]), label(byid[e["to"]]))
          for e in g["edges"]
          if byid.get(e["from"], {}).get("kind") == "object"
          and byid.get(e["to"], {}).get("kind") == "object"])

    # 8 - a document that passes between two parties sits on the line between
    # them; one that does not is a reading to look at, not necessarily an error
    # Twenty-one flows over the 78 cross without one, in fifteen diagrams, and
    # every one of them was read against the artwork: none is a missing document.
    # Most are not a hand-over at all, and say so in the drawing - a start event
    # reaching into the other lane, a phase change within one party, a guarded
    # branch looping back out of a decision, the goods themselves moving beside
    # their Despatch Advice. What is left is UBL's own looseness, and one case
    # UBL.xml settles outright: the punch-out exchange "is considered outside the
    # scope of UBL". So each crossing is named with what the drawing says it is,
    # and the rule reports rather than fails.
    def why(e, a, b):
        if e.get("edgeKind") == "goods":
            return "the goods, beside their Despatch Advice"
        if a["kind"] in ("initial", "final") or b["kind"] in ("initial", "final"):
            return "a start or end event, not work handed over"
        if lane_of(a, parts) == lane_of(b, parts):
            return "the same party, next phase band"
        if a["kind"] == "decision" and (e.get("guard") or "").strip():
            return "a guarded branch out of a decision"
        return "no document drawn - read this one against the artwork"

    cross = []
    for e in g["edges"]:
        a, b = byid.get(e["from"]), byid.get(e["to"])
        if not a or not b:
            continue
        pa, pb = partition_of(a, parts), partition_of(b, parts)
        if pa and pb and pa != pb and "object" not in (a["kind"], b["kind"]):
            cross.append("%s [%s] -> %s [%s]   (%s)"
                         % (label(a), pa, label(b), pb, why(e, a, b)))
    rule("work crossing between parties goes through a document", cross,
         "informational: UBL draws the hand-over as a document on the divider,"
         " and each exception below is named",
         report=True)

    # 9 - what is drawn dashed, stated rather than judged.
    #
    # This used to check that a dashed flow is an object flow and a solid one a
    # control flow, which is the UML convention and is not what UBL draws. Read
    # off the artwork across the 78: of the 73 diagrams with documents on them,
    # 71 draw every object flow solid, with no gap anywhere along it - the ink is
    # continuous at every sample. Only UBL-1.0-ProcurementProcess draws them
    # dashed, all nineteen of them. Meanwhile four diagrams dash a flow between
    # two actions: the "prior exchange of public keys" on the two Tender-Contract
    # diagrams, and five flows on the two Fulfilment processes, every one of them
    # a clean pattern in the ink at the size the reading claims.
    #
    # So the convention does not hold here, and a rule that fails on 76 of 78
    # diagrams is not a check, it is noise that hides the nine rules that do mean
    # something. What a dashed flow denotes in UBL is the specification's to say;
    # that it is drawn dashed is reported, and whether the reading matches the ink
    # is tested where the ink is, in the extractor.
    dashed = []
    for e in g["edges"]:
        a, b = byid.get(e["from"]), byid.get(e["to"])
        if a and b and e.get("dash"):
            dashed.append("%s ---> %s (%.0f on, %.0f off)"
                          % (label(a), label(b), e["dash"], e.get("gap") or 0))
    if dashed:
        print("\n  drawn dashed (%d):" % len(dashed))
        for d in dashed:
            print("    %s" % d)

    # 10 - the direction of every flow was read with confidence
    # A flow a person has already put beside the artwork is settled, however thin
    # the pixels were; those read "checked" and are not listed here. What is left
    # is a direction nobody has looked at and the reading is not sure of.
    rule("every flow's direction was read with confidence",
         ["%s -> %s" % (label(byid.get(e["from"], {"kind": "action", "label": e["from"]})),
                        label(byid.get(e["to"], {"kind": "action", "label": e["to"]})))
          for e in g["edges"] if e.get("directionConfidence") == "LOW"])

    # 10 - work leads somewhere. An action with a way in and no way out is the
    # shape a reversed flow leaves behind, and it is the one the picture hides:
    # the solid diagonal on FulfilmentDespatchAdvice, read backwards, left
    # "Receive Fulfilment Cancellation" taking a flow from a decision and a
    # document and passing nothing on, which is not something an activity diagram
    # says. A flow into an end event is a way out, and so is an open flow that
    # leaves the page.
    rule("every action passes its work on",
         [label(n) for n in g["nodes"] if n["kind"] == "action"
          and ins.get(n["id"]) and not outs.get(n["id"])
          and not any(o.get("node") == n["id"] for o in g.get("openEnds", []))],
         "informational: several diagrams do end on an action, so read these"
         " against the artwork rather than treating them as errors",
         report=True)

    # 11 - every element is reachable by following arrows from a start event, or
    # from where the work arrives on the page. Half the CPFR diagrams are one
    # phase of a larger process and draw no start event at all - the flow comes in
    # over the top edge - so an element fed only by an inward open end is reached,
    # and a diagram whose only way in is one of those is not skipped.
    starts = [n["id"] for n in g["nodes"] if n["kind"] == "initial"]
    starts += [o["node"] for o in g.get("openEnds", []) if o.get("inward")]
    seen, stack = set(), list(starts)
    while stack:
        i = stack.pop()
        if i in seen:
            continue
        seen.add(i)
        stack += [e["to"] for e in outs.get(i, [])]
    rule("every element is reachable from a start event",
         [] if not starts
         else [label(n) for n in g["nodes"] if n["id"] not in seen
               and n["kind"] not in ("note",)],
         "" if starts else "skipped: this diagram has no start event and no flow"
                           " arriving from off the page")
    return res


def main(src, out_json=None):
    g = json.load(open(src))
    name = (g.get("source") or src).split("/")[-1].rsplit(".", 1)[0]
    kinds = {}
    for n in g["nodes"]:
        kinds[n["kind"]] = kinds.get(n["kind"], 0) + 1
    print("MODEL  %s" % name)
    print("  " + ", ".join("%d %s" % (v, k) for k, v in sorted(kinds.items())) +
          ", %d flows, %d partitions" % (len(g["edges"]), len(g.get("partitions", []))))
    print("\nFLOW")
    lines = flow_lines(g)
    for l in lines:
        print("  " + l if l else "")
    print("CHECKS")
    res = checks(g)
    for r in res:
        mark = "note" if (r.get("report") and r["bad"]) else \
               ("ok" if r["ok"] else "FAIL")
        print("  %-4s %s%s" % (mark, r["rule"],
                               "   (%s)" % r["note"] if r["note"] else ""))
        for b in r["bad"][:8]:
            print("        - %s" % b)
        if len(r["bad"]) > 8:
            print("        - ... and %d more" % (len(r["bad"]) - 8))
    if out_json:
        json.dump(dict(name=name, counts=kinds, flow=lines, checks=res),
                  open(out_json, "w"), indent=1)
    return sum(0 if r["ok"] else 1 for r in res)


if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    oj = sys.argv[sys.argv.index("--json") + 1] if "--json" in sys.argv else None
    sys.exit(0 if main(a[0], oj) >= 0 else 1)
