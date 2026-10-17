const { chromium } = require('playwright');
const base = 'http://127.0.0.1:8766';
const pages = ['/', '/shop/', '/products/silk-embroidered-blouse/', '/products/silk-embroidered-blouse/?fit=custom', '/products/aggregate-stock/', '/cart/', '/checkout/', '/wishlist/', '/accounts/profile/', '/accounts/profile/edit/', '/accounts/orders/', `/accounts/orders/${process.env.ORDER}/`, `/orders/${process.env.ORDER}/success/`, `/customizations/${process.env.TOKEN}/`, `/customizations/${process.env.TOKEN}/created/`, '/contact/', '/book-appointment/', '/track-order/', '/faq/'];
(async () => {
  const b = await chromium.launch(); let bad = 0;
  for (const w of [360, 390]) {
    const ctx = await b.newContext({ viewport: { width: w, height: 800 }, isMobile: true, hasTouch: true, reducedMotion: 'reduce' }); const p = await ctx.newPage();
    await p.goto(base + '/accounts/login/'); await p.fill('input[name=username]', 'qa@example.com'); await p.fill('input[name=password]', 'Qa-pass-12345!');
    await Promise.all([p.waitForNavigation(), p.click('form.fd-form button[type=submit]')]);
    await p.goto(base + '/products/silk-embroidered-blouse/'); await Promise.all([p.waitForNavigation(), p.evaluate(() => document.getElementById('pdp-cart-form').submit())]);
    for (const u of pages) {
      await p.goto(base + u, { waitUntil: 'load' }); await p.waitForTimeout(300);
      const r = await p.evaluate(() => [...document.querySelectorAll('.btn, .fd-btn, button.fd-guide-btn')].filter(e => { const cs = getComputedStyle(e); if (cs.display === 'none' || e.closest('[hidden], .offcanvas:not(.show), dialog:not([open])') || e.getBoundingClientRect().width < 2) return false; const lh = parseFloat(cs.lineHeight) || parseFloat(cs.fontSize) * 1.5; const tw = document.createTreeWalker(e, NodeFilter.SHOW_TEXT); const tops = new Set(); for (let n; (n = tw.nextNode());) { if (!n.textContent.trim()) continue; const rg = document.createRange(); rg.selectNodeContents(n); [...rg.getClientRects()].filter(x => x.width > 2).forEach(x => tops.add(Math.round(x.top))); } return tops.size > 1; }).map(e => e.textContent.trim().replace(/\s+/g, ' ').slice(0, 40)));
      if (r.length) { bad += r.length; console.log(w, u, r); }
    }
    await ctx.close();
  }
  await b.close(); console.log('wrapped buttons:', bad);
})();
