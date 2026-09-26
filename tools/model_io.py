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

Every element gets an id that says what it is, not when it was read: the graph's
ids (`n1`, `n2`, ...) are handed out in reading order and move whenever the
extractor changes, so nothing could be pinned to one. See `assign_ids()`. The
graph's own ids are kept in the extraction report as `formerIds`, which is also
how the split joins back.
"""
import json, os, re, sys
from collections import Counter

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


def slug(s, limit=40):
    """lower case, words joined by hyphens, cut at a word boundary"""
    words = re.findall(r"[a-z0-9]+", (s or "").lower())
    out = ""
    for w in words:
        if out and len(out) + 1 + len(w) > limit:
            break
        out = (out + "-" + w) if out else w[:limit]
    return out


def _unique(wanted, order_key):
    """Give each element the id it asks for, numbering the ones that ask for the
    same thing - "-2", "-3" ... in the order of `order_key` (where they are on the
    page), the first keeping the bare name."""
    groups = {}
    for el, want in wanted:
        groups.setdefault(want, []).append(el)
    out = {}
    for want, els in groups.items():
        els = sorted(els, key=order_key)
        for i, el in enumerate(els):
            out[id(el)] = want if i == 0 else "%s-%d" % (want, i + 1)
    return out


def assign_ids(model, layout, report):
    """Replace the graph's ids with ids that say what each element is (see
    names()), and keep the graph's in the report as formerIds."""
    rename = names(model, layout)
    _rename(model, layout, report, rename)
    report["formerIds"] = {v: k for k, v in rename.items()}


def names(model, layout):
    """The id each element should have, as {current id: name}.

        lane-<title> / band-<title>            lane-accounting-supplier
        <kind>-<label>                         action-raise-invoice, object-invoice
        <kind>-<lane>                          initial-accounting-supplier
        flow-<from>-to-<to>                    flow-raise-invoice-to-invoice
        text-<words>                           text-accept-charges
        offpage-<node>                         offpage-action-download-business-card
        phase-<title>, mark-<n>                phase-create-order-forecast, mark-1

    Where two elements would get the same id, the one higher on the page (then
    further left) keeps it and the others are numbered -2, -3 in that order. A
    label shared by nodes in different lanes takes the lane's name first.

    These are names, not a hash: once a model is kept and corrected by hand, its
    ids are kept too, and a later correction to a label does not rename anything.
    They are derived afresh only while the model is still made from a reading."""
    lay_of = {}
    for sec in ("lanes", "nodes", "flows", "texts", "offPage", "marks", "phases"):
        for el in model[sec]:
            lay_of[id(el)] = layout[sec].get(el["id"], {})

    def at(el):
        """where an element is, for ordering duplicates: top, then left"""
        g = lay_of[id(el)]
        if "box" in g:                                   # drawn in a title's place
            return (g["box"][1], g["box"][0])
        if "x" in g:
            return (g["y"], g["x"])
        if "fromPoint" in g:
            return (g["fromPoint"][1], g["fromPoint"][0], g["toPoint"][1], g["toPoint"][0])
        if "y2" in g:                                    # a cross-mark
            return (min(g["y1"], g["y2"]), min(g["x1"], g["x2"]))
        if "at" in g and isinstance(g["at"], list):
            return (g["at"][1], g["at"][0])
        return (g.get("y0", 0), g.get("x0", 0))

    new = {}
    # lanes: by title, or by position where the artwork gives none
    want = []
    for l in model["lanes"]:
        kind = "lane" if l["axis"] == "column" else "band"
        want.append((l, "%s-%s" % (kind, slug(l["title"]) or str(l["index"] + 1))))
    for el, v in _unique(want, at).items():
        new[el] = v
    lane_name = {l["id"]: new[id(l)] for l in model["lanes"]}

    # nodes: by kind and label; unlabelled ones by kind and lane
    want = []
    for n in model["nodes"]:
        lab = slug(n.get("label"))
        if lab:
            want.append((n, "%s-%s" % (n["kind"], lab)))
        else:
            ln = lane_name.get(n.get("lane"))
            want.append((n, "%s-%s" % (n["kind"], ln[len("lane-"):]) if ln else n["kind"]))
    # the same label in different lanes: say which lane before resorting to numbers
    seen = Counter(w for _, w in want)
    def where(n):
        if n.get("lane"):
            return "in-" + lane_name[n["lane"]][len("lane-"):]
        if n.get("between"):
            return "between-" + "-and-".join(lane_name[x][len("lane-"):] for x in n["between"])
        return None
    want = [(n, w if seen[w] == 1 or not slug(n.get("label")) or not where(n)
             else "%s-%s" % (w, where(n)))
            for n, w in want]
    for el, v in _unique(want, at).items():
        new[el] = v
    node_name = {n["id"]: new[id(n)] for n in model["nodes"]}

    # a flow is named by its two ends, the labelled ones without their kinds:
    # "flow-raise-invoice-to-invoice" says enough, and any two that come out the
    # same are numbered. An unlabelled end keeps its kind - "initial-accounting-
    # supplier" - since without it the name would be just a lane's.
    labelled = {n["id"] for n in model["nodes"] if slug(n.get("label"))}
    bare = lambda i: (re.sub(r"^[a-z]+-", "", node_name[i]) if i in labelled
                      else node_name.get(i, i))
    want = [(f, "flow-%s-to-%s" % (bare(f["from"]), bare(f["to"]))) for f in model["flows"]]
    for el, v in _unique(want, at).items():
        new[el] = v
    want = [(t, "text-%s" % (slug(t["text"]) or "blank")) for t in model["texts"]]
    for el, v in _unique(want, at).items():
        new[el] = v
    want = [(o, "offpage-%s" % node_name.get(o["node"], o["node"])) for o in model["offPage"]]
    for el, v in _unique(want, at).items():
        new[el] = v
    # marks have no words of their own, so they are numbered from the top of the
    # page, always, so their ids are never a plain word; so are phases, until a
    # phase is given its title
    for i, el in enumerate(sorted(model["marks"], key=at)):
        new[id(el)] = "mark-%d" % (i + 1)
    want = [(p, "phase-%s" % slug(p["title"])) for p in model["phases"] if slug(p.get("title"))]
    for el, v in _unique(want, at).items():
        new[el] = v
    for i, el in enumerate(sorted((p for p in model["phases"] if id(p) not in new), key=at)):
        new[id(el)] = "phase-%d" % (i + 1)

    rename = {}
    for sec in ("lanes", "nodes", "flows", "texts", "offPage", "marks", "phases"):
        for el in model[sec]:
            rename[el["id"]] = new[id(el)]
    if len(set(rename.values())) != len(rename):
        raise ValueError("%s: two elements were given the same id" % model["figure"]["name"])
    return rename


