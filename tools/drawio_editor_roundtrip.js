// Open drawings in draw.io's own editor and save them again, headlessly: what a person does in the editor, to see
// what the editor does to our files.
//
//   node tools/drawio_editor_roundtrip.js <out dir> <figure.drawio> ...
//
// Loads the live editor (embed.diagrams.net, so the newest version, which can be ahead of any tag) in Chromium, sends
// each drawing to it through its embed protocol (postMessage, JSON), asks it to export the drawing as XML (what its
// Save writes), and writes <out dir>/<figure>.drawio and <out dir>/editor-version.txt. tools/drawio_upgrade.py
// --editor compares what came back with what went in.
//
// Needs the proxy's CA in the browser's trust store (README, "Upgrading draw.io"); the proxy is used if HTTPS_PROXY is set.
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path');
const CHROME = process.env.CHROMIUM_PATH || '/opt/pw-browsers/chromium-1194/chrome-linux/chrome';
const URL = 'https://embed.diagrams.net/?embed=1&proto=json&spin=0&ui=min&modified=0&saveAndExit=0';

async function roundtrip(browser, xml) {
  const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });
  const wait = async (event, ms) => {
    const t = Date.now();
    for (;;) {
      const m = await page.evaluate(ev => window.__msgs.find(x => x.event === ev) || null, event);
      if (m) return m;
      if (Date.now() - t > ms) throw new Error('no "' + event + '" from the editor in ' + ms / 1000 + ' s');
      await page.waitForTimeout(100);
    }
  };
  // the editor runs in an iframe of a page of ours, as it is embedded, and talks to it by postMessage
  const send = msg => page.evaluate(m => document.getElementById('ed').contentWindow.postMessage(JSON.stringify(m), '*'), msg);
  await page.setContent('<!doctype html><html><body style="margin:0"><script>window.__msgs = [];' +
    'addEventListener("message", e => { try { window.__msgs.push(JSON.parse(e.data)); } catch (_) {} });</script><iframe id="ed" style="width:1400px;height:900px;border:0" src="' + URL + '"></iframe></body></html>');
  await wait('init', 90000);
  const version = await page.frames().find(f => f.url().startsWith('https://embed.diagrams.net'))
    .evaluate(() => (typeof EditorUi !== 'undefined' && EditorUi.VERSION) || '?');
  await send({ action: 'load', xml, autosave: 0 });
  await wait('load', 60000);
  await page.waitForTimeout(500);
  await send({ action: 'export', format: 'xml' });
  const out = await wait('export', 60000);
  await page.close();
  return { version, data: out.data || out.xml };
}

(async () => {
  const [outDir, ...files] = process.argv.slice(2);
  if (!outDir || !files.length) { console.error('usage: node tools/drawio_editor_roundtrip.js <out dir> <figure.drawio> ...'); process.exit(2); }
  fs.mkdirSync(outDir, { recursive: true });
  const proxy = process.env.HTTPS_PROXY ? { server: process.env.HTTPS_PROXY } : undefined;
  const browser = await chromium.launch({ executablePath: CHROME, proxy });
  let version = '?', next = 0, failed = 0;
  const lane = async () => {
    while (next < files.length) {
      const file = files[next++], name = path.basename(file, '.drawio');
      try {
        const r = await roundtrip(browser, fs.readFileSync(file, 'utf8'));
        version = r.version;
        fs.writeFileSync(path.join(outDir, name + '.drawio'), r.data);
        console.log(name + ': saved by draw.io ' + r.version);
      } catch (e) { failed++; console.log(name + ': FAILED ' + (e.message || e)); }
    }
  };
  await Promise.all([lane(), lane(), lane()]);
  fs.writeFileSync(path.join(outDir, 'editor-version.txt'), version + '\n');
  await browser.close();
  process.exit(failed ? 1 : 0);
})().catch(e => { console.error(e.message || e); process.exit(1); });
