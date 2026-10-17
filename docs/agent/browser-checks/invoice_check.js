const { chromium } = require('playwright');
const base = 'http://127.0.0.1:8770';
(async () => {
  const b = await chromium.launch();
  for (const [tag, opts] of [['m', { viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true }], ['d', { viewport: { width: 1440, height: 900 } }]]) {
    const ctx = await b.newContext(opts); const p = await ctx.newPage(); const errs = []; p.on('pageerror', e => errs.push(e.message));
    await p.goto(base + '/accounts/login/'); await p.fill('input[name=username]', 'e2e@example.com'); await p.fill('input[name=password]', 'E2e-pass-123!');
    await Promise.all([p.waitForNavigation(), p.click('form.fd-form button[type=submit]')]);
    await p.goto(base + '/accounts/orders/', { waitUntil: 'load' });
    const orderHref = await p.getAttribute('a[href^="/accounts/orders/FD"]', 'href');
    await p.goto(base + orderHref, { waitUntil: 'load' });
    const billHref = await p.getAttribute('a:has-text("View Bill")', 'href');
    await p.goto(base + billHref, { waitUntil: 'load' }); await p.waitForTimeout(900);
    const docW = await p.evaluate(() => document.documentElement.scrollWidth), vw = await p.evaluate(() => innerWidth);
    const pdf = await p.getAttribute('a:has-text("Download PDF")', 'href').catch(() => null);
    await p.screenshot({ path: `/tmp/fdshot/invoice_${tag}.png`, fullPage: true });
    console.log(tag, 'bill:', billHref, '| width ok:', docW <= vw, `(${docW}/${vw})`, '| PDF link:', pdf, '| errors:', errs);
    await ctx.close();
  }
  await b.close();
})();
