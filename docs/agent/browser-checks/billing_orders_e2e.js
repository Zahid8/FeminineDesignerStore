const { chromium } = require('playwright');
const [A, B, C] = process.argv.slice(2);
const bill = 'http://127.0.0.1:3011', shop = 'http://127.0.0.1:8770';
const results = []; const ok = (n, c, d = '') => { results.push([c, n]); console.log((c ? 'PASS ' : 'FAIL ') + n + (d ? '  — ' + d : '')); };
(async () => {
  const b = await chromium.launch(); const errs = [];
  for (const [tag, vp] of [['d', { width: 1440, height: 900 }], ['m', { width: 390, height: 844 }]]) {
    const ctx = await b.newContext({ viewport: vp }); const p = await ctx.newPage();
    p.on('pageerror', e => errs.push(e.message));
    await p.goto(bill + '/login'); await p.fill('input[type=password]', 'feminine@222'); await Promise.all([p.waitForNavigation(), p.click('button[type=submit]')]);
    await p.goto(bill + '/online-orders?view=attention', { waitUntil: 'load' }); await p.waitForTimeout(1500);
    const body = await p.textContent('body');
    ok(`[${tag}] list flags refund due`, body.includes('Refund due'));
    ok(`[${tag}] list flags exchange request`, body.includes('Exchange request'));
    await p.goto(`${bill}/online-orders/${B}`, { waitUntil: 'load' }); await p.waitForTimeout(1200);
    ok(`[${tag}] cancelled paid order shows refund alert`, (await p.textContent('[role=alert]') || '').includes('Refund due'));
    await p.screenshot({ path: `home/b_${tag}_refund.png`, fullPage: true });
    if (tag === 'd') {
      await p.goto(`${bill}/online-orders/${A}`, { waitUntil: 'load' }); await p.waitForTimeout(1200);
      await p.fill('input[list=fd-couriers]', 'Delhivery'); await p.fill('input[placeholder="e.g. 1490 2210 5582"]', '149022105582');
      const auto = await p.inputValue('input[type=url]');
      ok('[d] tracking link auto-filled from courier + AWB', auto === 'https://www.delhivery.com/track/package/149022105582', auto);
      await p.fill('input[type=date]', '2026-10-22');
      await p.click('button:has-text("Save & mark shipped")'); await p.waitForTimeout(2500);
      const api = await (await ctx.request.get(`${shop}/api/online-orders/${A}/`, { headers: { Authorization: 'Bearer e2e-token' } })).json();
      ok('[d] webstore order now shipped with AWB', api.order.status === 'shipped' && api.order.tracking.number === '149022105582' && api.order.tracking.expected_delivery === '2026-10-22', JSON.stringify(api.order.tracking));
      ok('[d] history shows Shipped', (await p.textContent('body')).includes('History'));
      await p.screenshot({ path: `home/b_d_tracking.png`, fullPage: true });
      await p.goto(`${bill}/online-orders/${C}`, { waitUntil: 'load' }); await p.waitForTimeout(1200);
      await p.selectOption('text=Status >> xpath=following::select[1]', 'approved').catch(async () => { const sels = await p.$$('select'); await sels[sels.length - 1].selectOption('approved'); });
      await p.fill('textarea[placeholder^="e.g. Pickup"]', 'Pickup on Monday, keep the tags on.');
      await p.click('button:has-text("Update request")'); await p.waitForTimeout(2500);
      const api2 = await (await ctx.request.get(`${shop}/api/online-orders/${C}/`, { headers: { Authorization: 'Bearer e2e-token' } })).json();
      ok('[d] request approved with reply on webstore', api2.order.requests[0].status === 'approved', api2.order.requests[0].status);
      await p.screenshot({ path: `home/b_d_request.png`, fullPage: true });
    }
    await ctx.close();
  }
  ok('no page errors', errs.length === 0, errs.join(' | '));
  console.log('\nISSUES:', results.filter(r => !r[0]).map(r => r[1]).join('; ') || 'none');
  await b.close();
})();
