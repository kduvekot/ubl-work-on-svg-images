#!/usr/bin/env python3
"""Split the extractor's graph into the three files the rest of the pipeline reads,
and join them back.

    python3 model_io.py split    <NAME-graph.json> <out-dir>
    python3 model_io.py check    <NAME-graph.json> [...]     split and join, in memory
    python3 model_io.py validate <NAME-diagram.json> [...]   schemas and references

`extract_graph.py` writes one graph per diagram in which what the diagram *says*,
where it is *drawn* and how the reading *went* are mixed in the same objects. This
separates them:

    NAME-diagram.json     the model: lanes, nodes, flows, texts and what refers to
                          what. The part a person corrects and signs off, and what
                          a BPMN rendering would be made from.
    NAME-layout.json      where each element of the model is drawn, keyed by the
                          model's ids, in pixels of the 600-dpi original.
    NAME-extraction.json  the extractor's own measurements and the questions it
                          left open, keyed the same way. For review only: nothing
                          is drawn from it.

`split` is lossless and `check` proves it: joining the three files gives back a
graph equal to the one split, field for field, so no reading is lost on the way.

Two things the graph holds twice are held once here:

- a guard is a text block, and its flow points at it. The graph also copies the
  words onto the flow as `guard`; the copy is always the block's words with the
  line breaks taken out, which is what `guard_text()` gives back.
- a lane title is the lane's own. The graph also reads it as a free text block;
  those readings are moved to the extraction report (`titleReadings`), because
  they are how the extractor read the title and not a second thing on the page.

The graph's ids (`n1`, `n2`, ...) are handed out in reading order. They are kept
as they are for now, and the elements that had no id are given one in the same
spirit, by position in their list; so the ids are not yet stable across changes to
the extractor.
"""
import json, os, re, sys

MODEL_SCHEMA = "ubl-activity-diagram/1"
LAYOUT_SCHEMA = "ubl-activity-diagram-layout/1"
REPORT_SCHEMA = "ubl-activity-diagram-extraction/1"

# fields of a graph element that are drawing, and fields that are the reading's own
# diagnostics; whatever is in neither list is the model's
NODE_LAYOUT = ("x", "y", "w", "h", "shape", "stroke", "rx", "ry", "fold",
               "innerRatio", "bold", "labelLines")
NODE_REPORT = ("area", "fill", "solid", "stem", "lumps", "keptOnOutline", "band", "box")
EDGE_LAYOUT = ("fromPoint", "toPoint", "routing", "points", "dash", "gap", "dashOffset")
EDGE_REPORT = ("arrowInk", "arrowPx", "arrowFill", "arrowSaturated")


def name_of(path):
    return re.sub(r"(-graph)?\.json$", "", os.path.basename(path))


def norm(s):
    return " ".join((s or "").split())


def guard_text(text):
    """what a flow's guard says, from the text block that is it"""
    return norm(text["text"])


def _title_key(s):
    return re.sub(r"[^a-z0-9]", "", norm(s).lower())


def title_readings(g):
    """Which free text blocks are a lane title read a second time.

    Exactly the test the spec used to skip them with when drawing, moved here so
    the model holds each title once."""
    parts = g.get("partitions", [])
    boxes = [tuple(p["titleBox"]) for p in parts if p.get("titleBox")]
    keys = {_title_key(p.get("title")) for p in parts if p.get("title")}
    out = []
    for i, t in enumerate(g.get("text", [])):
        # Matched on letters alone, and either way round: the rule beside a title
        # strip lands in its crop, so the partition read "Transportation Network
        # Manager |" where the block reader read "Transportation Network Manager",
        # the two did not match, and IMFM drew the title twice.
        #
        # Matching by name alone needs a name long enough to be evidence. A lane
        # read as "No" - which happens where a guard sits up in the header strip,
        # on CPFR-ExceptionMonitor and CPFR-CreateOrderForecast - otherwise deletes
        # every other "No" on the page, and the two guards on the flows into the
        # end event went missing from the drawing while the artwork showed them
        # plainly. Over the 78 this branch suppresses eight blocks: the four
        # "No"s, wrongly, and four real lane titles of eleven letters and more,
        # rightly. The position test below still catches a short title in its own
        # place, which is the only place a short one is evidence of anything.
        k = _title_key(t["text"])
        if k and len(k) >= 6 and any(k == o or k in o or o in k for o in keys):
            out.append(i)
        elif any(abs(t["x"] - b[0]) <= 2 and abs(t["y"] - b[1]) <= 2 and
                 abs(t["w"] - b[2]) <= 2 and abs(t["h"] - b[3]) <= 2 for b in boxes):
            out.append(i)
    return out


