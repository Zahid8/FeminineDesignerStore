const { chromium } = require('playwright');
const base = 'http://127.0.0.1:8766'; const out = '/tmp/fdshot/admin/';
(async () => {
  const b = await chromium.launch(); const errs = [];
  const ctx = await b.newContext({ viewport: { width: 1440, height: 900 } }); const p = await ctx.newPage();
  p.on('pageerror', e => errs.push('pageerror ' + e.message));
  p.on('response', r => { if (r.status() >= 400 && !r.url().includes('/media/')) errs.push(r.status() + ' ' + r.url()); });
  await p.goto(base + '/admin/login/'); await p.waitForTimeout(500); await p.screenshot({ path: out + 'n-login.png' });
  await p.fill('#id_username', 'neuadmin'); await p.fill('#id_password', 'neu-pass-123');
  await Promise.all([p.waitForNavigation(), p.click('input[type=submit]')]); await p.waitForTimeout(600);
  await p.screenshot({ path: out + 'n-index.png' });
  for (const [n, u] of [['orders', '/admin/store/order/'], ['products', '/admin/store/product/'], ['settings', '/admin/store/sitesettings/']]) {
    await p.goto(base + u); await p.waitForTimeout(400); await p.screenshot({ path: out + `n-${n}.png` });
  }
  await p.goto(base + '/admin/store/order/'); await Promise.all([p.waitForNavigation(), p.click('#result_list tbody tr:first-child th a')]);
  await p.waitForTimeout(400); await p.screenshot({ path: out + 'n-order-change.png', fullPage: true });
  await p.goto(base + '/admin/store/product/'); await Promise.all([p.waitForNavigation(), p.click('#result_list tbody tr:first-child th a')]);
  await p.screenshot({ path: out + 'n-product-change.png', fullPage: true });
  await p.goto(base + '/admin/store/order/'); await p.fill('#nav-filter', 'disc'); await p.waitForTimeout(200);
  const visible = await p.$$eval('#nav-sidebar tr', trs => trs.filter(t => t.offsetParent).map(t => t.textContent.trim()));
  console.log('filter "disc" ->', visible);
  await p.fill('#nav-filter', ''); 
  const m = await (await b.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, storageState: await ctx.storageState() })).newPage();
  m.on('pageerror', e => errs.push('m pageerror ' + e.message));
  await m.goto(base + '/admin/'); await m.waitForTimeout(500); await m.screenshot({ path: out + 'n-m-index.png' });
  await m.click('[data-fd-menu]'); await m.waitForTimeout(400); await m.screenshot({ path: out + 'n-m-menu.png' });
  await m.click('[data-fd-menu-close]', { position: { x: 360, y: 400 } }); await m.waitForTimeout(300);
  console.log('menu closed:', !(await m.evaluate(() => document.body.classList.contains('fd-nav-open'))));
  await m.goto(base + '/admin/store/order/'); await m.waitForTimeout(400); await m.screenshot({ path: out + 'n-m-orders.png' });
  console.log('errors:', errs);
  await b.close();
})();
