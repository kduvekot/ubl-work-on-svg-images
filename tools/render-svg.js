// Render an SVG to PNG at an exact pixel width, headlessly.
//   node render-svg.js <in.svg> <out.png> <width> [dpi]
// Chromium does not write a pHYs chunk, so the physical resolution is stamped in
// afterwards - an XSL-FO formatter sizing the image by its intrinsic dimensions
// needs it, and the UBL art/ PNGs all carry 600 dpi.
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path'), os = require('os');

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

(async () => {
  const [svg, out, widthArg, dpiArg] = process.argv.slice(2);
  if (!svg || !out) { console.error('usage: node render-svg.js in.svg out.png [width]'); process.exit(2); }
  const width = Number(widthArg || 3425);
  // derive the exact pixel height from the viewBox and set it explicitly: with
  // height:auto the browser rounds the computed height UP, giving a 1px overshoot
  const src = fs.readFileSync(path.resolve(svg), 'utf8');
  const vb = /viewBox="[\d.+-]+\s+[\d.+-]+\s+([\d.]+)\s+([\d.]+)"/.exec(src);
  const height = vb ? Math.round(width * Number(vb[2]) / Number(vb[1])) : null;

  const browser = await chromium.launch({
    executablePath: CHROME,
    args: ['--no-sandbox', '--allow-file-access-from-files'],
  });
  const page = await browser.newPage({
    viewport: { width: Math.min(width + 40, 4000), height: 1200 },
    deviceScaleFactor: 1,
  });
  const wrap = path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'svgrender-')), 'w.html');
  fs.writeFileSync(wrap,
    `<!doctype html><style>html,body{margin:0;background:#fff}
     img{display:block;width:${width}px;height:${height ? height + 'px' : 'auto'}}</style>
     <img id="t" src="file://${path.resolve(svg)}">`);
  await page.goto('file://' + wrap);
  await page.waitForFunction(
    () => { const i = document.getElementById('t'); return i && i.complete && i.naturalWidth > 0; },
    null, { timeout: 30000 });
  let buf = await page.locator('#t').screenshot({ timeout: 30000 });
  if (dpiArg) buf = stampDpi(buf, Number(dpiArg));
  fs.writeFileSync(out, buf);
  await browser.close();
  console.log(`  rendered ${path.basename(svg)} -> ${path.basename(out)} @ ${width}px` + (height ? `x${height}` : '') + (dpiArg ? `, ${dpiArg} dpi` : ''));
})().catch(e => { console.error(e.message); process.exit(2); });
