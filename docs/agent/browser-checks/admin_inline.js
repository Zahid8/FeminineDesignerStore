const { chromium } = require('playwright');
const base = 'http://127.0.0.1:8766';
(async () => { const b = await chromium.launch(); const tag = process.env.TAG || 'a';
  for (const [vt, vp, m] of [['d', { width: 1440, height: 900 }, false], ['m', { width: 390, height: 844 }, true]]) {
    const ctx = await b.newContext({ viewport: vp, isMobile: m, hasTouch: m, deviceScaleFactor: 2 }); const p = await ctx.newPage();
    await p.goto(base + '/admin/login/'); await p.fill('#id_username', 'qa_admin'); await p.fill('#id_password', 'Qa-admin-123!');
    await Promise.all([p.waitForNavigation(), p.click('input[type=submit], button[type=submit]')]);
    await p.goto(base + '/admin/store/product/59/change/', { waitUntil: 'networkidle' });
    const g = await p.$('#images-group, .inline-group'); await g.scrollIntoViewIfNeeded(); await g.screenshot({ path: `home/${tag}_inline_${vt}.png` });
    await p.goto(base + '/admin/store/product/', { waitUntil: 'networkidle' });
    await p.screenshot({ path: `home/${tag}_list_${vt}.png` });
    await p.goto(base + '/admin/store/productimage/', { waitUntil: 'networkidle' });
    await p.screenshot({ path: `home/${tag}_imglist_${vt}.png` });
    await ctx.close(); }
  await b.close(); })();