def _pick(d, keys):
    return {k: d[k] for k in keys if k in d}


def _rest(d, *exclude):
    drop = set().union(*exclude)
    return {k: v for k, v in d.items() if k not in drop}


def split(g, name):
    parts = g.get("partitions", [])
    lane_id = {(p["axis"], p["index"]): "lane%d" % i for i, p in enumerate(parts)}
    has_cols = any(p["axis"] == "column" for p in parts)
    has_bands = any(p["axis"] == "band" for p in parts)

    model = dict(schema=MODEL_SCHEMA, figure=dict(name=name, source=g.get("source")),
                 lanes=[], nodes=[], flows=[], texts=[], offPage=[], marks=[], phases=[])
    layout = dict(schema=LAYOUT_SCHEMA, figure=name, units="px of the original PNG",
                  size=g["size"],
                  style=dict(fontPx=g.get("fontPx"), arrowPx=g.get("arrowPx"),
                             arrowWidthPx=g.get("arrowWidthPx"),
                             arrowStyle=g.get("arrowStyle")),
                  rules={}, greyRules=[], lanes={}, nodes={}, flows={}, texts={},
                  offPage={}, marks={}, phases={})
    report = dict(schema=REPORT_SCHEMA, figure=name, nodes={}, flows={}, offPage={},
                  marks={}, phases={}, greyRules=[], titleReadings=[], findings=[],
                  uncertain=g.get("uncertain", []))

    # the frame and partition rules, each with the span the artwork draws it over
    spans = g.get("ruleSpan") or {}
    for ax, key in (("v", "vertical"), ("h", "horizontal")):
        sp = spans.get(ax)
        layout["rules"][key] = [
            dict(at=r[0], width=r[1], span=(sp[i] if sp is not None and i < len(sp) else None))
            for i, r in enumerate(g["rules"][ax])]
    layout["rulesHaveSpans"] = {k: (ax in spans) for ax, k in (("v", "vertical"), ("h", "horizontal"))}
    if "ruleSpan" not in g:
        layout["rulesHaveSpans"] = None
    for r in g.get("greyRules", []):
        layout["greyRules"].append(_pick(r, ("axis", "at", "w", "level")))
        report["greyRules"].append(_rest(r, ("axis", "at", "w", "level")))

    for i, p in enumerate(parts):
        lid = "lane%d" % i
        model["lanes"].append(dict(id=lid, axis=p["axis"], index=p["index"], title=p["title"]))
        layout["lanes"][lid] = _rest(p, ("axis", "index", "title"))

    for n in g["nodes"]:
        m = dict(id=n["id"], kind=n["kind"])
        m.update(_rest(n, NODE_LAYOUT, NODE_REPORT, ("col", "row")))
        rep = _pick(n, NODE_REPORT)
        # which lane and band the node stands in, as the lanes' own ids; an index
        # that names no lane is kept, as read, in the report
        if "col" in n:
            m["lane"] = lane_id.get(("column", n["col"])) if has_cols else None
            if m["lane"] is None:
                rep["col"] = n["col"]
        if "row" in n:
            m["band"] = lane_id.get(("band", n["row"])) if has_bands else None
            if m["band"] is None:
                rep["row"] = n["row"]
        model["nodes"].append(m)
        layout["nodes"][n["id"]] = _pick(n, NODE_LAYOUT)
        if rep:
            report["nodes"][n["id"]] = rep

    titles = set(title_readings(g))
    text_id = {}
    for i, t in enumerate(g.get("text", [])):
        if i in titles:
            report["titleReadings"].append(dict(position=i, **t))
            continue
        tid = "t%d" % i
        text_id[i] = tid
        m = dict(id=tid, text=t["text"])
        if "attachedTo" in t:
            m["labels"] = None          # filled in below, once flows have ids
            m["_attached"] = t["attachedTo"]
        model["texts"].append(m)
        layout["texts"][tid] = _rest(t, ("text", "attachedTo"))

    flow_of = {}
    for i, e in enumerate(g["edges"]):
        fid = "f%d" % i
        m = dict(id=fid, **_rest(e, EDGE_LAYOUT, EDGE_REPORT,
                                 ("guard", "directionConfidence", "directionChecked",
                                  "edgeKind", "arrowBoth")))
        if "edgeKind" in e:
            m["kind"] = e["edgeKind"]
        if "directionConfidence" in e or "directionChecked" in e:
            m["direction"] = _pick(e, ("directionConfidence", "directionChecked"))
            m["direction"] = {{"directionConfidence": "confidence",
                               "directionChecked": "checked"}[k]: v
                              for k, v in m["direction"].items()}
        if "arrowBoth" in e:
            m["bothEnds"] = e["arrowBoth"]
        if "guard" in e:
            # the text block that is this guard: attached to this flow and saying
            # the same words
            key = "%s->%s" % (e["from"], e["to"])
            hits = [t for t in model["texts"]
                    if t.get("_attached") == key and guard_text(t) == e["guard"]]
            if not hits:
                # The reading also attached a lane title to a flow as its guard -
                # four times over the 78: "Seller" and "Producer" twice, and on
                # CPFR-CreateOrderForecast a real "No" guard taken for the title
                # of a lane. The block is the title's reading, so the guard is the
                # lane's title, and the model says exactly that.
                hits = [l for l in model["lanes"]
                        if norm(l["title"]) == e["guard"] and any(
                            r.get("attachedTo") == key and norm(r["text"]) == e["guard"]
                            for r in report["titleReadings"])]
                if len(hits) == 1:
                    report["findings"].append(dict(
                        kind="guard-is-lane-title", flow=fid, lane=hits[0]["id"],
                        detail="the guard on %s is the title of %s, %r"
                               % (key, hits[0]["id"], e["guard"]),
                        check="a lane title does not label a flow: either the "
                              "title was attached by mistake or the lane title is "
                              "a misread guard"))
            if len(hits) != 1:
                raise ValueError("%s: guard %r on %s matches %d text blocks"
                                 % (name, e["guard"], key, len(hits)))
            m["guard"] = hits[0]["id"]
        model["flows"].append(m)
        layout["flows"][fid] = _pick(e, EDGE_LAYOUT)
        rep = _pick(e, EDGE_REPORT)
        if rep:
            report["flows"][fid] = rep
        flow_of.setdefault("%s->%s" % (e["from"], e["to"]), []).append(fid)

    for t in model["texts"]:
        if "_attached" in t:
            # the flow a text block is attached to. Two flows between the same two
            # nodes would make this ambiguous; the 78 have none, and if one ever
            # appears the split refuses rather than guessing.
            fs = flow_of.get(t["_attached"], [])
            if len(fs) > 1:
                raise ValueError("%s: %s is attached to %d flows" % (name, t["id"], len(fs)))
            t["labels"] = fs[0] if fs else None
            if fs and any(o is not t and o.get("labels") == fs[0] for o in model["texts"]) \
                    and not any(f.get("kind") == "flow-with-two-texts" and f["flow"] == fs[0]
                                for f in report["findings"]):
                report["findings"].append(dict(
                    kind="flow-with-two-texts", flow=fs[0],
                    texts=[o["id"] for o in model["texts"] if o.get("labels") == fs[0]],
                    detail="more than one text block is attached to %s" % t["_attached"],
                    check="a flow has at most one guard: one of these belongs to "
                          "another flow"))
            if not fs:
                report.setdefault("unresolvedAttachments", {})[t["id"]] = t["_attached"]
            del t["_attached"]

    for i, o in enumerate(g.get("openEnds", [])):
        oid = "o%d" % i
        model["offPage"].append(dict(id=oid, node=o["node"],
                                     direction="in" if o["inward"] else "out",
                                     arrow=o["arrow"]))
        layout["offPage"][oid] = _pick(o, ("at", "end", "points", "x", "y", "w", "h"))
        report["offPage"][oid] = _rest(o, ("node", "inward", "arrow", "at", "end",
                                           "points", "x", "y", "w", "h"))
    for i, c in enumerate(g.get("crossMarks", [])):
        cid = "m%d" % i
        model["marks"].append(dict(id=cid, kind="cross-mark", rule=c["rule"]))
        layout["marks"][cid] = _pick(c, ("x1", "y1", "x2", "y2", "weight"))
        report["marks"][cid] = _rest(c, ("rule", "x1", "y1", "x2", "y2", "weight"))
    for i, d in enumerate(g.get("dashed", [])):
        did = "p%d" % i
        model["phases"].append(dict(id=did))
        layout["phases"][did] = _pick(d, ("x", "y", "w", "h", "rx", "dash", "gap", "weight"))
        report["phases"][did] = _rest(d, ("x", "y", "w", "h", "rx", "dash", "gap", "weight"))

    # what the graph has at the top that is not handled above goes to the report,
    # so a field the extractor adds later is carried rather than lost
    known = {"source", "size", "fontPx", "arrowPx", "arrowWidthPx", "arrowStyle",
             "rules", "ruleSpan", "greyRules", "dashed", "openEnds", "crossMarks",
             "partitions", "nodes", "edges", "text", "uncertain"}
    extra = {k: v for k, v in g.items() if k not in known}
    if extra:
        report["unmapped"] = extra
    report["present"] = [k for k in g]          # the graph's own key order
    return model, layout, report


