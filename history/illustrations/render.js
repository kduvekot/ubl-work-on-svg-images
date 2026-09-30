// Renders a .drawio with draw.io's own code (the viewer of release 31.5.3, as
// tools/export_drawio.js pins it) onto a W x H canvas: the drawing's point
// (x, y) lands at (x * s + dx, y * s + dy).
//   node render.js <in.drawio> <out.png> <W> <H> <s> <dx> <dy>
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path'), os = require('os');
const JS = path.join(process.env.DRAWIO_VIEWER_CACHE || path.join(os.homedir(), '.cache', 'ubl-drawio-viewer'), 'viewer-31.5.3.min.js');
const https = require('https');
const VIEWER_URL = 'https://raw.githubusercontent.com/jgraph/drawio/v31.5.3/src/main/webapp/js/viewer-static.min.js';
const CHROME = process.env.CHROMIUM_PATH || '/opt/pw-browsers/chromium-1194/chrome-linux/chrome';
// draw.io's viewer of the release tools/export_drawio.js pins, fetched once into its cache
function viewer() {
  if (fs.existsSync(JS)) return Promise.resolve(JS);
  fs.mkdirSync(path.dirname(JS), { recursive: true });
  return new Promise((ok, fail) => https.get(VIEWER_URL, res => {
    if (res.statusCode !== 200) return fail(new Error(VIEWER_URL + ': HTTP ' + res.statusCode));
    const out = fs.createWriteStream(JS + '.part'); res.pipe(out);
    out.on('finish', () => { out.close(); fs.renameSync(JS + '.part', JS); ok(JS); });
  }).on('error', fail));
}

(async () => {
  await viewer();
  const [inp, out, W, H, S, DX, DY] = process.argv.slice(2);
  const w = Math.round(+W), h = Math.round(+H), s = +S;
  const browser = await chromium.launch({ executablePath: CHROME });
  const page = await browser.newPage({ viewport: { width: w, height: h } });
  await page.setContent('<!doctype html><html><head><style>html,body{margin:0;background:#fff}' +
    '#g{position:absolute;left:0;top:0;width:' + w + 'px;height:' + h + 'px;overflow:hidden}' +
    '</style></head><body><div id="g"></div></body></html>');
  await page.addScriptTag({ path: JS });
  await page.evaluate(([xml, s, dx, dy]) => {
    const doc = mxUtils.parseXml(xml);
    const graph = new Graph(document.getElementById('g'));
    graph.setEnabled(false); graph.gridEnabled = false; graph.pageVisible = false;
    new mxCodec(doc).decode(doc.getElementsByTagName('mxGraphModel')[0], graph.getModel());
    graph.view.scaleAndTranslate(s, dx / s, dy / s);
  }, [fs.readFileSync(inp, 'utf8'), s, +DX, +DY]);
  await page.waitForTimeout(400);
  await page.screenshot({ path: out, clip: { x: 0, y: 0, width: w, height: h } });
  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });
