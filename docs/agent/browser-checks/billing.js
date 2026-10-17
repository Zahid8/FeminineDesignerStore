const { chromium } = require('playwright');
const base = 'http://127.0.0.1:3010';
(async () => {
  const b = await chromium.launch();
  const ctx = await b.newContext({ viewport: { width: 1440, height: 900 } });
  const p = await ctx.newPage(); p.setDefaultTimeout(180000); p.setDefaultNavigationTimeout(180000); const errs = []; p.on('pageerror', e => errs.push(e.message));
  await p.goto(base + '/login', { waitUntil: 'load' });
  await p.fill('input[type=password]', 'feminine@222');
  await Promise.all([p.waitForNavigation({ waitUntil: 'load' }), p.click('button[type=submit]')]);
  await p.goto(base + '/online-orders?view=all', { waitUntil: 'load' }); await p.waitForTimeout(800);
  await p.screenshot({ path: '/tmp/fdshot/bill_d_list.jpg', type: 'jpeg', quality: 72, fullPage: true });
  const rows = await p.locator('table tbody tr').count();
  const first = await p.locator('table tbody tr td a').first().getAttribute('href');
  await p.goto(base + first, { waitUntil: 'load' }); await p.waitForTimeout(600);
  await p.screenshot({ path: '/tmp/fdshot/bill_d_detail.jpg', type: 'jpeg', quality: 72, fullPage: true });
  // update status -> confirmed, payment -> paid
  await p.selectOption('select >> nth=0', 'confirmed');
  await p.selectOption('select >> nth=1', 'paid');
  await p.click('button:has-text("Update")'); await p.waitForTimeout(2500);
  const toast = await p.evaluate(() => document.body.innerText.includes('updated on the webstore'));
  const badge = await p.evaluate(() => document.body.innerText.includes('Confirmed') && document.body.innerText.includes('Paid'));
  // mobile
  const m = await b.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, storageState: await ctx.storageState() });
  const mp = await m.newPage(); mp.setDefaultTimeout(180000); mp.setDefaultNavigationTimeout(180000);
  await mp.goto(base + '/online-orders?view=all', { waitUntil: 'load' }); await mp.waitForTimeout(600);
  await mp.screenshot({ path: '/tmp/fdshot/bill_m_list.jpg', type: 'jpeg', quality: 72, fullPage: true });
  await mp.goto(base + '/orders', { waitUntil: 'load' });
  const link = await mp.locator('a:has-text("Online Orders")').count();
  console.log('rows', rows, '| first', first, '| toast', toast, '| badges', badge, '| mobile orders-page link', link, '| errors', errs);
  await b.close();
})();
