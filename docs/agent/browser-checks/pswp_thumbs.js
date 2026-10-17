const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch(); const errs = [];
  for (const [t, vp, mobile] of [['m', {width:390,height:844}, true], ['d', {width:1440,height:900}, false]]) {
    const ctx = await b.newContext({ viewport: vp, isMobile: mobile, hasTouch: mobile }); const p = await ctx.newPage(); p.on('pageerror', e => errs.push(e.message));
    await p.goto('http://127.0.0.1:8766/products/rani-pink-floral-brocade-blouse/', { waitUntil: 'networkidle' });
    await p.click('[data-gallery-open]'); await p.waitForSelector('.pswp__fd-thumb'); await p.waitForTimeout(600);
    const n = await p.$$eval('.pswp__fd-thumb', a => a.length);
    await p.click('.pswp__fd-thumb:nth-child(3)'); await p.waitForTimeout(500);
    console.log(t, 'thumbs', n, 'counter', await p.textContent('.pswp__counter'), 'active', await p.$eval('.pswp__fd-thumb.is-active', e => [...e.parentNode.children].indexOf(e)));
    await p.screenshot({ path: `home/pswp_thumbs_${t}.png` });
    await ctx.close();
  }
  console.log('errors', errs); await b.close();
})();
