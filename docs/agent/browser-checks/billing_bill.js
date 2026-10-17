const { chromium } = require('playwright');
const { execFileSync } = require('child_process'); const fs = require('fs');
const base = 'http://127.0.0.1:3011';
const SHIPPED = 'FD-20261017-FE49D4', DELIVERED = 'FD-20261017-129EF0';
const R = [], I = []; const ok = (n, c, d = '') => { R.push(`${c ? 'PASS' : 'FAIL'}  ${n}${d ? '  — ' + d : ''}`); if (!c) I.push(n); };
(async () => {
  const b = await chromium.launch();
  const ctx = await b.newContext({ viewport: { width: 1440, height: 900 } }); const p = await ctx.newPage(); p.setDefaultTimeout(60000);
  p.on('pageerror', e => I.push('JS error: ' + e.message));
  await p.goto(base + '/login'); await p.fill('input[type=password]', 'feminine@222'); await Promise.all([p.waitForNavigation(), p.click('button[type=submit]')]);

  await p.goto(base + `/online-orders/${SHIPPED}`, { waitUntil: 'load' });
  const billUrl = await p.locator('a:has-text("View bill")').first().getAttribute('href');
  ok('order page has a signed bill link', /\/bill\/online\/FD-20261017-FE49D4\/[A-Za-z0-9_-]{22}$/.test(billUrl || ''), billUrl);
  const chips = await p.$$eval('a[href^="https://wa.me/"]', as => as.map(a => ({ label: a.textContent.trim(), href: a.href })));
  ok('shipped order offers Order confirmation + Shipped + Payment reminder', chips.map(c => c.label).join('|') === 'Order confirmation|Shipped|Payment reminder', chips.map(c => c.label).join('|'));
  const shippedMsg = decodeURIComponent((chips.find(c => c.label === 'Shipped') || {}).href || '');
  ok('WhatsApp goes to +91 number with bill link in the text', shippedMsg.startsWith('https://wa.me/919876500000?text=') && shippedMsg.includes(billUrl), shippedMsg.slice(0, 160));
  await p.screenshot({ path: '/tmp/fdshot/bill_detail.png', fullPage: true });

  // Customer opens the link: no staff cookie
  const anon = await b.newContext();
  const res = await anon.request.get(billUrl);
  ok('customer can open the bill without logging in', res.status() === 200 && res.headers()['content-type'] === 'application/pdf', `${res.status()} ${res.headers()['content-type']}`);
  ok('bill opens inline and is not cached/indexed', (res.headers()['content-disposition'] || '').startsWith('inline') && res.headers()['cache-control'].includes('no-store') && res.headers()['x-robots-tag'] === 'noindex');
  fs.writeFileSync('/tmp/fdshot/online_bill.pdf', await res.body());
  const text = execFileSync('pdftotext', ['-layout', '/tmp/fdshot/online_bill.pdf', '-'], { encoding: 'utf8' });
  ok('PDF has order, customer, custom item + measurements, total', ['FD-20261017-FE49D4', 'Custom Kavya', 'Custom size', 'Chest 36 in', '₹2,500.00', 'Shipped'].every(t => text.includes(t)));
  const dl = await anon.request.get(billUrl + '?download=1');
  ok('download link saves as Bill_<order>.pdf', (dl.headers()['content-disposition'] || '') === 'attachment; filename="Bill_FD-20261017-FE49D4.pdf"', dl.headers()['content-disposition']);
  const bad = await anon.request.get(billUrl.slice(0, -1) + (billUrl.endsWith('A') ? 'B' : 'A'));
  ok('tampered link is rejected (404)', bad.status() === 404, String(bad.status()));
  const other = await anon.request.get(billUrl.replace('FD-20261017-FE49D4', DELIVERED));
  ok("one order's signature can't open another order", other.status() === 404, String(other.status()));
  const staffPage = await anon.request.get(base + `/online-orders/${SHIPPED}`, { maxRedirects: 0 });
  ok('staff pages still need login', [302, 303, 307, 308].includes(staffPage.status()), String(staffPage.status()));

  await p.goto(base + `/online-orders/${DELIVERED}`, { waitUntil: 'load' });
  const chips2 = await p.$$eval('a[href^="https://wa.me/"]', as => as.map(a => a.textContent.trim()));
  ok('delivered + paid order offers confirmation, shipped, delivered (no reminder)', chips2.join('|') === 'Order confirmation|Shipped|Delivered', chips2.join('|'));

  await p.goto(base + '/settings', { waitUntil: 'load' });
  const settingsText = await p.textContent('main');
  ok('settings lists the three online-order WhatsApp messages', ['Online order confirmation', 'Online order shipped', 'Online order delivered'].every(t => settingsText.includes(t)));

  const m = await (await b.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, storageState: await ctx.storageState() })).newPage();
  await m.goto(base + `/online-orders/${SHIPPED}`, { waitUntil: 'load' }); await m.screenshot({ path: '/tmp/fdshot/bill_detail_mobile.png', fullPage: true });
  await b.close();
  console.log(R.join('\n')); console.log('\nISSUES:', I.length ? '\n' + I.join('\n') : 'none');
})();
