// Route a figure's flows with libavoid, the orthogonal connector router of
// the adaptagrams project (Wybrow, Marriott, Stuckey; as in Inkscape and
// Dunnart), through its WebAssembly build libavoid-js (LGPL-2.1).
//
//   node avoid_route.mjs < job.json > routes.json
//
// job: { params: {...}, shapes: [{id, x, y, w, h, pins: [{cls, fx, fy, dir,
//        exclusive}]}], conns: [{id, src: {shape, cls} | {point: [x, y]},
//        dst: likewise}] }
// routes: { <conn id>: [[x, y], ...] }
//
// A shape is an obstacle the routes keep a buffer from; a pin is a point on
// its outline (fx, fy: fractions of its box) that a route may leave or meet
// it by, in the direction dir (1 up, 2 down, 4 left, 8 right). A connector
// ends on a class of pins, and libavoid chooses the pin. All connectors are
// routed together: libavoid then nudges parallel stretches apart, and orders
// them so they cross as little as they can.
import { AvoidLib } from 'libavoid-js';
import fs from 'fs';

const job = JSON.parse(fs.readFileSync(0, 'utf8'));
await AvoidLib.load();
const A = AvoidLib.getInstance();
const router = new A.Router(A.RouterFlag.OrthogonalRouting.value);
const P = job.params || {};
for (const [k, v] of Object.entries(P.parameters || {})) router.setRoutingParameter(A.RoutingParameter[k], v);
for (const [k, v] of Object.entries(P.options || {})) router.setRoutingOption(A.RoutingOption[k], v);

const shapes = {};
for (const s of job.shapes) {
  const ref = new A.ShapeRef(router, new A.Rectangle(new A.Point(s.x, s.y), new A.Point(s.x + s.w, s.y + s.h)));
  shapes[s.id] = ref;
  for (const p of s.pins || []) {
    const pin = new A.ShapeConnectionPin(ref, p.cls, p.fx, p.fy, true, 0, p.dir);
    pin.setExclusive(!!p.exclusive);
    if (p.cost) pin.setConnectionCost(p.cost);
  }
}
const conns = {};
for (const c of job.conns) {
  // an end is a class of pins on a shape, or a free point
  const end = e => e.point ? new A.ConnEnd(new A.Point(e.point[0], e.point[1]))
                           : new A.ConnEnd(shapes[e.shape], e.cls);
  const ref = new A.ConnRef(router, end(c.src), end(c.dst));
  ref.setRoutingType(A.ConnType.ConnType_Orthogonal);
  conns[c.id] = ref;
}
router.processTransaction();
const out = {};
for (const [id, ref] of Object.entries(conns)) {
  const pl = ref.displayRoute();
  const pts = [];
  for (let i = 0; i < pl.size(); i++) { const p = pl.at(i); pts.push([p.x, p.y]); }
  out[id] = pts;
}
process.stdout.write(JSON.stringify(out));