def join(model, layout, report):
    """The graph the three files were split from, exactly."""
    lanes = {l["id"]: l for l in model["lanes"]}
    g = {}
    g["source"] = model["figure"]["source"]
    g["size"] = layout["size"]
    st = layout["style"]
    g["fontPx"], g["arrowPx"] = st["fontPx"], st["arrowPx"]
    g["arrowWidthPx"], g["arrowStyle"] = st["arrowWidthPx"], st["arrowStyle"]
    g["rules"] = {ax: [[r["at"], r["width"]] for r in layout["rules"][k]]
                  for ax, k in (("v", "vertical"), ("h", "horizontal"))}
    hs = layout.get("rulesHaveSpans")
    if hs is not None:
        g["ruleSpan"] = {ax: [r["span"] for r in layout["rules"][k]]
                         for ax, k in (("v", "vertical"), ("h", "horizontal")) if hs[k]}
    g["greyRules"] = [dict(a, **b) for a, b in zip(layout["greyRules"], report["greyRules"])]
    g["dashed"] = [dict(layout["phases"][p["id"]], **report["phases"][p["id"]])
                   for p in model["phases"]]
    g["openEnds"] = [dict(node=o["node"], inward=o["direction"] == "in", arrow=o["arrow"],
                          **layout["offPage"][o["id"]], **report["offPage"][o["id"]])
                     for o in model["offPage"]]
    g["crossMarks"] = [dict(rule=c["rule"], **layout["marks"][c["id"]], **report["marks"][c["id"]])
                       for c in model["marks"]]
    g["partitions"] = [dict(axis=l["axis"], index=l["index"], title=l["title"],
                            **layout["lanes"][l["id"]]) for l in model["lanes"]]
    g["nodes"] = []
    for n in model["nodes"]:
        d = {k: v for k, v in n.items() if k not in ("lane", "band")}
        d.update(layout["nodes"][n["id"]])
        rep = dict(report["nodes"].get(n["id"], {}))
        if "lane" in n:
            d["col"] = lanes[n["lane"]]["index"] if n["lane"] else rep.pop("col")
        if "band" in n:
            d["row"] = lanes[n["band"]]["index"] if n["band"] else rep.pop("row")
        rep.pop("col", None); rep.pop("row", None)
        d.update(rep)
        g["nodes"].append(d)
    texts = {t["id"]: t for t in model["texts"]}
    flows = {f["id"]: f for f in model["flows"]}
    g["edges"] = []
    for f in model["flows"]:
        d = {k: v for k, v in f.items()
             if k not in ("id", "kind", "direction", "bothEnds", "guard")}
        d.update(layout["flows"][f["id"]])
        d.update(report["flows"].get(f["id"], {}))
        if "guard" in f:
            d["guard"] = (guard_text(texts[f["guard"]]) if f["guard"] in texts
                          else norm(lanes[f["guard"]]["title"]))
        for k, v in (f.get("direction") or {}).items():
            d[{"confidence": "directionConfidence", "checked": "directionChecked"}[k]] = v
        if "bothEnds" in f:
            d["arrowBoth"] = f["bothEnds"]
        if "kind" in f:
            d["edgeKind"] = f["kind"]
        g["edges"].append(d)
    unresolved = report.get("unresolvedAttachments", {})
    blocks = []
    for t in model["texts"]:
        d = dict(text=t["text"], **layout["texts"][t["id"]])
        if "labels" in t:
            if t["labels"]:
                fl = flows[t["labels"]]
                d["attachedTo"] = "%s->%s" % (fl["from"], fl["to"])
            else:
                d["attachedTo"] = unresolved[t["id"]]
        blocks.append((int(t["id"][1:]), d))
    for r in report["titleReadings"]:
        r = dict(r)
        blocks.append((r.pop("position"), r))
    g["text"] = [d for _, d in sorted(blocks, key=lambda b: b[0])]
    g["uncertain"] = report["uncertain"]
    g.update(report.get("unmapped", {}))
    return {k: g[k] for k in report["present"] if k in g}


