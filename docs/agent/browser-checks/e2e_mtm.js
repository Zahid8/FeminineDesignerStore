const { chromium } = require('playwright');
const base = 'http://127.0.0.1:8770';
const SOLD = '/products/aggregate-stock/', INSTOCK = '/products/silk-embroidered-blouse/';
const IN = { length: '15', chest: '36', waist: '30', armhole: '16', opening: '11', bicep: '13' };
const results = []; const issues = [];
const ok = (name, cond, detail = '') => { results.push(`${cond ? 'PASS' : 'FAIL'}  ${name}${detail ? '  — ' + detail : ''}`); if (!cond) issues.push(name); };

function watch(p, tag) {
  p.on('pageerror', e => issues.push(`[${tag}] JS error: ${e.message}`));
  p.on('console', m => { if (m.type() === 'error' && !/404/.test(m.text())) issues.push(`[${tag}] console: ${m.text()}`); });
  p.on('response', r => { const u = r.url(); if (r.status() >= 400 && u.startsWith(base) && !u.includes('/media/') && !u.endsWith('favicon.ico')) issues.push(`[${tag}] HTTP ${r.status()} ${u}`); });
}
async function toasts(p) { return (await p.$$eval('[data-toast]', els => els.map(e => (e.classList.contains('is-error') ? 'ERR:' : '') + e.textContent.replace(/\s+/g, ' ').trim()))); }
async function fillBuilder(p, vals, sleeveIdx = 5) {
  for (const [k, v] of Object.entries(vals)) await p.fill('#id_' + k, v);
  await p.click('#customize-section button:has-text("Continue to style")');
  await p.click(`label[for="sleeve-${sleeveIdx}"]`);
  await p.click('#customize-section button:has-text("Review")');
}
async function submitBuilder(p) {
  await Promise.all([p.waitForNavigation(), p.click('#custom-fit-form button[type=submit]:has-text("Add Made-to-Measure")')]);
}
async function checkout(p, tag) {
  await p.goto(base + '/checkout/');
  if (await p.inputValue('#id_customer_name') === '') await p.fill('#id_customer_name', 'Asha E2E');
  if (await p.inputValue('#id_customer_email') === '') await p.fill('#id_customer_email', 'asha.e2e@example.com');
  await p.fill('#id_customer_phone', '9876543210');
  await p.fill('#id_shipping_address', '12 MG Road, Pune 411001');
  const terms = await p.isVisible('.fd-terms');
  await Promise.all([p.waitForNavigation(), p.click('#checkout-form button[type=submit]')]);
  const url = p.url(); const m = url.match(/orders\/([^/]+)\/success/);
  ok(`[${tag}] checkout lands on success page`, !!m, url.replace(base, ''));
  ok(`[${tag}] made-to-measure terms shown at checkout`, terms);
  return m && m[1];
}
async function api(ctx, num) {
  const r = await ctx.request.get(`${base}/api/online-orders/${num}/`, { headers: { Authorization: 'Bearer e2e-token' } });
  return r.ok() ? (await r.json()).order : { status: r.status() };
}