def _rename(model, layout, report, rename):
    """apply an old-id -> new-id map to every place an id is held"""
    r = lambda v: rename.get(v, v) if isinstance(v, str) else v
    for sec in ("lanes", "nodes", "flows", "texts", "offPage", "marks", "phases"):
        for el in model[sec]:
            el["id"] = r(el["id"])
            for k in ("lane", "band", "from", "to", "guard", "labels", "node"):
                if k in el:
                    el[k] = r(el[k])
        layout[sec] = {r(k): v for k, v in layout[sec].items()}
    for sec in ("nodes", "flows", "offPage", "marks", "phases"):
        report[sec] = {r(k): v for k, v in report[sec].items()}
    if "documentLanes" in report:
        report["documentLanes"] = {r(k): r(v) for k, v in report["documentLanes"].items()}
    for n in model["nodes"]:
        if "between" in n:
            n["between"] = [r(x) for x in n["between"]]
    if "unresolvedAttachments" in report:
        report["unresolvedAttachments"] = {r(k): v for k, v in report["unresolvedAttachments"].items()}
    for f in report["findings"]:
        for k in ("flow", "lane"):
            if k in f:
                f[k] = r(f[k])
        if "texts" in f:
            f["texts"] = [r(t) for t in f["texts"]]


_CORRECTIONS = None


def corrections_for(name):
    """the corrections recorded for one diagram, from tools/model-corrections.json"""
    global _CORRECTIONS
    if _CORRECTIONS is None:
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "model-corrections.json")
        _CORRECTIONS = json.load(open(p, encoding="utf-8"))["diagrams"] if os.path.exists(p) else {}
    return _CORRECTIONS.get(name, [])


