const { chromium } = require('playwright');
const base = 'http://127.0.0.1:3011', shop = 'http://127.0.0.1:8766';
const CUSTOM = 'FD-20261017-FE49D4', MIXED = 'FD-20261017-129EF0', READY = 'FD-20261017-627765';
const results = [], issues = [];
const ok = (n, c, d = '') => { results.push(`${c ? 'PASS' : 'FAIL'}  ${n}${d ? '  — ' + d : ''}`); if (!c) issues.push(n); };
async function waitStatus(ctx, num, want, ms = 20000) {
  const end = Date.now() + ms; let got;
  while (Date.now() < end) { got = await shopStatus(ctx, num); if (got === want) return got; await new Promise(r => setTimeout(r, 400)); }
  return got;
}
async function shopStatus(ctx, num) {
  const r = await ctx.request.get(`${shop}/api/online-orders/${num}/`, { headers: { Authorization: 'Bearer demo-token-123' } });
  return (await r.json()).order.status;
}
(async () => {
  const b = await chromium.launch();
  const ctx = await b.newContext({ viewport: { width: 1440, height: 900 } }); const p = await ctx.newPage();
  p.setDefaultTimeout(60000);
  p.on('pageerror', e => issues.push('JS error: ' + e.message));
  p.on('response', r => { if (r.status() >= 500) issues.push(`HTTP ${r.status()} ${r.url()}`); });
  await p.goto(base + '/login'); await p.fill('input[type=password]', 'feminine@222');
  await Promise.all([p.waitForNavigation(), p.click('button[type=submit]')]);

  await p.goto(base + '/online-orders?view=all', { waitUntil: 'networkidle' });
  const tabs = await p.$$eval('nav[aria-label="Online order lists"] a', as => as.map(a => a.textContent.replace(/\d+/g, '').trim()));
  ok('tabs include Shipped, Delivered, Fulfilled', ['Shipped', 'Delivered', 'Fulfilled'].every(t => tabs.includes(t)), tabs.join(' | '));
  const rowText = async num => (await p.locator('table tbody tr', { hasText: num }).first().textContent()).replace(/\s+/g, ' ');
  ok('custom order shows "Custom size"', (await rowText(CUSTOM)).includes('Custom size'));
  ok('mixed order shows "Ready-made + custom size"', (await rowText(MIXED)).includes('Ready-made + custom size'));
  ok('ready order shows "Ready-made"', /Ready-made(?! \+)/.test(await rowText(READY)));
  await p.screenshot({ path: '/tmp/fdshot/bill_stage_list.png' });

  await p.goto(base + '/online-orders?view=all&type=made_to_measure', { waitUntil: 'networkidle' });
  const filtered = await p.$$eval('table tbody tr', trs => trs.map(t => t.textContent));
  ok('type filter "Has custom size" keeps custom + mixed only', filtered.some(t => t.includes(CUSTOM)) && filtered.some(t => t.includes(MIXED)) && !filtered.some(t => t.includes(READY)), `${filtered.length} rows`);
  await p.goto(base + '/online-orders?view=all&type=ready_made', { waitUntil: 'networkidle' });
  const ready = await p.$$eval('table tbody tr', trs => trs.map(t => t.textContent));
  ok('type filter "Ready-made only" excludes custom', ready.some(t => t.includes(READY)) && !ready.some(t => t.includes(CUSTOM)) && !ready.some(t => t.includes(MIXED)));

  // Quick action from the table: READY is processing -> Mark shipped
  await p.goto(base + '/online-orders?view=all', { waitUntil: 'networkidle' });
  await p.locator('table tbody tr', { hasText: READY }).getByRole('button', { name: /Mark shipped/ }).click();
  ok('table "Mark shipped" saves to webstore', (await waitStatus(ctx, READY, 'shipped')) === 'shipped');
  await p.waitForTimeout(1500);
  ok('row shows Shipped badge after refresh', (await rowText(READY)).includes('Shipped'));
  ok('row now offers "Mark delivered"', (await rowText(READY)).includes('Mark delivered'));

  // Detail page: CUSTOM confirmed -> processing -> shipped -> delivered -> fulfilled
  await p.goto(base + `/online-orders/${CUSTOM}`, { waitUntil: 'networkidle' });
  const detail = (await p.textContent('main')).replace(/\s+/g, ' ');
  ok('detail shows order type and per-item fit + measurements', detail.includes('Custom size') && detail.includes('Measurements') && detail.includes('Chest'));
  await p.screenshot({ path: '/tmp/fdshot/bill_stage_detail.png', fullPage: true });
  for (const [label, expected] of [['Mark as processing', 'processing'], ['Mark as shipped', 'shipped'], ['Mark as delivered', 'delivered'], ['Mark as fulfilled', 'completed']]) {
    await p.getByRole('button', { name: label }).click();
    const got = await waitStatus(ctx, CUSTOM, expected);
    ok(`detail "${label}" → webstore ${expected}`, got === expected, got);
    await p.waitForFunction(l => !document.body.innerText.includes(l) && !document.body.innerText.includes('Saving…'), label, { timeout: 30000 }).catch(() => {});
  }
  ok('fulfilled order shows done message', (await p.textContent('main')).includes('Fulfilled — nothing left to do'));
  await p.screenshot({ path: '/tmp/fdshot/bill_stage_done.png' });

  // Jump back via stage tracker (Delivered), then Delivered tab
  await p.getByRole('button', { name: 'Delivered', exact: true }).click();
  ok('stage tracker can set Delivered directly', (await waitStatus(ctx, CUSTOM, 'delivered')) === 'delivered');
  await p.goto(base + '/online-orders?view=delivered', { waitUntil: 'networkidle' });
  ok('Delivered tab lists the order', (await p.content()).includes(CUSTOM));

  // Mobile
  const m = await (await b.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, storageState: await ctx.storageState() })).newPage();
  m.on('pageerror', e => issues.push('mobile JS error: ' + e.message));
  await m.goto(base + '/online-orders?view=all', { waitUntil: 'networkidle' }); await m.screenshot({ path: '/tmp/fdshot/bill_stage_mobile.png' });
  await m.goto(base + `/online-orders/${MIXED}`, { waitUntil: 'networkidle' }); await m.screenshot({ path: '/tmp/fdshot/bill_stage_mobile_detail.png', fullPage: true });
  ok('mobile detail shows stage tracker', await m.isVisible('ol[aria-label="Order stages"]'));

  await b.close();
  console.log(results.join('\n')); console.log('\nISSUES:', issues.length ? '\n' + issues.join('\n') : 'none');
})();
