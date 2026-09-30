"""The UBL shape library for draw.io, tools/ubl-library.xml: the shapes of the
drawings, in their style, each with its ubl-kind set.

    python3 library.py                       writes tools/ubl-library.xml
"""
import os
import base64, json, zlib, urllib.parse, html
def compress(xml):
    data = urllib.parse.quote(xml, safe="-_.!~*'()")
    c = zlib.compressobj(9, zlib.DEFLATED, -15); raw = c.compress(data.encode()) + c.flush()
    return base64.b64encode(raw).decode()
def vertex(kind, label, style, w, h, extra=""):
    return ('<mxGraphModel><root><mxCell id="0"/><mxCell id="1" parent="0"/>'
            '<object id="2" label="%s" ubl-kind="%s"%s><mxCell style="%s" vertex="1" parent="1">'
            '<mxGeometry width="%d" height="%d" as="geometry"/></mxCell></object></root></mxGraphModel>'
            % (html.escape(label, quote=True), kind, extra, style, w, h))
def edge(flow, w):
    return ('<mxGraphModel><root><mxCell id="0"/><mxCell id="1" parent="0"/>'
            '<object id="2" label="" ubl-kind="flow" ubl-flow="%s"><mxCell style="edgeStyle=none;rounded=0;html=1;endArrow=open;endFill=0;endSize=10;" edge="1" parent="1">'
            '<mxGeometry relative="1" as="geometry"><mxPoint x="0" y="0" as="sourcePoint"/><mxPoint x="%d" y="0" as="targetPoint"/></mxGeometry></mxCell></object></root></mxGraphModel>' % (flow, w))
TXT = "html=1;whiteSpace=nowrap;fontSize=12;align=center;verticalAlign=middle;"
items = [
 ("Action", vertex("action", "Action", "rounded=1;absoluteArcSize=1;arcSize=24;" + TXT + "fontStyle=1;", 150, 40), 150, 40),
 ("Document (object node)", vertex("object", "Document", "rounded=0;strokeWidth=2;" + TXT + "fontStyle=3;", 110, 60), 110, 60),
 ("Decision", vertex("decision", "", "rhombus;" + TXT, 40, 40), 40, 40),
 ("Start (initial node)", vertex("initial", "", "ellipse;shape=startState;fillColor=#000000;strokeColor=none;html=1;", 30, 30), 30, 30),
 ("End (activity final)", vertex("final", "", "ellipse;shape=endState;fillColor=#000000;strokeColor=#000000;html=1;", 24, 24), 24, 24),
 ("Fork/join bar, horizontal", vertex("fork", "", "html=1;points=[];perimeter=orthogonalPerimeter;fillColor=#000000;strokeColor=none;", 80, 5), 80, 5),
 ("Fork/join bar, upright", vertex("fork", "", "html=1;points=[];perimeter=orthogonalPerimeter;fillColor=#000000;strokeColor=none;", 5, 80), 5, 80),
 ("Note", vertex("note", "Note", "shape=note;size=12;" + TXT, 140, 60), 140, 60),
 ("Text", vertex("text", "Text", "text;" + TXT, 100, 20), 100, 20),
 ("Lane (a party; drop it on the pool)", vertex("lane", "Party", "swimlane;expand=0;horizontal=1;startSize=24;swimlaneLine=0;collapsible=0;html=1;fillColor=none;fontSize=12;", 250, 600), 250, 600),
 ("Control flow", edge("control", 120), 120, 1),
 ("Object flow (to or from a document)", edge("object", 120), 120, 1),
]
lib = [dict(xml=compress(x), w=w, h=h, title=t, aspect="fixed") for t, x, w, h in items]
open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'tools', 'ubl-library.xml'), 'w').write('<mxlibrary>' + json.dumps(lib) + '</mxlibrary>\n')
print(len(lib), 'shapes')
