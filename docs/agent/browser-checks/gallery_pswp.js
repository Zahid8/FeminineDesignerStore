const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch(); const base = process.env.SHOP || 'http://127.0.0.1:8766';
  const errs = [];
  for (const [t, vp, mobile] of [['m', {width:390,height:844}, true], ['d', {width:1440,height:900}, false]]) {
    const ctx = await b.newContext({ viewport: vp, isMobile: mobile, hasTouch: mobile });
    const p = await ctx.newPage(); p.on('pageerror', e => errs.push(e.message)); p.on('console', m => { if (m.type()==='error') errs.push(m.text()); });
    await p.goto(base + '/products/silk-embroidered-blouse/', { waitUntil: 'networkidle' });
    await p.screenshot({ path: `polish/g_pdp_${t}.png` });
    const ar = await p.$eval('.product-gallery .carousel-inner', e => getComputedStyle(e).aspectRatio + ' ' + Math.round(e.getBoundingClientRect().width) + 'x' + Math.round(e.getBoundingClientRect().height));
    console.log(t, 'frame', ar);
    if (mobile) await p.tap('.product-gallery .carousel-inner'); else await p.click('[data-gallery-open]');
    await p.waitForSelector('.pswp--open', { timeout: 5000 }); await p.waitForTimeout(700);
    await p.screenshot({ path: `polish/g_pswp_${t}.png` });
    console.log(t, 'counter', await p.textContent('.pswp__counter'));
    await p.click('.pswp__button--arrow--next').catch(() => p.keyboard.press('ArrowRight')); await p.waitForTimeout(500);
    console.log(t, 'after next', await p.textContent('.pswp__counter'));
    await p.keyboard.press('Escape'); await p.waitForTimeout(700);
    console.log(t, 'closed', !(await p.$('.pswp--open')), 'carousel idx', await p.$$eval('.product-gallery .carousel-item', a => a.findIndex(x => x.classList.contains('active'))));
    await p.goto(base + '/shop/', { waitUntil: 'networkidle' }); await p.screenshot({ path: `polish/g_shop_${t}.png` });
    await ctx.close();
  }
  console.log('errors', errs.filter(e => !/404/.test(e)));
  await b.close();
})();
