// Export draw.io drawings to what the UBL repository publishes: per figure,
//
//   <out>/images/<figure>.drawio    the drawing itself (the source)
//   <out>/images/<figure>.svg       the vector picture: the revisable file for ISO
//   <out>/art/<figure>.png          print: 600 dpi, at most 3425 px (5.7 in) wide
//   <out>/htmlart/<figure>.png      web: at most 750 px wide
//
// and <out>/export.json, per figure: its natural size, the scale it is fitted
// to the page at, and the size its text prints at.
//
//   node tools/export_drawio.js <out dir> <figure.drawio> ...
//
// Needs Node with playwright (a global install is found through NODE_PATH, see
// tools/drawio_baseline.py) and the Chromium of this environment (CHROMIUM_PATH).
//
// The picture is drawn by draw.io's own code: its viewer, of the release pinned
// in DRAWIO_VERSION, fetched once from that release's tag into
// DRAWIO_VIEWER_CACHE (default ~/.cache/ubl-drawio-viewer). draw.io writes each
// label as HTML in a <foreignObject>, which is not SVG text; the export lets
// the browser lay the label out as draw.io does, reads where each line of it
// lands, and writes those lines as SVG <text> in its place. The rest of the
// picture is draw.io's, cleaned of what only draw.io's editor needs (dark-mode
// colours, the "Text is not SVG" notice, pointer events).
//
// Both PNGs are renders of that SVG, as an image, so they show what the SVG
// shows. Scale: the page is 5.7 in wide, 548 px at 96 px/in; a figure wider is
// fitted to it, a narrower one kept at its natural size (README, "Decided for
// that export").
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path'), os = require('os'), https = require('https');

const DRAWIO_VERSION = '31.5.3';
const VIEWER_URL = 'https://raw.githubusercontent.com/jgraph/drawio/v' + DRAWIO_VERSION +
                   '/src/main/webapp/js/viewer-static.min.js';
const CHROME = process.env.CHROMIUM_PATH || '/opt/pw-browsers/chromium-1194/chrome-linux/chrome';

const PAGE_PX = 548;             // 5.7 in at 96 px/in: the width of the page
const ART_DPI = 600, ART_MAX = 3425, HTML_MAX = 750;
const FONT = "Helvetica, Arial, 'Liberation Sans', sans-serif";

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

