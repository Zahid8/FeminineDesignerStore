const { chromium } = require('playwright');
const base = 'http://127.0.0.1:8766';
const pages = [['index', '/admin/'], ['products', '/admin/store/product/'], ['product', '/admin/store/product/59/change/'], ['images', '/admin/store/productimage/'], ['orders', '/admin/store/order/'], ['order', '/admin/store/order/20/change/']];
(async () => {
  const b = await chromium.launch(); const tag = process.env.TAG || 'a';
  for (const [vt, vp, mobile] of [['m', { width: 390, height: 844 }, true], ['t', { width: 820, height: 1180 }, true], ['d', { width: 1440, height: 900 }, false]]) {
    const ctx = await b.newContext({ viewport: vp, isMobile: mobile, hasTouch: mobile }); const p = await ctx.newPage();
    await p.goto(base + '/admin/login/'); await p.fill('#id_username', 'qa_admin'); await p.fill('#id_password', 'Qa-admin-123!');
    await Promise.all([p.waitForNavigation(), p.click('input[type=submit], button[type=submit]')]);
    for (const [n, u] of pages) {
      await p.goto(base + u, { waitUntil: 'networkidle' });
      const w = await p.evaluate(() => document.documentElement.scrollWidth);
      if (vt !== 'd' || n === 'product') await p.screenshot({ path: `home/${tag}_${vt}_${n}.png`, fullPage: n !== 'index' });
      console.log(vt, n, 'scrollWidth', w, '/', vp.width);
    }
    await ctx.close();
  }
  await b.close();
})();
