const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch(); const base = 'http://127.0.0.1:8766'; const errs = [];
  const ctx = await b.newContext({ viewport: {width:390,height:844}, isMobile: true, hasTouch: true });
  const p = await ctx.newPage(); p.on('pageerror', e => errs.push(e.message));
  await p.goto(base + '/products/silk-embroidered-blouse/'); await Promise.all([p.waitForNavigation(), p.evaluate(() => document.getElementById('pdp-cart-form').submit())]);
  await p.goto(base + '/checkout/', { waitUntil: 'networkidle' });
  await p.fill('input[name=city]', ''); await p.selectOption('select[name=state]', '');
  await p.fill('input[name=pincode]', '400050');
  await p.waitForFunction(() => document.querySelector('[name=city]').value !== '', null, { timeout: 8000 });
  const r = await p.evaluate(() => [document.querySelector('[name=city]').value, document.querySelector('[name=state]').value, document.querySelector('[data-pin-hint]').textContent]);
  console.log(r);
  const el = await p.$('[name=pincode]'); await el.scrollIntoViewIfNeeded(); await p.screenshot({ path: 'home/pin.png' });
  await p.fill('input[name=pincode]', '999999'); await p.waitForTimeout(2500);
  console.log('bad pin hint:', await p.textContent('[data-pin-hint]'));
  console.log('errors', errs); await b.close();
})();