def write(obj, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1, ensure_ascii=False)
        f.write("\n")


def paths(out_dir, name):
    return tuple(os.path.join(out_dir, "%s-%s.json" % (name, k))
                 for k in ("diagram", "layout", "extraction"))


def load(diagram_path):
    """the model and its layout, from the model's path"""
    base = re.sub(r"-diagram\.json$", "", diagram_path)
    return (json.load(open(diagram_path, encoding="utf-8")),
            json.load(open(base + "-layout.json", encoding="utf-8")))


def validate(diagram_path):
    """What is wrong with a model and its layout and report, as a list of
    sentences: each file against its schema, then the references between them -
    every id a flow, guard, node or text names exists, and every element of the
    model has a place in the layout and nothing else does. Empty means sound."""
    base = re.sub(r"-diagram\.json$", "", diagram_path)
    files = dict(diagram=diagram_path, layout=base + "-layout.json",
                 extraction=base + "-extraction.json")
    docs, errs = {}, []
    here = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema")
    try:
        import jsonschema
    except ImportError:
        jsonschema = None
        print("warning: jsonschema is not installed, so only the references were "
              "checked, not the schemas", file=sys.stderr)
    for k, p in files.items():
        if not os.path.exists(p):
            errs.append("%s: missing" % p)
            continue
        docs[k] = json.load(open(p, encoding="utf-8"))
        if jsonschema:
            schema = json.load(open(os.path.join(here, k + ".schema.json")))
            for e in sorted(jsonschema.Draft202012Validator(schema).iter_errors(docs[k]),
                            key=lambda e: list(e.path)):
                errs.append("%s: %s: %s" % (os.path.basename(p),
                                            "/".join(map(str, e.path)) or "(top)", e.message))
    m, l = docs.get("diagram"), docs.get("layout")
    if not m or not l:
        return errs
    ids = {}
    for sec in ("lanes", "nodes", "flows", "texts", "offPage", "marks", "phases"):
        for x in m.get(sec, []):
            if x["id"] in ids:
                errs.append("id %s is used twice (%s and %s)" % (x["id"], ids[x["id"]], sec))
            ids[x["id"]] = sec

    def ref(what, v, *secs):
        if v is not None and ids.get(v) not in secs:
            errs.append("%s names %r, which is not one of the diagram's %s"
                        % (what, v, " or ".join(secs)))
    for n in m["nodes"]:
        ref("node %s's lane" % n["id"], n.get("lane"), "lanes")
        ref("node %s's band" % n["id"], n.get("band"), "lanes")
    for f in m["flows"]:
        ref("flow %s's source" % f["id"], f["from"], "nodes")
        ref("flow %s's target" % f["id"], f["to"], "nodes")
        ref("flow %s's guard" % f["id"], f.get("guard"), "texts", "lanes")
    for t in m["texts"]:
        ref("text %s" % t["id"], t.get("labels"), "flows")
    for o in m["offPage"]:
        ref("off-page flow %s" % o["id"], o["node"], "nodes")
    for sec in ("lanes", "nodes", "flows", "texts", "offPage", "marks", "phases"):
        want = {x["id"] for x in m.get(sec, [])}
        have = set(l.get(sec, {}))
        for i in sorted(want - have):
            errs.append("%s %s has no place in the layout" % (sec, i))
        for i in sorted(have - want):
            errs.append("the layout places %s %s, which the model does not have" % (sec, i))
    return errs


