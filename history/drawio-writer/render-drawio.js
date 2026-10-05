// Render a .drawio file to PNG with draw.io's own drawing code, headlessly.
//   node render-drawio.js <in.drawio> <out.png> <width> <height> [<scale>]
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
const DRAWIO_VERSION = '31.5.3';   // as tools/export_drawio.js; not the live viewer.diagrams.net, which moves on
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
  const page = await browser.newPage({ viewport: { width: w, height: h } });
  await page.setContent('<!doctype html><html><head><style>html,body{margin:0;background:#fff}' +
    '#g{position:absolute;left:0;top:0;width:' + w + 'px;height:' + h + 'px;overflow:hidden}' +
    '</style></head><body><div id="g"></div></body></html>');
  await page.addScriptTag({ path: js });
  const version = await page.evaluate(([xml, s]) => {
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
    graph.view.scaleAndTranslate(s, -m, -m);
    return (typeof EditorUi !== 'undefined' && EditorUi.VERSION) || mxClient.VERSION;
  }, [fs.readFileSync(inp, 'utf8'), s]);
  if (version !== DRAWIO_VERSION) throw new Error('draw.io ' + version + ', expected ' + DRAWIO_VERSION);
  await page.waitForTimeout(200);
  await page.screenshot({ path: out, clip: { x: 0, y: 0, width: w, height: h } });
  await browser.close();
  console.log('  rendered ' + path.basename(inp) + ' -> ' + path.basename(out) +
              ' @ ' + w + 'x' + h + ' (draw.io ' + version + ')');
})().catch(e => { console.error(e); process.exit(1); });
