// Renders the schematic previews to PNG with the pre-installed Chromium (Playwright).
//   node tools/preview/render.cjs
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');
(async () => {
  const outDir = path.join(__dirname, 'out');
  const imgDir = path.join(__dirname, '..', '..', 'docs', 'img');
  fs.mkdirSync(imgDir, { recursive: true });
  const browser = await chromium.launch();
  for (const f of fs.readdirSync(outDir).filter((x) => x.endsWith('.html'))) {
    const page = await browser.newPage({ viewport: { width: 1500, height: 800 }, deviceScaleFactor: 2 });
    await page.goto('file://' + path.join(outDir, f));
    await page.locator('#wrap').screenshot({ path: path.join(imgDir, f.replace('.html', '.png')) });
    await page.close();
    console.log('rendered', f);
  }
  await browser.close();
})();