def main(argv):
    if len(argv) >= 3 and argv[0] == "split":
        g = json.load(open(argv[1], encoding="utf-8"))
        name = name_of(argv[1])
        model, layout, report = split(g, name)
        if join(model, layout, report) != g:
            sys.exit("%s: the split does not join back to the graph it came from" % name)
        for obj, p in zip((model, layout, report), paths(argv[2], name)):
            write(obj, p)
        print("  %s -> diagram, layout, extraction  (%d nodes, %d flows, %d texts)"
              % (name, len(model["nodes"]), len(model["flows"]), len(model["texts"])))
        return 0
    if len(argv) >= 2 and argv[0] == "check":
        bad = 0
        for p in argv[1:]:
            g = json.load(open(p, encoding="utf-8"))
            m, l, r = split(g, name_of(p))
            # through text, so what is checked is what a file would hold
            m, l, r = (json.loads(json.dumps(x)) for x in (m, l, r))
            if join(m, l, r) != g:
                bad += 1
                print("DOES NOT ROUND-TRIP: %s" % p)
        print("%d of %d graphs round-trip exactly" % (len(argv) - 1 - bad, len(argv) - 1))
        return 1 if bad else 0
    if len(argv) >= 2 and argv[0] == "validate":
        bad = 0
        for p in argv[1:]:
            errs = validate(p)
            for e in errs:
                print("%s: %s" % (name_of(p).replace("-diagram", ""), e))
            bad += bool(errs)
        print("%d of %d diagrams valid" % (len(argv) - 1 - bad, len(argv) - 1))
        return 1 if bad else 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
