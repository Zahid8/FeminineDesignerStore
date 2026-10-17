// Mobile usability scan: small tap targets and tiny text on interactive controls.
const { chromium } = require('playwright');
const base = 'http://127.0.0.1:8766';
const pages = ['/', '/shop/', '/products/silk-embroidered-blouse/', '/products/silk-embroidered-blouse/?fit=custom', '/cart/', '/checkout/', '/accounts/login/', '/accounts/register/', '/contact/', '/faq/', '/book-appointment/', '/track-order/', '/wishlist/'];
(async () => {
  const b = await chromium.launch(); const ctx = await b.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true }); const p = await ctx.newPage();
  await p.goto(base + '/products/silk-embroidered-blouse/'); await Promise.all([p.waitForNavigation(), p.evaluate(() => document.getElementById('pdp-cart-form').submit())]);
  for (const path of pages) {
    await p.goto(base + path, { waitUntil: 'load' }); await p.waitForTimeout(400);
    const r = await p.evaluate(() => {
      const out = [];
      document.querySelectorAll('a[href], button, input:not([type=hidden]), select, textarea, label[for], summary').forEach(e => {
        const cs = getComputedStyle(e); if (cs.display === 'none' || cs.visibility === 'hidden' || e.closest('[hidden], .offcanvas, .search-popup, dialog, .fd-mega, .fd-sticky-buy, .swiper-slide:not(.swiper-slide-visible)')) return;
        const r = e.getBoundingClientRect(); if (r.width === 0 || r.height === 0) return;
        const inline = cs.display === 'inline' && e.tagName === 'A' && e.closest('p, li, small, dd, .fd-summary-row, figcaption, .fd-crumbs');
        const text = (e.textContent || e.value || e.getAttribute('aria-label') || '').trim().slice(0, 30);
        if (!inline && (r.height < 34 || r.width < 34) && e.tagName !== 'INPUT') out.push(`small ${Math.round(r.width)}x${Math.round(r.height)} <${e.tagName.toLowerCase()} ${e.className.toString().slice(0, 30)}> "${text}"`);
        if (parseFloat(cs.fontSize) < 10 && text && !inline) out.push(`tiny ${cs.fontSize} <${e.tagName.toLowerCase()} ${e.className.toString().slice(0, 30)}> "${text}"`);
      });
      return [...new Set(out)].slice(0, 12);
    });
    if (r.length) console.log(path, '\n  ' + r.join('\n  '));
  }
  await b.close(); console.log('tap scan done');
})();
