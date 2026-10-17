const { chromium } = require('playwright');
const { execFileSync } = require('child_process'); const fs = require('fs');
const EMAIL = 'meera.' + Date.now() + '@example.com';
const shop = process.env.SHOP || 'http://127.0.0.1:8766', bill = 'http://127.0.0.1:3011';
const R = [], I = []; const ok = (n, c, d = '') => { R.push(`${c ? 'PASS' : 'FAIL'}  ${n}${d ? '  — ' + d : ''}`); if (!c) I.push(n); };
async function addToBag(p) {
  await p.goto(shop + '/products/silk-embroidered-blouse/', { waitUntil: 'load' });
  await p.click('label[for="size-2"]').catch(() => {});
  await Promise.all([p.waitForNavigation(), p.click('#pdp-cart-form button[type=submit]:has-text("Add to Cart")')]);
}
async function fillCheckout(p, extra = {}) {
  await p.goto(shop + '/checkout/', { waitUntil: 'load' });
  await p.fill('#id_customer_name', 'Meera Location'); await p.fill('#id_customer_email', EMAIL);
  await p.fill('#id_customer_phone', '9812345678'); await p.fill('#id_address_line1', 'Flat 4B, Lotus Residency'); await p.fill('#id_address_line2', 'Baner Road'); await p.fill('#id_city', 'Pune'); await p.selectOption('#id_state', 'Maharashtra'); await p.fill('#id_pincode', '411045');
  await p.fill('#id_notes', 'Call before coming, gate code 2244');
  for (const [k, v] of Object.entries(extra)) await p.fill(k, v);
}
(async () => {
  const b = await chromium.launch();
  // 1) Shop: invalid link rejected, then geolocation button, then pasted share text
  const ctx = await b.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, geolocation: { latitude: 18.559123, longitude: 73.786456 }, permissions: ['geolocation'] });
  const p = await ctx.newPage(); p.on('pageerror', e => I.push('shop JS error: ' + e.message));
  await addToBag(p);
  await fillCheckout(p, { '#id_location_url': 'near the big temple' });
  await Promise.all([p.waitForLoadState('load'), p.click('#checkout-form button[type=submit]')]);
  ok('shop: non-link is rejected with a clear message', ((await p.textContent('.fd-location-field .invalid-feedback').catch(() => '')) || '').includes('Paste a Google Maps link'), p.url());
  ok('shop: field is optional (label says so)', (await p.textContent('label[for="id_location_url"]')).includes('optional'));
  await p.click('.fd-location-btn'); await p.waitForTimeout(800);
  ok('shop: "Use my current location" fills a Maps link', (await p.inputValue('#id_location_url')) === 'https://www.google.com/maps?q=18.559123,73.786456', await p.inputValue('#id_location_url'));
  await p.fill('#id_location_url', 'My home 🏠 https://maps.app.goo.gl/MeeraHome123 see you!');
  await p.screenshot({ path: '/tmp/fdshot/loc_checkout.png', fullPage: false });
  await p.locator('#id_location_url').screenshot({ path: '/tmp/fdshot/loc_field.png' }).catch(() => {});
  await Promise.all([p.waitForNavigation(), p.click('#checkout-form button[type=submit]')]);
  const num = (p.url().match(/orders\/([^/]+)\/success/) || [])[1];
  ok('shop: order placed with location', !!num, p.url());
  const successHtml = await p.content();
  ok('shop: confirmation shows "Open in Google Maps" with the cleaned link', successHtml.includes('href="https://maps.app.goo.gl/MeeraHome123"') && successHtml.includes('Open in Google Maps'));
  await p.screenshot({ path: '/tmp/fdshot/loc_success.png', fullPage: true });

  // 2) Billing app shows everything
  const bc = await b.newContext({ viewport: { width: 1440, height: 900 } }); const bp = await bc.newPage(); bp.setDefaultTimeout(60000);
  bp.on('pageerror', e => I.push('billing JS error: ' + e.message));
  await bp.goto(bill + '/login'); await bp.fill('input[type=password]', 'feminine@222'); await Promise.all([bp.waitForNavigation(), bp.click('button[type=submit]')]);
  await bp.goto(bill + '/online-orders?view=all', { waitUntil: 'load' });
  const row = bp.locator('table tbody tr', { hasText: num });
  ok('billing list: Map link on the order row', (await row.locator('a:has-text("Map")').getAttribute('href')) === 'https://maps.app.goo.gl/MeeraHome123');
  await bp.goto(bill + `/online-orders/${num}`, { waitUntil: 'load' });
  const main = (await bp.textContent('main')).replace(/\s+/g, ' ');
  const gm = await bp.locator('a:has-text("Open in Google Maps")').getAttribute('href');
  ok('billing order: Google Maps button opens the pin', gm === 'https://maps.app.goo.gl/MeeraHome123', gm);
  for (const [label, text] of [
    ['delivery address', 'Flat 4B, Lotus Residency'], ['second address line', 'Pune, Maharashtra 411045'], ['customer note', 'Call before coming, gate code 2244'],
    ['customer phone', '9812345678'], ['customer email', EMAIL], ['guest checkout', 'Guest checkout'], ['first order', 'First order'],
    ['payment method', 'Manual UPI'], ['balance', 'Balance'], ['placed time', 'Placed'], ['last updated', 'Last updated'],
    ['item SKU', 'SKU'], ['item size', 'Size'], ['item price breakdown', '×'], ['shipping line', 'Shipping'], ['order type', 'Ready-made'],
  ]) ok(`billing order shows ${label}`, main.includes(text), text);
  ok('billing order: product photo or placeholder shown', (await bp.locator('main img[alt], main svg.lucide-package').count()) > 0);
  ok('billing order: "View on store" product link is absolute', ((await bp.locator('a:has-text("View on store")').first().getAttribute('href')) || '').startsWith(shop + '/products/'));
  await bc.grantPermissions(['clipboard-read', 'clipboard-write'], { origin: bill });
  await bp.click('button:has-text("Copy delivery details")');
  const clip = await bp.evaluate(() => navigator.clipboard.readText());
  ok('billing order: "Copy delivery details" copies name, address, phone, map', ['Meera Location', 'Flat 4B', '9812345678', 'maps.app.goo.gl/MeeraHome123'].every(t => clip.includes(t)), clip.replace(/\n/g, ' | '));
  await bp.screenshot({ path: '/tmp/fdshot/loc_billing.png', fullPage: true });

  // 3) Bill PDF includes the map link
  const billUrl = await bp.locator('a:has-text("View bill")').first().getAttribute('href');
  const res = await (await b.newContext()).request.get(billUrl);
  fs.writeFileSync('/tmp/fdshot/loc_bill.pdf', await res.body());
  const text = execFileSync('pdftotext', ['/tmp/fdshot/loc_bill.pdf', '-'], { encoding: 'utf8' });
  ok('bill PDF has the delivery address and map link', text.includes('Flat 4B, Lotus Residency') && text.includes('maps.app.goo.gl/MeeraHome123'));

  await b.close();
  console.log(R.join('\n')); console.log('\nISSUES:', I.length ? '\n' + I.join('\n') : 'none');
})();
