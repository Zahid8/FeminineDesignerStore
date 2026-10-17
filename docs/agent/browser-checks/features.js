// T30 feature walkthrough against the demo server (port 8766).
// Usage: node features.js <screenshot-dir> <server-log-file>
const { chromium } = require('playwright');
const fs = require('fs');
const out = process.argv[2];
const serverLog = process.argv[3];
const base = 'http://127.0.0.1:8766';
const shot = (p, name) => p.screenshot({ path: `${out}/${name}.jpg`, type: 'jpeg', quality: 70 });

(async () => {
  const b = await chromium.launch();
  const ctx = await b.newContext({ viewport: { width: 1440, height: 900 } });
  const p = await ctx.newPage();
  const errs = [];
  p.on('pageerror', e => errs.push(e.message));
  const log = (...a) => console.log(...a);

  // Wishlist heart (no reload)
  await p.goto(base + '/shop/', { waitUntil: 'networkidle' });
  const navBefore = await p.evaluate(() => performance.getEntriesByType('navigation').length);
  await p.locator('.product-item').first().hover();
  await p.locator('.fd-card-wish button').first().click();
  await p.waitForTimeout(600);
  log('wishlist: pressed', await p.getAttribute('.fd-card-wish button >> nth=0', 'aria-pressed'),
      '| header count', await p.textContent('[data-wishlist-count]'),
      '| same page', p.url().endsWith('/shop/'));

  // Filter drawer + chips
  await p.click('button[aria-controls="fd-filters"]');
  await p.waitForTimeout(500);
  await shot(p, 'd_shop_filters');
  await p.check('#fd-filters input[name="in_stock"]');
  await p.click('#fd-filters label[for^="f-size-"]:text-is("M")');
  await Promise.all([p.waitForNavigation(), p.click('#fd-filters button[type=submit]')]);
  log('filters: url', p.url().replace(base, ''), '| chips', await p.locator('.fd-chip').count(),
      '|', await p.textContent('.fd-result-meta'));
  await shot(p, 'd_shop_filtered');

  // PDP: size guide, low stock, dispatch, tabs
  const href = await p.getAttribute('.product-item a >> nth=0', 'href');
  await p.goto(base + href, { waitUntil: 'networkidle' });
  await shot(p, 'd_pdp');
  if (await p.locator('[data-open-dialog]').count()) {
    await p.click('[data-open-dialog]');
    await p.waitForTimeout(400);
    log('size guide open', await p.evaluate(() => document.getElementById('size-guide-dialog').open));
    await shot(p, 'd_pdp_size_guide');
    await p.keyboard.press('Escape');
  }
  log('pdp texts:', ['Inclusive of all taxes', 'Ships in', 'Country of origin', 'Order on WhatsApp']
      .map(t => t + '=' + (p.url() && 0 || '')).length ? await p.evaluate(() => ['Inclusive of all taxes', 'Ships in', 'Country of origin', 'Order on WhatsApp'].map(t => `${t}:${document.body.innerText.includes(t)}`).join(' ')) : '');

  // Add to cart -> cart shipping + checkout payment options
  await Promise.all([p.waitForNavigation(), p.evaluate(() => document.getElementById('pdp-cart-form').submit())]);
  await p.goto(base + '/cart/', { waitUntil: 'networkidle' });
  log('cart: shipping row', await p.evaluate(() => document.body.innerText.includes('Shipping')),
      '| free-ship hint', await p.locator('.fd-ship-progress').count());
  await p.goto(base + '/checkout/', { waitUntil: 'networkidle' });
  log('checkout payment options', await p.locator('.fd-pay-option').allTextContents().then(t => t.map(x => x.trim().split('\n')[0])));
  await shot(p, 'd_checkout');

  // Wishlist page
  await p.goto(base + '/wishlist/', { waitUntil: 'networkidle' });
  log('wishlist page cards', await p.locator('.product-item').count());
  await shot(p, 'd_wishlist');

  // Content + service pages
  for (const [path, name] of [['/faq/', 'faq'], ['/pages/shipping-policy/', 'page'], ['/book-appointment/', 'appointment'], ['/track-order/', 'track']]) {
    const r = await p.goto(base + path, { waitUntil: 'networkidle' });
    log(path, r.status());
    await shot(p, 'd_' + name);
  }

  // OTP login using the console SMS backend code from the server log
  const o = await b.newContext({ viewport: { width: 390, height: 844 }, isMobile: true });
  const m = await o.newPage();
  m.on('pageerror', e => errs.push(e.message));
  await m.goto(base + '/accounts/login/phone/', { waitUntil: 'networkidle' });
  await shot(m, 'm_otp_login');
  await m.fill('input[name=phone]', '98765 0' + String(Date.now()).slice(-4));
  await Promise.all([m.waitForNavigation(), m.click('form.fd-form button[type=submit]')]);
  await shot(m, 'm_otp_verify');
  await m.waitForTimeout(500);
  const lines = fs.readFileSync(serverLog, 'utf8').split('\n').filter(l => l.includes('[SMS to'));
  const code = lines[lines.length - 1].split('] ')[1].split(' ')[0];
  await m.fill('input[name=code]', code);
  await Promise.all([m.waitForNavigation(), m.click('form.fd-form button[type=submit]')]);
  log('otp: landed on', m.url().replace(base, ''), '| signed in', await m.evaluate(() => document.body.innerText.includes('My Account') || document.body.innerText.includes('Hello')));

  // Mobile shop + PDP
  await m.goto(base + '/shop/', { waitUntil: 'networkidle' });
  await shot(m, 'm_shop');
  await m.goto(base + href, { waitUntil: 'networkidle' });
  await shot(m, 'm_pdp');

  log('page errors', errs);
  await b.close();
})();
