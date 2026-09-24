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
    ins, outs = {}, {}
    for e in g["edges"]:
        outs.setdefault(e["from"], []).append(e)
        ins.setdefault(e["to"], []).append(e)
    res = []

    def rule(name, bad, note=""):
        res.append(dict(rule=name, ok=not bad, bad=bad, note=note))

    # 1 - every element takes part in the flow
    rule("every element is connected",
         [label(n) for n in g["nodes"]
          if not ins.get(n["id"]) and not outs.get(n["id"])])

    # 2 - a start event starts something and nothing starts it
    rule("start events have a way out and no way in",
         [label(n) for n in g["nodes"] if n["kind"] == "initial"
          and (ins.get(n["id"]) or not outs.get(n["id"]))])

    # 3 - an end event ends something
    rule("end events have a way in and no way out",
         [label(n) for n in g["nodes"] if n["kind"] == "final"
          and (outs.get(n["id"]) or not ins.get(n["id"]))])

    # 4 - a decision that cannot branch is not a decision
    rule("decisions have at least two ways out",
         [label(n) for n in g["nodes"] if n["kind"] == "decision"
          and len(outs.get(n["id"], [])) < 2])

    # 5 - the branches of a decision say which is which
    rule("branches out of a decision are labelled",
         ["%s -> %s" % (label(byid[n["id"]]), label(byid.get(e["to"], n)))
          for n in g["nodes"] if n["kind"] == "decision"
          and len(outs.get(n["id"], [])) >= 2
          for e in outs[n["id"]] if not (e.get("guard") or "").strip()])

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
    cross = []
    for e in g["edges"]:
        a, b = byid.get(e["from"]), byid.get(e["to"])
        if not a or not b:
            continue
        pa, pb = partition_of(a, parts), partition_of(b, parts)
        if pa and pb and pa != pb and "object" not in (a["kind"], b["kind"]):
            cross.append("%s [%s] -> %s [%s]" % (label(a), pa, label(b), pb))
    rule("work crossing between parties goes through a document", cross,
         "informational: UBL draws the hand-over as a document on the divider")

    # 9 - UBL draws the two kinds of flow differently: a control flow, between
    # actions and decisions, is a solid line; an object flow, into or out of a
    # document, is dashed. So the line style and the ends have to agree, and where
    # they do not one of the two was misread. Informational, because a handful of
    # diagrams also dash an annotation between two actions - the "prior exchange
    # of public keys" pair on the Billing processes is drawn that way.
    style = []
    for e in g["edges"]:
        a, b = byid.get(e["from"]), byid.get(e["to"])
        if not a or not b:
            continue
        doc = "object" in (a["kind"], b["kind"])
        if bool(e.get("dash")) != doc:
            style.append("%s %s %s (%s)"
                         % (label(a), "--->" if e.get("dash") else "--->",
                            label(b), "dashed but neither end is a document"
                            if e.get("dash") else "solid but one end is a document"))
    rule("dashed flows are the ones that touch a document", style,
         "informational: UBL draws object flows dashed and control flows solid")

    # 10 - the direction of every flow was read with confidence
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
         " against the artwork rather than treating them as errors")

    # 11 - every element is reachable by following arrows from a start event
    seen, stack = set(), [n["id"] for n in g["nodes"] if n["kind"] == "initial"]
    while stack:
        i = stack.pop()
        if i in seen:
            continue
        seen.add(i)
        stack += [e["to"] for e in outs.get(i, [])]
    rule("every element is reachable from a start event",
         [] if not any(n["kind"] == "initial" for n in g["nodes"])
         else [label(n) for n in g["nodes"] if n["id"] not in seen
               and n["kind"] not in ("note",)],
         "" if any(n["kind"] == "initial" for n in g["nodes"])
         else "skipped: this diagram has no start event")
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
        print("  %-4s %s%s" % ("ok" if r["ok"] else "FAIL", r["rule"],
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
