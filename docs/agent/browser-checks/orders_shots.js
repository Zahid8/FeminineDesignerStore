const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch(); const base = 'http://127.0.0.1:8766'; const errs = [];
  const [A, B] = process.argv.slice(2);
  const ctx = await b.newContext({ viewport: {width:390,height:844}, isMobile: true, hasTouch: true, deviceScaleFactor: 2 });
  const p = await ctx.newPage(); p.on('pageerror', e => errs.push(e.message));
  await p.goto(base + '/accounts/login/?method=email'); await p.fill('input[name=username]', 'qa@example.com'); await p.fill('input[name=password]', 'Qa-pass-12345!');
  await Promise.all([p.waitForNavigation(), p.click('form.fd-form button[type=submit]')]);
  for (const [n, u] of [['list', '/accounts/orders/'], ['shipped', `/accounts/orders/${A}/`], ['delivered', `/accounts/orders/${B}/`], ['request', `/orders/${B}/request/`]]) {
    await p.goto(base + u, { waitUntil: 'networkidle' }); await p.waitForTimeout(400);
    await p.screenshot({ path: `home/o_${n}.png`, fullPage: true });
    const w = await p.evaluate(() => document.documentElement.scrollWidth); console.log(n, 'width', w);
  }
  console.log('errors', errs); await b.close();
})();
