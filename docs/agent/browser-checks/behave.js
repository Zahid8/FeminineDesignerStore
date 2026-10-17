const { chromium } = require('playwright');
const base = 'http://127.0.0.1:8765';
(async () => {
  const b = await chromium.launch(); const ctx = await b.newContext({ viewport: { width: 1440, height: 900 } });
  const p = await ctx.newPage(); const errs = []; p.on('pageerror', e => errs.push(e.message));
  await p.goto(base + '/shop/'); const href = await p.getAttribute('.product-item a', 'href');
  await p.goto(base + href, { waitUntil: 'networkidle' });
  const q = '#quantity';
  await p.click('[data-action=dec]'); const a = await p.inputValue(q);
  for (let i = 0; i < 15; i++) await p.click('[data-action=inc]'); const max = await p.getAttribute(q, 'max'); const bVal = await p.inputValue(q);
  await p.fill(q, ''); await p.dispatchEvent(q, 'change'); const c = await p.inputValue(q);
  console.log('pdp stepper: dec-from-1 =', a, '| inc x15 =', bVal, '(max', max + ') | invalid->', c, '| url unchanged', p.url().endsWith(href));
  await Promise.all([p.waitForNavigation(), p.evaluate(() => document.querySelector('form[action*="cart/add"]').submit())]);
  await p.goto(base + '/cart/', { waitUntil: 'networkidle' });
  const sel = '.fd-cart-line .qty-input';
  await p.fill(sel, '1'); await p.click('.fd-cart-line [data-action=dec]'); console.log('cart dec 1 ->', await p.inputValue(sel));
  await p.screenshot({ path: '/tmp/fdshot/cart.png' });
  // search focus (desktop trigger)
  await p.click('.fd-util-right .search-button'); await p.waitForTimeout(400);
  const vis = await p.evaluate(() => document.querySelector('.search-popup').classList.contains('is-visible'));
  const focused = await p.evaluate(() => document.activeElement.name);
  await p.keyboard.press('Escape'); await p.waitForTimeout(200);
  const after = await p.evaluate(() => ({ vis: document.querySelector('.search-popup').classList.contains('is-visible'), focusDesktop: document.activeElement.classList.contains('search-button') }));
  console.log('search: visible', vis, 'focused', focused, '| after Esc', JSON.stringify(after));
  // toasts: trigger a message (empty-cart checkout path not needed) — check offcanvas cart opens
  await p.click('.fd-util-right [data-bs-target="#offcanvasCart"]'); await p.waitForTimeout(600);
  console.log('offcanvas cart shown', await p.evaluate(() => document.getElementById('offcanvasCart').classList.contains('show')));
  await p.screenshot({ path: '/tmp/fdshot/offcanvas.png' });
  // mobile menu
  const m = await b.newPage({ viewport: { width: 390, height: 844 } });
  await m.goto(base + '/', { waitUntil: 'networkidle' }); await m.click('.fd-hamburger'); await m.waitForTimeout(600);
  console.log('mobile menu shown', await m.evaluate(() => document.getElementById('offcanvasNavbar').classList.contains('show')));
  await m.screenshot({ path: '/tmp/fdshot/mmenu.png' });
  // broken-image fallback on home
  const h = await b.newPage({ viewport: { width: 1440, height: 900 } });
  await h.goto(base + '/', { waitUntil: 'networkidle' });
  console.log('fallback imgs', await h.evaluate(() => [...document.querySelectorAll('img[data-fd-fallback]')].map(i => i.src.split('/').pop())));
  // customize anchor with Lenis active
  await p.goto(base + href, { waitUntil: 'networkidle' });
  await p.click('a[href="#customize-section"]'); await p.waitForTimeout(1200);
  console.log('customize anchor top', await p.evaluate(() => Math.round(document.getElementById('customize-section').getBoundingClientRect().top)));
  // no-JS render
  const nj = await b.newContext({ viewport: { width: 1440, height: 900 }, javaScriptEnabled: false });
  const n = await nj.newPage(); await n.goto(base + '/', { waitUntil: 'networkidle' });
  await n.screenshot({ path: (process.env.OUT || '/tmp/fdshot') + '/nojs_home.png', fullPage: true });
  console.log('nojs hidden reveal', await n.evaluate(() => [...document.querySelectorAll('[data-reveal]')].filter(e => getComputedStyle(e).opacity === '0').length));
  // v2: sort select, density toggle, sticky buy bar, live search, mega menu
  const s2 = await b.newPage({ viewport: { width: 1440, height: 900 } }); const e2 = []; s2.on('pageerror', e => e2.push(e.message));
  await s2.goto(base + '/shop/', { waitUntil: 'networkidle' });
  await Promise.all([s2.waitForNavigation(), s2.selectOption('#sort', 'price_asc')]);
  console.log('sort url', s2.url(), '| first price', await s2.locator('.product-price .fd-price').first().textContent());
  await s2.click('.fd-density button[aria-label="Large grid"]'); await s2.waitForTimeout(200);
  console.log('density attr', await s2.getAttribute('.fd-grid', 'data-density'), '| stored', await s2.evaluate(() => localStorage.getItem('fd-density')));
  await s2.hover('.indichic-nav .nav-link[aria-controls="fd-mega"]'); await s2.waitForTimeout(500);
  console.log('mega open', await s2.evaluate(() => document.getElementById('fd-mega').classList.contains('is-open')));
  await s2.click('.fd-util-right .search-button'); await s2.waitForTimeout(400);
  await s2.type('#search-form', 'blouse'); await s2.waitForTimeout(1500);
  console.log('live search cards', await s2.locator('[data-search-results] .product-item').count(), '|', await s2.textContent('[data-search-status]'));
  const m2 = await b.newPage({ viewport: { width: 390, height: 844 } });
  await m2.goto(base + href, { waitUntil: 'networkidle' });
  const sbBefore = await m2.evaluate(() => document.querySelector('[data-sticky-buy]').classList.contains('is-visible'));
  for (let i = 0; i < 12; i++) { await m2.mouse.wheel(0, 300); await m2.waitForTimeout(80); } await m2.waitForTimeout(600);
  const sbAfter = await m2.evaluate(() => document.querySelector('[data-sticky-buy]').classList.contains('is-visible'));
  console.log('sticky buy before/after scroll', sbBefore, sbAfter);
  console.log('errors2', e2);
  console.log('errors', errs);
  await b.close();
})();
