// Render a .drawio file to PNG with draw.io's own drawing code, headlessly.
//   node render-drawio.js <in.drawio> <out.png> <width|auto> <height|auto> [<scale>] [picture|png]
//
// Where the render starts, its origin, is one of two, named:
//
//   picture  (the default) the drawing's picture, as the export makes it: tools/drawio_picture.js, the one
//            definition the export's SVG and PNGs use too (draw.io's export crop; an illustration's frame), so
//            a render and the exported PNG of a drawing are the same picture, pixel for pixel. <width> and
//            <height> "auto": the picture's size at <scale>, rounded up.
//   png      the coordinates of the UBL PNG the drawing was read from, to compare the two: the frame's
//            ubl-offset (the 78, drawio_from_spec.py), else the page's corner, or, where the drawing reaches
//            above or left of it, its bounds. Used by the comparisons with the original PNGs
//            (history/drawio-edits/diff/, run.sh and sweep.sh here) and by a baseline made before (2026-10-05 and earlier).
//
// Until 2026-10-06 this script had only "png", and used it for every render, while the export cropped as
// draw.io does: the two pictures of a drawing were a unit or more apart, by an amount that differed from
// drawing to drawing (one unit, half the frame line, for the 78; the page's empty margin for a drawing
// with none). tools/drawio_picture.js says it once now.
//
// With DRAWIO_RENDER_DEVICE=1 draw.io draws at scale 1 and the browser enlarges the page to <scale>
// (deviceScaleFactor), and the PNG is cut to <width> x <height>. Zoomed in draw.io's own view, 31.5.3 rounds
// an edge label's place along its flow, and the corners of an orthogonal flow, to device pixels, and 32.0.2
// to model units, so the two draw the same drawing a pixel or so apart; at scale 1 they agree, and so do
// they in this mode. tools/drawio_upgrade.py and tools/drawio_baseline.py compare renders so, and so are the
// renders of the baselines made since 2026-10-06 (history/drawio-edits/diff/one.py); those of 2026-10-05 were not.
//
// The drawing code is draw.io's viewer (viewer-static.min.js) of the release pinned in DRAWIO_VERSION - the
// one tools/export_drawio.js pins, so the renders the baselines are made and held with are of the same
// draw.io as the export - fetched once from that release's tag into DRAWIO_VIEWER_CACHE (default
// ~/.cache/ubl-drawio-viewer).
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path'), os = require('os'), https = require('https');
const PINNED_CHROME = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome';
const CHROME = process.env.CHROMIUM_PATH || (fs.existsSync(PINNED_CHROME) ? PINNED_CHROME : undefined);
// the pin, as tools/export_drawio.js (tools/drawio-version.json; DRAWIO_VERSION in the environment overrides it);
// not the live viewer.diagrams.net, which moves on
const DRAWIO_VERSION = process.env.DRAWIO_VERSION || require('../../tools/drawio-version.json').version;
const VIEWER_URL = 'https://raw.githubusercontent.com/jgraph/drawio/v' + DRAWIO_VERSION +
                   '/src/main/webapp/js/viewer-static.min.js';
const PICTURE = require('../../tools/drawio_picture.js').source;

function fetch(url, dest) {
  return new Promise((ok, fail) => {
    https.get(url, res => {
      if (res.statusCode !== 200) return fail(new Error(url + ': HTTP ' + res.statusCode));
      const out = fs.createWriteStream(dest + '.part');
      res.pipe(out);
      out.on('finish', () => { out.close(); fs.renameSync(dest + '.part', dest); ok(dest); });
    }).on('error', fail);
  });
}

async function viewer() {
  const dir = process.env.DRAWIO_VIEWER_CACHE || path.join(os.homedir(), '.cache', 'ubl-drawio-viewer');
  fs.mkdirSync(dir, { recursive: true });
  const file = path.join(dir, 'viewer-' + DRAWIO_VERSION + '.min.js');
  if (!fs.existsSync(file)) await fetch(VIEWER_URL, file);
  return file;
}

