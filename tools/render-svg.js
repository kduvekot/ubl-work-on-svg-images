// Render an SVG to PNG at an exact pixel width, headlessly.
//   node render-svg.js <in.svg> <out.png> <width> [dpi]
//   node render-svg.js --batch <jobs-file>      one job a line: in.svg out.png width [dpi]
// Chromium does not write a pHYs chunk, so the physical resolution is stamped in
// afterwards - an XSL-FO formatter sizing the image by its intrinsic dimensions
// needs it, and the UBL art/ PNGs all carry 600 dpi.
//
// Starting Chromium is most of what one render costs (about a second of the 1.2
// measured), so a batch shares one browser, RENDER_PAGES pages at a time
// (default 4). And a render is kept: it is keyed on the SVG's bytes, the width,
// the dpi and the browser build, so an SVG rendered before - a baseline's, which
// never changes, or one a correction did not touch - is not rendered again. Set
// UBL_RENDER_CACHE to choose where (default ~/.cache/ubl-render), and
// UBL_NO_RENDER_CACHE=1 to bypass it.
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path'), os = require('os'), crypto = require('crypto');
const CHROME = process.env.CHROMIUM_PATH || '/opt/pw-browsers/chromium-1194/chrome-linux/chrome';

const CRC = (() => { const t = new Int32Array(256);
  for (let n = 0; n < 256; n++) { let c = n;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xEDB88320 ^ (c >>> 1) : c >>> 1; t[n] = c; }
  return b => { let c = -1; for (const x of b) c = t[(c ^ x) & 0xFF] ^ (c >>> 8); return (c ^ -1) >>> 0; };
})();

/** insert a pHYs chunk declaring `dpi` right after IHDR */
function stampDpi(png, dpi) {
  const ppm = Math.round(dpi / 0.0254);
  const data = Buffer.alloc(9);
  data.writeUInt32BE(ppm, 0); data.writeUInt32BE(ppm, 4); data[8] = 1;   // unit = metre
  const type = Buffer.from('pHYs');
  const chunk = Buffer.concat([
    Buffer.alloc(4), type, data, Buffer.alloc(4)]);
  chunk.writeUInt32BE(9, 0);
  chunk.writeUInt32BE(CRC(Buffer.concat([type, data])), 4 + type.length + data.length);
  const ihdrEnd = 8 + 12 + png.readUInt32BE(8);      // sig + IHDR
  return Buffer.concat([png.subarray(0, ihdrEnd), chunk, png.subarray(ihdrEnd)]);
}

const CACHE = process.env.UBL_RENDER_CACHE || path.join(os.homedir(), '.cache', 'ubl-render');
const USE_CACHE = !process.env.UBL_NO_RENDER_CACHE;
// what decides the pixels besides the job itself: the browser build, and this
// file (a change to how a render is made must not hit an old one)
const BUILD = (() => {
  const st = fs.statSync(CHROME);
  let pw = '';
  try { pw = require('playwright/package.json').version; } catch (e) {}
  return [CHROME, st.size, st.mtimeMs, pw,
          crypto.createHash('sha1').update(fs.readFileSync(__filename)).digest('hex')].join('|');
})();

function jobOf(svg, out, widthArg, dpiArg) {
  const width = Number(widthArg || 3425);
  // derive the exact pixel height from the viewBox and set it explicitly: with
  // height:auto the browser rounds the computed height UP, giving a 1px overshoot
  const src = fs.readFileSync(path.resolve(svg));
  const vb = /viewBox="[\d.+-]+\s+[\d.+-]+\s+([\d.]+)\s+([\d.]+)"/.exec(src.toString('utf8'));
  const height = vb ? Math.round(width * Number(vb[2]) / Number(vb[1])) : null;
  const key = crypto.createHash('sha1').update(BUILD).update('\0' + width + '\0' + (dpiArg || ''))
    .update('\0').update(src).digest('hex');
  return { svg, out, width, height, dpi: dpiArg ? Number(dpiArg) : null, key };
}

function fromCache(j) {
  if (!USE_CACHE) return false;
  try { fs.copyFileSync(path.join(CACHE, j.key + '.png'), j.out); return true; }
  catch (e) { return false; }
}

function toCache(j, buf) {
  if (!USE_CACHE) return;
  try {
    fs.mkdirSync(CACHE, { recursive: true });
    const tmp = path.join(CACHE, j.key + '.tmp' + process.pid);
    fs.writeFileSync(tmp, buf);
    fs.renameSync(tmp, path.join(CACHE, j.key + '.png'));
  } catch (e) { /* a cache that cannot be written is not an error */ }
}

async function render(browser, j, dir) {
  const page = await browser.newPage({
    viewport: { width: Math.min(j.width + 40, 4000), height: 1200 },
    deviceScaleFactor: 1,
  });
  try {
    const wrap = path.join(dir, j.key + '.html');
    fs.writeFileSync(wrap,
      `<!doctype html><style>html,body{margin:0;background:#fff}
       img{display:block;width:${j.width}px;height:${j.height ? j.height + 'px' : 'auto'}}</style>
       <img id="t" src="file://${path.resolve(j.svg)}">`);
    await page.goto('file://' + wrap);
    await page.waitForFunction(
      () => { const i = document.getElementById('t'); return i && i.complete && i.naturalWidth > 0; },
      null, { timeout: 30000 });
    let buf = await page.locator('#t').screenshot({ timeout: 30000 });
    if (j.dpi) buf = stampDpi(buf, j.dpi);
    fs.writeFileSync(j.out, buf);
    toCache(j, buf);
  } finally {
    await page.close();
  }
}

(async () => {
  const argv = process.argv.slice(2);
  let jobs;
  if (argv[0] === '--batch') {
    jobs = fs.readFileSync(argv[1], 'utf8').split('\n').map(l => l.trim()).filter(Boolean)
      .map(l => jobOf(...l.split(/\s+/)));
  } else {
    if (!argv[0] || !argv[1]) { console.error('usage: node render-svg.js in.svg out.png [width] [dpi] | --batch jobs'); process.exit(2); }
    jobs = [jobOf(...argv)];
  }
  const todo = jobs.filter(j => !fromCache(j));
  let failed = 0;
  if (todo.length) {
    const browser = await chromium.launch({
      executablePath: CHROME,
      args: ['--no-sandbox', '--allow-file-access-from-files'],
    });
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'svgrender-'));
    const lanes = Math.max(1, Number(process.env.RENDER_PAGES || 4));
    let next = 0;
    await Promise.all(Array.from({ length: Math.min(lanes, todo.length) }, async () => {
      while (next < todo.length) {
        const j = todo[next++];
        try { await render(browser, j, dir); }
        catch (e) { failed++; console.error(`  FAILED ${j.svg}: ${e.message}`); }
      }
    }));
    await browser.close();
    fs.rmSync(dir, { recursive: true, force: true });
  }
  for (const j of jobs)
    console.log(`  rendered ${path.basename(j.svg)} -> ${path.basename(j.out)} @ ${j.width}px` +
                (j.height ? `x${j.height}` : '') + (j.dpi ? `, ${j.dpi} dpi` : '') +
                (todo.includes(j) ? '' : ' (cached)'));
  if (failed) process.exit(2);
})().catch(e => { console.error(e.message); process.exit(2); });