// Runs in the page: the drawing's SVG, drawn by draw.io, its labels made SVG text.
function toSvg([xml, name, font, drawioVersion]) {
  const doc = mxUtils.parseXml(xml);
  const graph = new Graph(document.getElementById('g'));
  new mxCodec(doc).decode(doc.getElementsByTagName('mxGraphModel')[0], graph.getModel());
  const svg = graph.getSvg('#ffffff', 1, 0, false, null, true);
  document.body.appendChild(svg);            // laid out, so the labels can be measured
  const NS = 'http://www.w3.org/2000/svg';
  const W = +svg.getAttribute('viewBox').split(' ')[2], H = +svg.getAttribute('viewBox').split(' ')[3];

  const hex = c => '#' + c.match(/\d+/g).slice(0, 3).map(v => (+v).toString(16).padStart(2, '0')).join('');
  const ascent = {};
  const ctx = document.createElement('canvas').getContext('2d');
  function fontAscent(cs) {
    const f = cs.fontStyle + ' ' + cs.fontWeight + ' ' + cs.fontSize + ' ' + cs.fontFamily;
    if (!(f in ascent)) { ctx.font = f; ascent[f] = ctx.measureText('Hg').fontBoundingBoxAscent; }
    return ascent[f];
  }
  // a run of text in one style: what an SVG <tspan> carries
  function styleOf(el, root) {
    const cs = getComputedStyle(el);
    let underline = false;
    for (let e = el; e && e !== root.parentNode; e = e.parentNode)
      if (e.nodeType === 1 && /underline/.test(getComputedStyle(e).textDecorationLine)) underline = true;
    return { weight: +cs.fontWeight >= 600 ? 'bold' : null, italic: cs.fontStyle === 'italic' ? 'italic' : null,
             underline, size: parseFloat(cs.fontSize), fill: hex(cs.color), cs };
  }
  const same = (a, b) => a.weight === b.weight && a.italic === b.italic && a.underline === b.underline &&
                         a.size === b.size && a.fill === b.fill;

  // one label: its lines, each a list of runs, in the coordinates of `local`
  function lines(root, local) {
    const inv = local.getScreenCTM().inverse();
    const pt = svg.createSVGPoint();
    const at = (x, y) => { pt.x = x; pt.y = y; return pt.matrixTransform(inv); };
    const out = [];
    let line = null;
    const range = document.createRange();
    const walk = node => {
      if (node.nodeType === 1 && node.localName === 'br') { line = null; return; }
      if (node.nodeType === 3) {
        const st = styleOf(node.parentNode, root);
        for (let i = 0; i < node.data.length; i++) {
          const ch = node.data[i];
          range.setStart(node, i); range.setEnd(node, i + 1);
          const r = [...range.getClientRects()].find(r => r.width > 0);
          if (/\s/.test(ch)) { if (line) line.chars.push({ ch: ' ', r, st }); continue; }
          if (!r) continue;
          if (!line || r.top > line.top + r.height / 2) { line = { top: r.top, chars: [] }; out.push(line); }
          line.chars.push({ ch, r, st });
        }
        return;
      }
      for (const c of node.childNodes) walk(c);
    };
    walk(root);
    return out.map(l => {
      const ink = l.chars.filter(c => c.ch !== ' ');
      const first = ink[0];
      const left = Math.min(...ink.map(c => c.r.left)), right = Math.max(...ink.map(c => c.r.right));
      const baseline = first.r.top + fontAscent(first.st.cs);
      // spaces: one between words, none at either end
      let s = l.chars.slice(l.chars.indexOf(first), l.chars.lastIndexOf(ink[ink.length - 1]) + 1);
      s = s.filter((c, i) => c.ch !== ' ' || s[i - 1].ch !== ' ');
      const runs = [];
      for (const c of s) {
        const last = runs[runs.length - 1];
        if (last && same(last.st, c.st)) last.text += c.ch; else runs.push({ text: c.ch, st: c.st });
      }
      const p0 = at(left, baseline), p1 = at(right, baseline);
      return { left: p0.x, right: p1.x, baseline: p0.y, runs };
    });
  }

  const report = { labels: 0, lines: 0 };
  for (const sw of [...svg.querySelectorAll('switch')]) {
    const fo = sw.querySelector('foreignObject');
    if (!fo) continue;
    const local = sw.parentNode;
    // measure a turned label unturned: take its turns off, put them back after
    const turned = [];
    for (let e = local; e !== svg; e = e.parentNode) {
      const t = e.getAttribute('transform');
      if (t && /rotate/.test(t)) {
        if (!/^\s*rotate\([^)]*\)\s*$/.test(t)) throw new Error(name + ': a label under ' + t);
        turned.push([e, t]); e.removeAttribute('transform');
      }
    }
    const block = fo.querySelector('div div div') || fo.querySelector('div div') || fo.firstElementChild;
    const align = getComputedStyle(block).textAlign;
    const ls = lines(block, local);
    for (const [e, t] of turned) e.setAttribute('transform', t);
    const words = block.textContent.replace(/\s+/g, ' ').trim();
    const got = ls.map(l => l.runs.map(r => r.text).join('')).join(' ').replace(/\s+/g, ' ').trim();
    if (words.replace(/ /g, '') !== got.replace(/ /g, ''))
      throw new Error(name + ': label "' + words + '" measured as "' + got + '"');
    const g = document.createElementNS(NS, 'g');
    for (const l of ls) {
      const text = document.createElementNS(NS, 'text');
      const anchor = align === 'center' ? 'middle' : (align === 'right' || align === 'end') ? 'end' : 'start';
      const x = anchor === 'middle' ? (l.left + l.right) / 2 : anchor === 'end' ? l.right : l.left;
      const r2 = v => String(Math.round(v * 100) / 100);
      text.setAttribute('x', r2(x));
      text.setAttribute('y', r2(l.baseline));
      text.setAttribute('font-family', font);
      if (anchor !== 'start') text.setAttribute('text-anchor', anchor);
      const base = l.runs[0].st;
      text.setAttribute('font-size', String(base.size));
      text.setAttribute('fill', base.fill);
      const put = (el, st) => {
        if (st.weight) el.setAttribute('font-weight', st.weight);
        if (st.italic) el.setAttribute('font-style', st.italic);
        if (st.underline) el.setAttribute('text-decoration', 'underline');
      };
      if (l.runs.length === 1) { put(text, base); text.textContent = l.runs[0].text; }
      else for (const r of l.runs) {
        const span = document.createElementNS(NS, 'tspan');
        put(span, r.st);
        if (r.st.size !== base.size) span.setAttribute('font-size', String(r.st.size));
        if (r.st.fill !== base.fill) span.setAttribute('fill', r.st.fill);
        span.textContent = r.text;
        text.appendChild(span);
      }
      g.appendChild(text);
      report.lines++;
    }
    sw.parentNode.replaceChild(g, sw);
    report.labels++;
  }

  // what only draw.io's editor needs
  svg.querySelectorAll('style, a, switch, foreignObject').forEach(e => e.remove());
  for (const e of [svg, ...svg.querySelectorAll('*')]) {
    e.removeAttribute('pointer-events');
    const st = e.getAttribute('style');
    if (st !== null) {
      const keep = st.split(';').map(s => s.trim()).filter(s => s && !/light-dark|^background/.test(s));
      if (keep.length) e.setAttribute('style', keep.join('; ')); else e.removeAttribute('style');
    }
    if (e.localName === 'text' && e.getAttribute('font-family') !== font) e.setAttribute('font-family', font);
  }
  svg.removeAttribute('id');
  const bg = svg.querySelector('rect');
  bg.setAttribute('width', String(W)); bg.setAttribute('height', String(H));

  // the page: fitted to 5.7 in, in millimetres
  const scale = Math.min(1, 548 / W);
  const mm = v => String(Math.round(v * scale * 25.4 / 96 * 1000) / 1000) + 'mm';
  svg.setAttribute('width', mm(W));
  svg.setAttribute('height', mm(H));
  const title = document.createElementNS(NS, 'title');
  title.textContent = name;
  svg.insertBefore(title, svg.firstChild);
  svg.insertBefore(document.createComment(
    ' Generated from ' + name + '.drawio by tools/export_drawio.js (draw.io ' + drawioVersion +
    '). Edit ' + name + '.drawio, not this file. '), svg.firstChild);
  const text = '<?xml version="1.0" encoding="UTF-8"?>\n' + new XMLSerializer().serializeToString(svg) + '\n';
  document.body.removeChild(svg);
  return { svg: text, width: W, height: H, scale, ...report };
}

