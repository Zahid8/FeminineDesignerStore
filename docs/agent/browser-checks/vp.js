const { chromium } = require('playwright');
const [,, url, out, w, h, scrolls] = process.argv;
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: +w || 1440, height: +h || 900 }, isMobile: (+w||1440) < 500, hasTouch: (+w||1440) < 500 });
  p.on('pageerror', e => console.log('pageerror', e.message));
  await p.goto('http://127.0.0.1:8765' + url, { waitUntil: 'networkidle' });
  await p.waitForTimeout(1800);
  for (let i = 0; i < (+scrolls || 0); i++) { await p.mouse.wheel(0, 300); await p.waitForTimeout(120); }
  await p.waitForTimeout(1500);
  await p.screenshot({ path: out });
  await b.close();
})();
