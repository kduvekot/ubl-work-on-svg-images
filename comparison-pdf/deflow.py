#!/usr/bin/env python3
"""Render-only fixup: rewrite Inkscape <flowRoot> (SVG 1.2 draft, unsupported by
Batik and by every web browser) into standard <text>/<tspan>, so the comparison
PDF can show the text those five diagrams carry. Source files are not modified."""
import re, sys, os, shutil
import xml.etree.ElementTree as ET

SVG = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG)
NS = {"svg": SVG}


def style_val(style, key, default=None):
    m = re.search(r"(?:^|;)\s*%s\s*:\s*([^;]+)" % re.escape(key), style or "")
    return m.group(1).strip() if m else default


def convert(path, out):
    src = open(path, encoding="utf-8").read()
    tree = ET.parse(path)
    root = tree.getroot()
    parents = {c: p for p in root.iter() for c in p}
    n = 0
    for fr in list(root.iter("{%s}flowRoot" % SVG)):
        style = fr.get("style", "")
        size = float(re.sub(r"[a-z%]+$", "", style_val(style, "font-size", "10px")))
        lh = style_val(style, "line-height", "100%")
        lead = size * (float(lh[:-1]) / 100 if lh.endswith("%") else float(lh))
        anchor = style_val(style, "text-anchor", "start")

        rect = fr.find("./{%s}flowRegion/{%s}rect" % (SVG, SVG))
        if rect is None:
            continue
        rx, ry = float(rect.get("x", 0)), float(rect.get("y", 0))
        rw = float(rect.get("width", 0))
        x = rx + rw / 2 if anchor == "middle" else (rx + rw if anchor == "end" else rx)

        text = ET.Element("{%s}text" % SVG)
        for a in ("style", "transform", "id", "{http://www.w3.org/XML/1998/namespace}space"):
            if fr.get(a) is not None:
                text.set(a, fr.get(a))
        text.set("x", "%g" % x)
        text.set("y", "%g" % (ry + size))

        lines = [p for p in fr.findall("./{%s}flowPara" % SVG)]
        for i, p in enumerate(lines):
            ts = ET.SubElement(text, "{%s}tspan" % SVG)
            ts.set("x", "%g" % x)
            ts.set("y", "%g" % (ry + size + i * lead))
            ts.text = "".join(p.itertext())

        parent = parents[fr]
        parent[list(parent).index(fr)] = text
        n += 1

    tree.write(out, encoding="utf-8", xml_declaration=True)
    return n


if __name__ == "__main__":
    src_dir, dst_dir = sys.argv[1], sys.argv[2]
    os.makedirs(dst_dir, exist_ok=True)
    total = 0
    for name in sorted(os.listdir(src_dir)):
        s, d = os.path.join(src_dir, name), os.path.join(dst_dir, name)
        if name.endswith(".svg") and "flowRoot" in open(s, encoding="utf-8").read():
            c = convert(s, d)
            total += c
            print("converted %2d flowRoot in %s" % (c, name))
        else:
            shutil.copy2(s, d)
    print("total flowRoot converted:", total)