(async () => {
  const b = await chromium.launch();

  // ---------- S1: guest, desktop, SOLD-OUT product, inches ----------
  {
    const ctx = await b.newContext({ viewport: { width: 1440, height: 900 } }); const p = await ctx.newPage(); watch(p, 'S1');
    await p.goto(base + SOLD, { waitUntil: 'networkidle' });
    ok('[S1] sold-out PDP shows "Customize this design"', await p.isVisible('button:has-text("Customize this design")'));
    await p.click('button:has-text("Customize this design")'); await p.waitForTimeout(500);
    ok('[S1] builder opens', await p.isVisible('#customize-section'));
    await fillBuilder(p, IN);
    const chips = await p.$$eval('#customize-section .fd-custom-chips li', ls => ls.filter(l => l.offsetParent).map(l => l.textContent.replace(/\s+/g, ' ').trim()));
    ok('[S1] review lists measurements + sleeves', chips.some(c => c.includes('Chest') && c.includes('36')) && chips.some(c => c.includes('Sleeves')), chips.join(' | '));
    await submitBuilder(p);
    const t = await toasts(p);
    ok('[S1] success toast after add', t.some(x => /made-to-measure/i.test(x) && !x.startsWith('ERR')), t.join(' | '));
    await p.goto(base + '/cart/');
    const line = (await p.textContent('.fd-cart-list')).replace(/\s+/g, ' ');
    ok('[S1] cart line is made to measure with measurements', /Made to measure/i.test(line) && /Chest/.test(line), line.slice(0, 160));
    await p.locator('.fd-cart-qty [data-action="inc"]').first().click();
    await Promise.all([p.waitForNavigation(), p.locator('.fd-cart-qty [data-qty-update]').first().click()]);
    ok('[S1] quantity updated to 2 despite 0 stock', (await p.inputValue('.fd-cart-qty input[name=quantity]')) === '2', (await toasts(p)).join(' | '));
    const num = await checkout(p, 'S1');
    const o = await api(ctx, num);
    const it = (o.items || [])[0] || {};
    ok('[S1] API order has 1 custom item, qty 2', (o.items || []).length === 1 && it.quantity === 2 && !!it.customization, JSON.stringify(it).slice(0, 220));
    ok('[S1] unit price includes ₹400 tailoring fee', it.unit_price && Number(it.unit_price) > 400, `unit ${it.unit_price}, total ${o.total}`);
    await ctx.close();
  }

  // ---------- S2: logged-in, mobile, IN-STOCK product: ready-made + custom (cm) ----------
  {
    const ctx = await b.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true }); const p = await ctx.newPage(); watch(p, 'S2');
    await p.goto(base + '/accounts/login/');
    await p.fill('input[name=username]', 'e2e@example.com'); await p.fill('input[name=password]', 'E2e-pass-123!');
    await Promise.all([p.waitForNavigation(), p.click('form.fd-form button[type=submit]')]);
    ok('[S2] customer logged in', !p.url().includes('/accounts/login/'), p.url().replace(base, ''));
    await p.goto(base + INSTOCK, { waitUntil: 'networkidle' });
    await p.click('label[for="size-2"]');
    await p.fill('#quantity', '2');
    await Promise.all([p.waitForNavigation(), p.click('#pdp-cart-form button[type=submit]:has-text("Add to Cart")')]);
    ok('[S2] ready-made qty 2 added', (await toasts(p)).some(x => /added to your bag/.test(x) && !x.startsWith('ERR')), (await toasts(p)).join(' | '));
    await p.goto(base + INSTOCK + '?fit=custom', { waitUntil: 'networkidle' });
    await p.locator('#customize-section').scrollIntoViewIfNeeded();
    await p.click('#customize-section .fd-unit-toggle button:has-text("cm")');
    const cm = Object.fromEntries(Object.entries(IN).map(([k, v]) => [k, (Number(v) * 2.54).toFixed(2)]));
    await fillBuilder(p, cm, 3);
    await submitBuilder(p);
    ok('[S2] custom (cm) added', (await toasts(p)).some(x => /made-to-measure/i.test(x) && !x.startsWith('ERR')), (await toasts(p)).join(' | '));
    await p.goto(base + '/cart/');
    ok('[S2] cart has 2 separate lines', (await p.$$('.fd-cart-line')).length === 2);
    const num = await checkout(p, 'S2');
    const o = await api(ctx, num);
    const custom = (o.items || []).find(i => i.customization); const ready = (o.items || []).find(i => !i.customization);
    ok('[S2] order has ready-made x2 + custom x1', ready && ready.quantity === 2 && custom && custom.quantity === 1);
    ok('[S2] cm converted to inches (chest 36)', custom && JSON.stringify(custom.customization).includes('36'), custom && JSON.stringify(custom.customization).slice(0, 200));
    await p.goto(base + INSTOCK + '?fit=custom', { waitUntil: 'networkidle' });
    ok('[S2] saved measurements prefill next time', (await p.content()).includes('Prefilled with your saved measurements'));
    await p.goto(base + `/accounts/orders/${num}/`);
    ok('[S2] order visible in My Orders with measurements', /Chest/.test(await p.textContent('main')));
    await ctx.close();
  }

  // ---------- S3: fitting-call request -> add to bag (sold-out) ----------
  {
    const ctx = await b.newContext({ viewport: { width: 1440, height: 900 } }); const p = await ctx.newPage(); watch(p, 'S3');
    await p.goto(base + SOLD + '?fit=custom', { waitUntil: 'networkidle' });
    await fillBuilder(p, IN);
    await p.click('summary:has-text("Request a fitting call")');
    await p.fill('#cf-name', 'Meera'); await p.fill('#cf-phone', '9876500000');
    await Promise.all([p.waitForNavigation(), p.click('button:has-text("Request a Fitting Call")')]);
    ok('[S3] fitting-call confirmation shown', /What happens next/.test(await p.content()));
    await Promise.all([p.waitForNavigation(), p.click('a:has-text("Add to Bag with These Measurements")')]);
    ok('[S3] builder prefilled from request', (await p.content()).includes('Prefilled from your fitting request'));
    await p.click('#customize-section button:has-text("Continue to style")'); await p.click('#customize-section button:has-text("Review")');
    await submitBuilder(p);
    ok('[S3] prefilled request adds to bag', (await toasts(p)).some(x => /made-to-measure/i.test(x) && !x.startsWith('ERR')), (await toasts(p)).join(' | '));
    await ctx.close();
  }

  // ---------- S4: invalid measurement — is the error visible? ----------
  {
    const ctx = await b.newContext({ viewport: { width: 1440, height: 900 } }); const p = await ctx.newPage(); watch(p, 'S4');
    await p.goto(base + SOLD + '?fit=custom', { waitUntil: 'networkidle' });
    await fillBuilder(p, { ...IN, chest: '90' });
    await submitBuilder(p);
    await p.waitForTimeout(1000);
    const err = p.locator('.fd-field-error').first();
    const hasErr = await err.count() > 0;
    const inView = hasErr && await err.evaluate(e => { const r = e.getBoundingClientRect(); return r.top >= 0 && r.bottom <= innerHeight && !!e.offsetParent; });
    ok('[S4] invalid value rejected with message', hasErr, hasErr ? await err.textContent() : 'no error element');
    ok('[S4] error message visible without scrolling', inView, `scrollY=${await p.evaluate(() => scrollY)}`);
    ok('[S4] entered values kept', (await p.inputValue('#id_waist')) === '30');
    await p.screenshot({ path: '/tmp/fdshot/e2e_s4.png' });
    await ctx.close();
  }

  // ---------- S5: admin + API list ----------
  {
    const ctx = await b.newContext({ viewport: { width: 1440, height: 900 } }); const p = await ctx.newPage(); watch(p, 'S5');
    await p.goto(base + '/admin/login/');
    await p.fill('#id_username', 'neuadmin'); await p.fill('#id_password', 'neu-pass-123');
    await Promise.all([p.waitForNavigation(), p.click('input[type=submit]')]);
    await p.goto(base + '/admin/store/order/');
    await Promise.all([p.waitForNavigation(), p.click('#result_list tbody tr:first-child th a')]);
    ok('[S5] admin order shows customization', /chest/i.test(await p.content()));
    const r = await ctx.request.get(base + '/api/online-orders/', { headers: { Authorization: 'Bearer e2e-token' } });
    ok('[S5] Online Orders API list OK', r.ok(), `HTTP ${r.status()}`);
    await ctx.close();
  }

  await b.close();
  console.log(results.join('\n'));
  console.log('\nISSUES:', issues.length ? '\n' + [...new Set(issues)].join('\n') : 'none');
})();