// PNG with its resolution recorded (pHYs), as the print tools size an image by it
function withDpi(png, dpi) {
  const zlib = require('zlib');
  const ppm = Math.round(dpi / 0.0254);
  const data = Buffer.alloc(9);
  data.writeUInt32BE(ppm, 0); data.writeUInt32BE(ppm, 4); data.writeUInt8(1, 8);
  const type = Buffer.from('pHYs');
  const chunk = Buffer.alloc(21);
  chunk.writeUInt32BE(9, 0); type.copy(chunk, 4); data.copy(chunk, 8);
  chunk.writeUInt32BE(zlib.crc32(Buffer.concat([type, data])) >>> 0, 17);
  // drop any pHYs there is, put ours after IHDR (8 byte signature + 25 byte IHDR)
  const parts = [png.subarray(0, 33)];
  for (let o = 33; o < png.length;) {
    const len = png.readUInt32BE(o), t = png.toString('latin1', o + 4, o + 8);
    if (t !== 'pHYs') parts.push(png.subarray(o, o + 12 + len));
    o += 12 + len;
  }
  parts.splice(1, 0, chunk);
  return Buffer.concat(parts);
}

// the SVG drawn as an image at exactly pxW x pxH pixels: at the size of the
// canvas itself, as a screenshot's clip is cut to whole CSS pixels before it is
// scaled, which would lose the drawing's last rows
async function png(browser, svgText, pxW, pxH, dpi, out) {
  const page = await browser.newPage({ viewport: { width: pxW, height: pxH }, deviceScaleFactor: 1 });
  await page.setContent('<!doctype html><html><head><style>html,body{margin:0;background:#fff}' +
    'img{display:block;width:' + pxW + 'px;height:' + pxH + 'px}</style></head><body>' +
    '<img src="data:image/svg+xml;base64,' + Buffer.from(svgText).toString('base64') + '"></body></html>');
  await page.waitForFunction(() => document.images[0].complete);
  const shot = await page.screenshot({ clip: { x: 0, y: 0, width: pxW, height: pxH } });
  await page.close();
  fs.writeFileSync(out, withDpi(shot, dpi));
}

