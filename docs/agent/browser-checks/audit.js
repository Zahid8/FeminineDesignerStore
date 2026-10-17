// Full-page audit captures of every customer page at desktop + mobile (demo server :8766).
const { chromium } = require('playwright');
const fs = require('fs');
const out = process.argv[2]; fs.mkdirSync(out, { recursive: true });
const base = 'http://127.0.0.1:8766';
(async () => {
  const b = await chromium.launch();
  for (const [tag, opts] of [['d', { viewport: { width: 1440, height: 900 } }], ['m', { viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true }]]) {
    const ctx = await b.newContext(opts);
    const p = await ctx.newPage();
    // seed: add item to cart, save a wishlist item, sign in via OTP later not needed
    await p.goto(base + '/shop/'); const href = await p.getAttribute('.product-item a', 'href');
    await p.goto(base + href);
    await Promise.all([p.waitForNavigation(), p.evaluate(() => document.getElementById('pdp-cart-form').submit())]);
    await p.goto(base + '/wishlist/toggle/' + href.split('/').filter(Boolean).pop() + '/').catch(() => {});
    const pages = ['/', '/shop/', href, '/cart/', '/checkout/', '/wishlist/', '/accounts/login/', '/accounts/register/', '/accounts/login/phone/', '/contact/', '/faq/', '/pages/shipping-policy/', '/book-appointment/', '/track-order/', '/no-such-page/'];
    for (const path of pages) {
      await p.goto(base + path, { waitUntil: 'networkidle' });
      const h = await p.evaluate(() => document.body.scrollHeight);
      for (let y = 0; y < h; y += 500) { await p.mouse.wheel(0, 500); await p.waitForTimeout(60); }
      await p.waitForTimeout(800);
      await p.evaluate(() => { document.querySelectorAll('img[loading=lazy]').forEach(i => { i.loading = 'eager'; }); window.scrollTo(0, 0); });
      await p.waitForTimeout(600);
      await p.screenshot({ path: `${out}/${tag}_${path.replace(/[^a-z0-9]+/gi, '_').replace(/^_|_$/g, '') || 'home'}.jpg`, fullPage: true, type: 'jpeg', quality: 70 });
    }
    // cart drawer + search popup
    await p.goto(base + '/', { waitUntil: 'networkidle' });
    await p.click('[data-bs-target="#offcanvasCart"]'); await p.waitForTimeout(700);
    await p.screenshot({ path: `${out}/${tag}_drawer.jpg`, type: 'jpeg', quality: 70 });
    await p.keyboard.press('Escape'); await p.waitForTimeout(500);
    await p.click('.search-button'); await p.waitForTimeout(400); await p.type('#search-form', 'silk'); await p.waitForTimeout(1200);
    await p.screenshot({ path: `${out}/${tag}_search.jpg`, type: 'jpeg', quality: 70 });
    await ctx.close();
  }
  await b.close(); console.log('done');
})();