def apply_corrections(model, layout, report, name, recorded=None):
    """Apply what a person decided about this diagram's model.

    The corrections name elements as the uncorrected reading names them (the ids
    names() gives before any correction), and are applied before the final ids
    are assigned, so that a lane corrected to "Buyer Party" is called
    lane-buyer-party. The kinds:

      attach-guard           text `text` is the guard of `to` (a flow or an
                             off-page flow), and of nothing else
      guard-from-lane-title  what the reading took for lane `lane`'s title is a
                             guard of `to`; it becomes a text, drawn where it was
      phase-title-from-lane  lane `lane`'s title is phase `phase`'s title
      phase-title-from-text  text `text` is phase `phase`'s title
      name-lane              lane `lane` is called `title`, which the artwork
                             does not show; `source` says where the name comes
                             from ("text" of the specification, or "convention")
      continues              off-page flow `offPage` continues from or into the
                             figure `figure`
      external               node `node` stands for a process outside this
                             diagram's scope; `reference` says which, and where
      between                node `node` stands between the two `lanes`
      flow-kind              flow `flow` is of kind `kind` (e.g. "precondition")

    Each may say what the reading held before (`was`), and is refused if the
    reading no longer holds it: a correction is a decision about one reading,
    and applied to another it would be a guess. The uncorrected model and layout
    are kept in the report, so the split still joins back to the graph exactly;
    none of this moves anything that is drawn."""
    todo = corrections_for(name) if recorded is None else recorded
    if not todo:
        return
    report["uncorrected"] = json.loads(json.dumps(dict(model=model, layout=layout)))
    named = names(model, layout)                     # graph id -> reading name
    gid = {v: k for k, v in named.items()}           # reading name -> graph id
    rn = lambda v: named.get(v, v)

    def el(sec, ref, cid):
        i = gid.get(ref, ref if ref.startswith("corr-") else None)
        for x in model[sec]:
            if x["id"] == i:
                return x
        raise ValueError("%s: correction %s names %s %r, which this reading does not have"
                         % (name, cid, sec, ref))

    def check_was(c, x):
        for k, v in c.get("was", {}).items():
            have = rn(x.get(k)) if isinstance(x.get(k), str) and x.get(k) in named else x.get(k)
            if have != v:
                raise ValueError("%s: correction %s was made for %s = %r, and this reading has "
                                 "%r - check it again against the artwork" % (name, c["id"], k, v, have))

    def target(ref, cid):
        i = gid.get(ref)
        for sec in ("flows", "offPage"):
            for x in model[sec]:
                if x["id"] == i:
                    return x
        raise ValueError("%s: correction %s names %r, which is not a flow of this reading"
                         % (name, cid, ref))

    def make_guard(t, to):
        for x in model["flows"] + model["offPage"]:      # it is no one else's guard
            if x.get("guard") == t["id"]:
                del x["guard"]
        t["labels"] = to["id"]
        to["guard"] = t["id"]

    touched = set()
    for c in todo:
        op, cid = c["op"], c["id"]
        if op == "attach-guard":
            t = el("texts", c["text"], cid)
            check_was(c, t)
            to = target(c["to"], cid)
            make_guard(t, to)
            touched |= {t["id"], to["id"]}
        elif op == "guard-from-lane-title":
            l = el("lanes", c["lane"], cid)
            check_was(c, l)
            to = target(c["to"], cid)
            box = layout["lanes"][l["id"]].pop("titleBox")
            t = dict(id="corr-%s" % cid, text=l["title"])
            model["texts"].append(t)
            layout["texts"][t["id"]] = {"as": "lane-title", "box": box}
            for x in model["flows"] + model["offPage"]:  # the title was no one's guard
                if x.get("guard") == l["id"]:
                    del x["guard"]
                    touched.add(x["id"])
            l["title"] = ""
            make_guard(t, to)
            touched |= {l["id"], to["id"]}
        elif op == "phase-title-from-lane":
            l, p = el("lanes", c["lane"], cid), el("phases", c["phase"], cid)
            check_was(c, l)
            p["title"] = l["title"]
            layout["phases"][p["id"]]["title"] = {"as": "lane-title",
                                                  "box": layout["lanes"][l["id"]].pop("titleBox")}
            l["title"] = ""
            touched |= {l["id"], p["id"]}
        elif op == "phase-title-from-text":
            t, p = el("texts", c["text"], cid), el("phases", c["phase"], cid)
            check_was(c, t)
            p["title"] = t["text"]
            layout["phases"][p["id"]]["title"] = dict(layout["texts"].pop(t["id"]), **{"as": "text"})
            model["texts"].remove(t)
            touched |= {t["id"], p["id"]}
        elif op == "name-lane":
            l = el("lanes", c["lane"], cid)
            check_was(c, l)
            if "titleBox" in layout["lanes"][l["id"]]:
                raise ValueError("%s: correction %s names %s, which still draws a title of its "
                                 "own; move that first" % (name, cid, c["lane"]))
            l["title"], l["titleShown"], l["titleSource"] = c["title"], False, c["source"]
            touched.add(l["id"])
        elif op == "split-lane":
            # a column the reading took as one, divided at `at` (a rule it read
            # but did not take for a divider); the new column is to the right
            l = el("lanes", c["lane"], cid)
            ll = layout["lanes"][l["id"]]
            at = c["at"]
            if not ll["x0"] < at < ll["x1"]:
                raise ValueError("%s: correction %s splits %s at %s, outside it" % (name, cid, c["lane"], at))
            for x in model["lanes"]:
                if x["axis"] == "column" and x["index"] > l["index"]:
                    x["index"] += 1
            r = dict(id="corr-%s" % cid, axis="column", index=l["index"] + 1, title="")
            model["lanes"].insert(model["lanes"].index(l) + 1, r)
            layout["lanes"][r["id"]] = {"x0": at, "x1": ll["x1"]}
            ll["x1"] = at
            for n in model["nodes"]:
                g = layout["nodes"][n["id"]]
                if n.get("lane") == l["id"] and g["x"] + g["w"] / 2.0 > at:
                    n["lane"] = r["id"]
            touched |= {l["id"], r["id"]}
        elif op == "external":
            # a box standing for a whole process this diagram points at and does
            # not describe (a BPMN call activity): CPFR's Order Generation, the
            # prior exchange of public keys
            n = el("nodes", c["node"], cid)
            check_was(c, n)
            n["scope"] = "external"
            n["reference"] = c["reference"]
            touched.add(n["id"])
        elif op == "between":
            n = el("nodes", c["node"], cid)
            n["lane"] = None
            n["between"] = [el("lanes", x, cid)["id"] for x in c["lanes"]]
            touched.add(n["id"])
        elif op == "flow-kind":
            f = el("flows", c["flow"], cid)
            check_was(c, f)
            f["kind"] = c["kind"]
            touched.add(f["id"])
        elif op == "continues":
            o = el("offPage", c["offPage"], cid)
            o["continues"] = c["figure"]
            touched.add(o["id"])
        else:
            raise ValueError("%s: correction %s: unknown op %r" % (name, cid, op))
    for f in report["findings"]:
        if touched & ({f.get("flow"), f.get("lane")} | set(f.get("texts", []))):
            f["resolvedBy"] = [c["id"] for c in todo]
    report["corrections"] = [c["id"] for c in todo]