(async () => {
  const [outDir, ...files] = process.argv.slice(2);
  if (!outDir || !files.length) {
    console.error('usage: node tools/export_drawio.js <out dir> <figure.drawio> ...');
    process.exit(2);
  }
  for (const d of ['images', 'art', 'htmlart']) fs.mkdirSync(path.join(outDir, d), { recursive: true });
  const js = await viewer();
  const browser = await chromium.launch({ executablePath: CHROME });
  const draw = await browser.newPage();
  await draw.setContent('<!doctype html><html><body><div id="g"></div></body></html>');
  await draw.addScriptTag({ path: js });
  const version = await draw.evaluate(() => (typeof EditorUi !== 'undefined' && EditorUi.VERSION) || mxClient.VERSION);
  if (version !== DRAWIO_VERSION) throw new Error('draw.io ' + version + ', expected ' + DRAWIO_VERSION);
  const reportFile = path.join(outDir, 'export.json');
  const report = fs.existsSync(reportFile) ? JSON.parse(fs.readFileSync(reportFile, 'utf8')) : {};

  for (const file of files) {
    const name = path.basename(file, '.drawio');
    const r = await draw.evaluate(toSvg, [fs.readFileSync(file, 'utf8'), name, FONT, version]);
    fs.copyFileSync(file, path.join(outDir, 'images', name + '.drawio'));
    fs.writeFileSync(path.join(outDir, 'images', name + '.svg'), r.svg);
    const artW = Math.round(r.width * r.scale * ART_DPI / 96);   // 3425 at the page's width
    const htmlW = Math.round(artW * HTML_MAX / ART_MAX);          // 750 at the page's width
    const tall = w => Math.round(w * r.height / r.width);
    await png(browser, r.svg, artW, tall(artW), ART_DPI, path.join(outDir, 'art', name + '.png'));
    await png(browser, r.svg, htmlW, tall(htmlW), 96, path.join(outDir, 'htmlart', name + '.png'));
    const textPt = Math.round(12 * r.scale * 72 / 96 * 10) / 10;
    report[name] = { width: r.width, height: r.height, scale: Math.round(r.scale * 1000) / 1000,
                     textPt, labels: r.labels, lines: r.lines, art: [artW, tall(artW)], htmlart: [htmlW, tall(htmlW)], drawio: version };
    console.log(name + ': ' + r.width + 'x' + r.height + ' px, scale ' + report[name].scale +
                ', text ' + textPt + ' pt, ' + r.labels + ' labels in ' + r.lines + ' lines');
  }
  fs.writeFileSync(reportFile, JSON.stringify(report, null, 1) + '\n');
  await browser.close();
})().catch(e => { console.error(e.message || e); process.exit(1); });
