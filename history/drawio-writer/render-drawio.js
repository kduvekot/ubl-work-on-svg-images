// Render a .drawio file to PNG with draw.io's own drawing code, headlessly.
//   node render-drawio.js <in.drawio> <out.png> <width> <height> [<scale>]
//
// With DRAWIO_RENDER_DEVICE=1 draw.io draws at scale 1 and the browser enlarges the page to <scale>
// (deviceScaleFactor), and the PNG is cut to <width> x <height>. Zoomed in draw.io's own view, 31.5.3 rounds
// an edge label's place along its flow, and the corners of an orthogonal flow, to device pixels, and 32.0.2
// to model units, so the two draw the same drawing a pixel or so apart; at scale 1 they agree, and so do
// they in this mode. tools/drawio_upgrade.py and tools/drawio_baseline.py compare render so, and so are the
// renders of the baseline 2026-10-06 made (history/drawio-edits/diff/one.py); those of 2026-10-05 were not.
//
// The drawing code is draw.io's viewer (viewer-static.min.js) of the release
// pinned in DRAWIO_VERSION - the one tools/export_drawio.js pins, so the renders
// the baselines are made and held with are of the same draw.io as the export -
// fetched once from that release's tag into DRAWIO_VIEWER_CACHE (default
// ~/.cache/ubl-drawio-viewer) and loaded into the same Chromium that renders
// the SVGs (tools/render-svg.js). The model is drawn at scale 1 with its
// frame where the SVG has it, so the PNG lines up with the SVG's render
// pixel for pixel: the canvas is <width> x <height>, the size of the SVG's
// render. A figure drawn at its natural scale is drawn at <scale> (the SVG's
// width / its own), so it lines up with the SVG's render.
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path'), os = require('os'), https = require('https');
const CHROME = process.env.CHROMIUM_PATH || '/opt/pw-browsers/chromium-1194/chrome-linux/chrome';
// the pin, as tools/export_drawio.js (tools/drawio-version.json; DRAWIO_VERSION in the environment overrides it);
// not the live viewer.diagrams.net, which moves on
const DRAWIO_VERSION = process.env.DRAWIO_VERSION || require('../../tools/drawio-version.json').version;
const VIEWER_URL = 'https://raw.githubusercontent.com/jgraph/drawio/v' + DRAWIO_VERSION +
                   '/src/main/webapp/js/viewer-static.min.js';

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

(async () => {
  const [inp, out, W, H, SC] = process.argv.slice(2);
  const s = +(SC || 1);
  // rounded as tools/render-svg.js rounds the SVG's height, so the two match
  const w = Math.round(+W), h = Math.round(+H);
  const js = await viewer();
  const browser = await chromium.launch({ executablePath: CHROME });
  const dev = !!process.env.DRAWIO_RENDER_DEVICE;       // draw.io draws at scale 1; the browser enlarges
  const cw = dev ? Math.ceil(w / s) : w, ch = dev ? Math.ceil(h / s) : h;
  const page = await browser.newPage(dev ? { viewport: { width: cw, height: ch }, deviceScaleFactor: s } : { viewport: { width: w, height: h } });
  await page.setContent('<!doctype html><html><head><style>html,body{margin:0;background:#fff}' +
    '#g{position:absolute;left:0;top:0;width:' + cw + 'px;height:' + ch + 'px;overflow:hidden}' +
    '</style></head><body><div id="g"></div></body></html>');
  await page.addScriptTag({ path: js });
  const version = await page.evaluate(([xml, s, dev]) => {
    const doc = mxUtils.parseXml(xml);
    const model = doc.getElementsByTagName('mxGraphModel')[0];
    const graph = new Graph(document.getElementById('g'));
    graph.setEnabled(false);
    graph.gridEnabled = false;
    graph.pageVisible = false;
    new mxCodec(model.ownerDocument).decode(model, graph.getModel());
    // the drawing sits one margin in from the page's corner (the frame's
    // ubl-offset, drawio_from_spec.py): take it off, so the render lines up
    // with the SVG's
    const frame = doc.querySelector('object[ubl-kind="frame"]');
    const m = frame ? +(frame.getAttribute('ubl-offset') || 0) : 0;
    let tx = -m, ty = -m;
    if (!frame) {
      // a drawing with no frame (an illustration, a figure drawn later: the TC's own) whose cells reach left
      // of or above its origin (Business Information): moved in so that it is on the canvas whole
      graph.view.scaleAndTranslate(1, 0, 0);
      const b = graph.getGraphBounds();
      tx = Math.max(0, -b.x); ty = Math.max(0, -b.y);
    }
    graph.view.scaleAndTranslate(dev ? 1 : s, tx, ty);
    return (typeof EditorUi !== 'undefined' && EditorUi.VERSION) || mxClient.VERSION;
  }, [fs.readFileSync(inp, 'utf8'), s, dev]);
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
              ' @ ' + w + 'x' + h + ' (draw.io ' + version + ')');
})().catch(e => { console.error(e); process.exit(1); });