// In the page: the drawing decoded into a graph in #g, and where the render starts ([x, y] in the drawing's
// units) with the picture's size
function place([xml, origin]) {
  const doc = mxUtils.parseXml(xml);
  const model = doc.getElementsByTagName('mxGraphModel')[0];
  const graph = new Graph(document.getElementById('g'));
  graph.setEnabled(false);
  graph.gridEnabled = false;
  graph.pageVisible = false;
  new mxCodec(model.ownerDocument).decode(model, graph.getModel());
  window.graph = graph;
  if (origin === 'png') {
    // the PNG's coordinates: the drawing sits one margin in from the page's corner (the frame's ubl-offset,
    // drawio_from_spec.py); a drawing with no frame, at the page's corner, or moved in where it reaches left
    // of or above it (Business Information), so that it is on the canvas whole
    const frame = doc.querySelector('object[ubl-kind="frame"]');
    if (frame) {
      const m = +(frame.getAttribute('ubl-offset') || 0);
      return { at: [m, m] };
    }
    graph.view.scaleAndTranslate(1, 0, 0);
    const b = graph.getGraphBounds();
    return { at: [Math.min(0, b.x), Math.min(0, b.y)] };
  }
  const p = drawioPicture(graph, doc);
  return { at: [p.x, p.y], size: [p.width, p.height] };
}

(async () => {
  const [inp, out, W, H, SC, ORIGIN] = process.argv.slice(2);
  const s = +(SC || 1), origin = ORIGIN || 'picture';
  if (!['picture', 'png'].includes(origin)) throw new Error('origin: picture or png, not ' + origin);
  const xml = fs.readFileSync(inp, 'utf8');
  const js = await viewer();
  const browser = await chromium.launch({ executablePath: CHROME });
  let w = W, h = H;
  if (W === 'auto' || H === 'auto') {
    // the picture's size, from a page of its own (the render's page is sized before the drawing is in it)
    if (origin !== 'picture') throw new Error('auto: the picture\'s size, for the origin "picture" only');
    const p = await browser.newPage();
    await p.setContent('<!doctype html><html><body><div id="g"></div></body></html>');
    await p.addScriptTag({ path: js });
    await p.addScriptTag({ content: PICTURE });
    const { size } = await p.evaluate(place, [xml, origin]);
    await p.close();
    if (W === 'auto') w = Math.ceil(size[0] * s - 1e-6);
    if (H === 'auto') h = Math.ceil(size[1] * s - 1e-6);
  }
  // rounded as tools/render-svg.js rounds the SVG's height, so the two match
  w = Math.round(+w); h = Math.round(+h);
  const dev = !!process.env.DRAWIO_RENDER_DEVICE;       // draw.io draws at scale 1; the browser enlarges
  const cw = dev ? Math.ceil(w / s) : w, ch = dev ? Math.ceil(h / s) : h;
  const page = await browser.newPage(dev ? { viewport: { width: cw, height: ch }, deviceScaleFactor: s } : { viewport: { width: w, height: h } });
  await page.setContent('<!doctype html><html><head><style>html,body{margin:0;background:#fff}' +
    '#g{position:absolute;left:0;top:0;width:' + cw + 'px;height:' + ch + 'px;overflow:hidden}' +
    '</style></head><body><div id="g"></div></body></html>');
  await page.addScriptTag({ path: js });
  await page.addScriptTag({ content: PICTURE });
  const { at } = await page.evaluate(place, [xml, origin]);
  const version = await page.evaluate(([at, s, dev]) => {
    window.graph.view.scaleAndTranslate(dev ? 1 : s, -at[0], -at[1]);
    return (typeof EditorUi !== 'undefined' && EditorUi.VERSION) || mxClient.VERSION;
  }, [at, s, dev]);
  if (version !== DRAWIO_VERSION) throw new Error('draw.io ' + version + ', expected ' + DRAWIO_VERSION);
  await page.waitForTimeout(200);
  if (!dev) await page.screenshot({ path: out, clip: { x: 0, y: 0, width: w, height: h } });
  else {
    // the browser clips to whole CSS pixels, so take the whole page (cw x ch CSS px, at least w x h device
    // pixels) and cut it to the canvas, white where the page is short of it
    const shot = await page.screenshot({ clip: { x: 0, y: 0, width: cw, height: ch } });
    const cut = await browser.newPage({ viewport: { width: 64, height: 64 } });
    const b64 = await cut.evaluate(async ([src, w, h]) => {
      const img = new Image(); img.src = src; await img.decode();
      const c = document.createElement('canvas'); c.width = w; c.height = h;
      const x = c.getContext('2d'); x.fillStyle = '#fff'; x.fillRect(0, 0, w, h); x.drawImage(img, 0, 0);
      return c.toDataURL('image/png').split(',')[1];
    }, ['data:image/png;base64,' + shot.toString('base64'), w, h]);
    fs.writeFileSync(out, Buffer.from(b64, 'base64'));
  }
  await browser.close();
  console.log('  rendered ' + path.basename(inp) + ' -> ' + path.basename(out) +
              ' @ ' + w + 'x' + h + ', from ' + at.map(v => Math.round(v * 100) / 100).join(',') + ' (' + origin + ', draw.io ' + version + ')');
})().catch(e => { console.error(e); process.exit(1); });
