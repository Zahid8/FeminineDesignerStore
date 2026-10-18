const { chromium } = require('playwright');
const base = 'http://127.0.0.1:8766';
const results = []; const ok = (n, c, d = '') => { results.push([c, n]); console.log((c ? 'PASS ' : 'FAIL ') + n + (d ? '  — ' + d : '')); };
(async () => {
  const b = await chromium.launch(); const errs = [];
  // desktop guest hover
  let ctx = await b.newContext({ viewport: { width: 1440, height: 900 } }); let p = await ctx.newPage(); p.on('pageerror', e => errs.push(e.message));
  await p.goto(base + '/', { waitUntil: 'networkidle' });
  await p.hover('.fd-account-trigger'); await p.waitForTimeout(350);
  ok('desktop guest: hover opens', await p.isVisible('.fd-account-panel .fd-account-cta'));
  await p.screenshot({ path: 'home/am_guest_d.png', clip: { x: 1000, y: 0, width: 440, height: 520 } });
  await ctx.close();
  // desktop signed-in hover → orders
  ctx = await b.newContext({ viewport: { width: 1440, height: 900 } }); p = await ctx.newPage(); p.on('pageerror', e => errs.push(e.message));
  await p.goto(base + '/accounts/login/?method=email'); await p.fill('input[name=username]', 'qa@example.com'); await p.fill('input[name=password]', 'Qa-pass-12345!');
  await Promise.all([p.waitForNavigation(), p.click('form.fd-form button[type=submit]')]);
  await p.hover('.fd-account-trigger'); await p.waitForTimeout(350);
  ok('desktop user: menu shows greeting', (await p.textContent('.fd-account-head')).includes('Hello'));
  await p.screenshot({ path: 'home/am_user_d.png', clip: { x: 1000, y: 0, width: 440, height: 600 } });
  await Promise.all([p.waitForNavigation(), p.click('.fd-account-panel a:has-text("My orders")')]);
  ok('desktop user: My orders link', p.url().includes('/accounts/orders/'));
  await ctx.close();
  // mobile tap
  ctx = await b.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, deviceScaleFactor: 2 }); p = await ctx.newPage(); p.on('pageerror', e => errs.push(e.message));
  await p.goto(base + '/accounts/login/?method=email'); await p.fill('input[name=username]', 'qa@example.com'); await p.fill('input[name=password]', 'Qa-pass-12345!');
  await Promise.all([p.waitForNavigation(), p.click('form.fd-form button[type=submit]')]);
  await p.tap('.fd-account-trigger'); await p.waitForTimeout(350);
  ok('mobile: tap opens sheet', await p.isVisible('.fd-account-panel a:has-text("Saved addresses")'));
  await p.screenshot({ path: 'home/am_user_m.png' });
  await p.mouse.click(195, 120); await p.waitForTimeout(300);
  ok('mobile: tap outside closes', !(await p.isVisible('.fd-account-panel a:has-text("Saved addresses")')));
  await p.tap('.fd-account-trigger'); await p.waitForTimeout(300);
  await Promise.all([p.waitForNavigation(), p.tap('.fd-account-signout button')]);
  ok('mobile: sign out works', !(await p.content()).includes('Hello, '));
  await ctx.close();
  ok('no page errors', errs.length === 0, errs.join(' | '));
  console.log('\nISSUES:', results.filter(r => !r[0]).map(r => r[1]).join('; ') || 'none');
  await b.close();
})();
