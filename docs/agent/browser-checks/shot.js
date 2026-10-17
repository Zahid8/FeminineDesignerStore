// Usage: node shot.js <outdir> [pages...]
const { chromium } = require('playwright');
const out = process.argv[2] || '/tmp/fdshot/out';
const base = 'http://127.0.0.1:8765';
const fs = require('fs');
fs.mkdirSync(out, { recursive: true });

(async () => {
  const browser = await chromium.launch();
  const ctxD = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const ctxM = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });
  // put something in the cart for both contexts
  let slug = null;
  for (const ctx of [ctxD, ctxM]) {
    const p = await ctx.newPage();
    await p.goto(base + '/shop/');
    const href = await p.getAttribute('.product-item a', 'href');
    slug = href;
    await p.goto(base + href);
    await Promise.all([p.waitForNavigation(), p.evaluate(() => document.querySelector('form[action*="cart/add"]').submit())]);
    await p.close();
  }
  const pages = process.argv.slice(3).length ? process.argv.slice(3) :
    ['/', '/shop/', slug, '/cart/', '/checkout/', '/accounts/login/', '/contact/'];
  for (const [name, ctx] of [['d', ctxD], ['m', ctxM]]) {
    for (const path of pages) {
      const page = await ctx.newPage();
      const errs = [];
      page.on('console', m => { if (m.type() === 'error' || m.type() === 'warning') errs.push(m.type() + ': ' + m.text()); });
      page.on('pageerror', e => errs.push('pageerror: ' + e.message));
      await page.goto(base + path, { waitUntil: 'networkidle' });
      // wheel-scroll through to trigger reveal animations (Lenis ignores scrollTo loops)
      const h = await page.evaluate(() => document.body.scrollHeight);
      for (let y = 0; y < h; y += 500) { await page.mouse.wheel(0, 500); await page.waitForTimeout(90); }
      await page.waitForTimeout(1200);
      await page.evaluate(async () => {
        document.querySelectorAll('img[loading=lazy]').forEach(i => { i.loading = 'eager'; });
        window.scrollTo(0, 0); await new Promise(r => setTimeout(r, 900));
      });
      const file = `${out}/${name}_${path.replace(/[^a-z0-9]+/gi, '_') || 'home'}.jpg`;
      await page.screenshot({ path: file, fullPage: true, type: 'jpeg', quality: 72 });
      console.log(file, errs.length ? '\n  ' + errs.join('\n  ') : '');
      await page.close();
    }
  }
  await browser.close();
})();
