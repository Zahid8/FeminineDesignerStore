const { chromium } = require('playwright');
const base = process.env.SHOP || 'http://127.0.0.1:8766';
const results = []; const ok = (n, c, d = '') => { results.push([c, n]); console.log((c ? 'PASS ' : 'FAIL ') + n + (d ? '  — ' + d : '')); };
(async () => {
  const b = await chromium.launch(); const errs = [];
  const ctx = await b.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, deviceScaleFactor: 2 });
  const p = await ctx.newPage(); p.on('pageerror', e => errs.push(e.message));
  for (const slug of ['rani-pink-floral-brocade-blouse', 'black-sequin-sweetheart-blouse']) {
    await p.goto(`${base}/products/${slug}/`); await Promise.all([p.waitForNavigation(), p.evaluate(() => document.getElementById('pdp-cart-form').submit())]);
  }
  await p.goto(base + '/products/rani-pink-floral-brocade-blouse/', { waitUntil: 'networkidle' });
  await p.fill('[data-delivery-pin]', '400050'); await p.click('[data-delivery-check] button'); await p.waitForTimeout(1500);
  ok('PDP delivery estimate', /Delivery by/.test(await p.textContent('[data-delivery-result]')), await p.textContent('[data-delivery-result]'));
  await p.locator('[data-delivery-check]').screenshot({ path: 'home/bag_pdp_eta.png' });
  await p.goto(base + '/cart/', { waitUntil: 'networkidle' }); await p.waitForTimeout(1500);
  ok('bag shows MRP strike + % off', (await p.$$('.fd-cart-price s')).length >= 1 && (await p.textContent('.fd-off')).includes('% off'), await p.textContent('.fd-off'));
  ok('bag remembers PIN → delivery dates on lines', /Delivery by/.test(await p.textContent('[data-eta-line] span')), await p.textContent('[data-eta-line] span'));
  ok('offers listed', (await p.textContent('.fd-offers')).includes('FESTIVE10'));
  ok('sticky checkout bar', await p.isVisible('[data-sticky-pay]'));
  await p.screenshot({ path: 'home/bag_full.png', fullPage: true });
  await Promise.all([p.waitForNavigation(), p.click('.fd-offers li:has-text("FESTIVE10") button')]);
  ok('coupon applied', (await p.textContent('.fd-coupon-applied')).includes('FESTIVE10'), (await p.textContent('.fd-price-rows')).replace(/\s+/g, ' '));
  await p.fill('#coupon-code', 'nope').catch(() => {});
  await Promise.all([p.waitForNavigation(), p.click('.fd-coupon-applied button')]);
  await p.fill('#coupon-code', 'nope'); await Promise.all([p.waitForNavigation(), p.click('.fd-coupon-form button')]);
  ok('bad coupon message', (await p.textContent('body')).includes('NOPE is not a valid coupon'));
  await Promise.all([p.waitForNavigation(), p.click('.fd-cart-line >> nth=1 >> button:has-text("Save for later")')]);
  ok('save for later', (await p.$$('.fd-cart-line')).length === 1 && (await p.textContent('.fd-saved')).includes('Saved for later (1)'));
  await Promise.all([p.waitForNavigation(), p.click('.fd-saved button:has-text("Move to bag")')]);
  ok('move back to bag', (await p.$$('.fd-cart-line')).length === 2);
  const before = await p.$$eval('.fd-cart-line', a => a.length);
  await Promise.all([p.waitForNavigation(), p.click('.fd-cart-line >> nth=0 >> button:has-text("Move to wishlist")')]);
  ok('move to wishlist removes from bag', (await p.$$('.fd-cart-line')).length === before - 1);
  await p.goto(base + '/wishlist/'); ok('wishlist has it', (await p.$$('.product-item')).length >= 1);
  const w = await p.evaluate(() => document.documentElement.scrollWidth); ok('no sideways scroll', w <= 391, String(w));
  ok('no page errors', errs.length === 0, errs.join(' | '));
  console.log('\nISSUES:', results.filter(r => !r[0]).map(r => r[1]).join('; ') || 'none');
  await b.close();
})();
