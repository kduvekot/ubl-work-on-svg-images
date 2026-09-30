// Print HTML pages to PDF with Chromium, each page's own @page size.
//   node print.js <page.html> ...          writes <page>.pdf beside each
const { chromium } = require('playwright');
const path = require('path');
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage();
  for (const f of process.argv.slice(2)) {
    await p.goto('file://' + path.resolve(f), { waitUntil: 'load' });
    await p.pdf({ path: f.replace(/\.html$/, '.pdf'), preferCSSPageSize: true, printBackground: true });
  }
  await b.close();
})();