def place_documents(model, layout, report):
    """A document drawn across the line between two columns stands between them.

    UBL draws every document (object node) on the divider between the two parties
    that exchange it - all 228 in the 78 diagrams - and the reading assigned each
    to whichever column its centre fell in, sometimes by a pixel: on Fig 12
    Retail Event came out the Buyer's and Product Activity, drawn the same way on
    the same line, the Seller's. Decided with the TC (q4b): such a document has no
    lane of its own; it is `between` the two columns either side of the line.
    Who hands it over and who receives it are its flows, which already name them.

    The lane it was given is kept in the report, so the split joins back."""
    cols = sorted((l for l in model["lanes"] if l["axis"] == "column"), key=lambda l: l["index"])
    bounds = [(a, b, layout["lanes"][a["id"]]["x1"]) for a, b in zip(cols, cols[1:])
              if layout["lanes"][a["id"]].get("x1") == layout["lanes"][b["id"]].get("x0")]
    moved = {}
    for n in model["nodes"]:
        if n["kind"] != "object":
            continue
        g = layout["nodes"][n["id"]]
        across = [(a, b) for a, b, x in bounds if g["x"] < x < g["x"] + g["w"]]
        if len(across) == 1:
            a, b = across[0]
            moved[n["id"]] = n.get("lane")
            n["lane"] = None
            n["between"] = [a["id"], b["id"]]
    report["documentLanes"] = moved


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
    apply_corrections(model, layout, report, name)
    place_documents(model, layout, report)
    assign_ids(model, layout, report)
    return model, layout, report


def join(model, layout, report):
    """The graph the three files were split from, exactly."""
    model, layout, report = (json.loads(json.dumps(x)) for x in (model, layout, report))
    if "uncorrected" in report:
        # corrections were applied: the reading, before them, in the graph's ids.
        # The report's own entries are keyed by the final ids, so they go back too.
        _rename(model, layout, report, report.pop("formerIds"))
        model, layout = report["uncorrected"]["model"], report["uncorrected"]["layout"]
    elif "formerIds" in report:
        _rename(model, layout, report, report.pop("formerIds"))
        back = report.get("documentLanes", {})
        for n in model["nodes"]:
            if n["id"] in back:
                n["lane"] = back[n["id"]]
                n.pop("between", None)
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
        for x in n.get("between", []):
            ref("node %s's between" % n["id"], x, "lanes")
    for f in m["flows"]:
        ref("flow %s's source" % f["id"], f["from"], "nodes")
        ref("flow %s's target" % f["id"], f["to"], "nodes")
        ref("flow %s's guard" % f["id"], f.get("guard"), "texts", "lanes")
    for t in m["texts"]:
        ref("text %s" % t["id"], t.get("labels"), "flows", "offPage")
    for o in m["offPage"]:
        ref("off-page flow %s" % o["id"], o["node"], "nodes")
        ref("off-page flow %s's guard" % o["id"], o.get("guard"), "texts")
    # a guard and its text agree about each other
    for x in m["flows"] + m["offPage"]:
        g = x.get("guard")
        t = next((t for t in m["texts"] if t["id"] == g), None)
        if t is not None and t.get("labels") != x["id"]:
            errs.append("%s's guard is %s, which says it labels %r"
                        % (x["id"], g, t.get("labels")))
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
