// Finds elements that overflow the viewport or their container on every customer page (demo :8766).
const { chromium } = require('playwright');
const base = 'http://127.0.0.1:8766';
const pages = ['/', '/shop/', '/products/silk-embroidered-blouse/', '/products/silk-embroidered-blouse/?fit=custom', '/cart/', '/checkout/', '/wishlist/', '/accounts/login/', '/accounts/register/', '/accounts/login/phone/', '/accounts/profile/', '/accounts/orders/', '/contact/', '/faq/', '/book-appointment/', '/track-order/', '/client-diaries/', '/no-such-page/'];
(async () => {
  const b = await chromium.launch();
  for (const [tag, opts] of [['d', { viewport: { width: 1440, height: 900 } }], ['m', { viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true }]]) {
    const ctx = await b.newContext(opts); const p = await ctx.newPage();
    await p.goto(base + '/accounts/login/'); await p.fill('input[name=username]', 'e2e@example.com').catch(()=>{}); await p.fill('input[name=password]', 'E2e-pass-123!').catch(()=>{});
    await Promise.all([p.waitForNavigation().catch(()=>{}), p.click('form.fd-form button[type=submit]').catch(()=>{})]);
    await p.goto(base + '/products/silk-embroidered-blouse/'); await Promise.all([p.waitForNavigation(), p.evaluate(() => document.getElementById('pdp-cart-form').submit())]);
    for (const path of pages) {
      await p.goto(base + path, { waitUntil: 'load' }); await p.waitForTimeout(500);
      const r = await p.evaluate(() => {
        const vw = document.documentElement.clientWidth; const out = [];
        const docOver = document.documentElement.scrollWidth > vw + 1;
        document.querySelectorAll('body *').forEach(e => {
          const cs = getComputedStyle(e); if (cs.display === 'none' || cs.visibility === 'hidden' || cs.position === 'fixed') return;
          const r = e.getBoundingClientRect(); if (r.width === 0) return;
          if (r.right > vw + 1 && !e.closest('.swiper, .fd-marquee, .offcanvas, .search-popup, [data-fd-scroll]')) out.push('viewport: ' + (e.className || e.tagName).toString().slice(0, 60) + ' right=' + Math.round(r.right));
          const par = e.parentElement; if (par && par !== document.body) { const pr = par.getBoundingClientRect(); const pcs = getComputedStyle(par);
            if (r.right > pr.right + 2 && pcs.overflowX === 'visible' && !e.closest('.swiper, .fd-marquee, .offcanvas, .search-popup') && r.width > 40) out.push('parent: ' + (e.className || e.tagName).toString().slice(0, 50) + ' in ' + (par.className || par.tagName).toString().slice(0, 40)); }
        });
        return { docOver, out: [...new Set(out)].slice(0, 6) };
      });
      if (r.docOver || r.out.length) console.log(tag, path, r.docOver ? 'PAGE SCROLLS SIDEWAYS' : '', r.out);
    }
    await ctx.close();
  }
  await b.close(); console.log('overflow scan done');
})();
