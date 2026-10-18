// Full design QA of the customer-facing site (demo server :8766).
// Checks every page at 5 widths for: sideways scroll, text escaping its box,
// text touching a box edge (no padding), clipped text, overlapping text,
// low contrast, broken images, small tap targets (phones), JS/HTTP errors.
const { chromium } = require('playwright');
const fs = require('fs');
const base = process.env.BASE || 'http://127.0.0.1:8766';
const ORDER = process.env.ORDER, TOKEN = process.env.TOKEN;
const OUT = process.env.OUT || '/tmp/fdshot/qa';
fs.mkdirSync(OUT, { recursive: true });
const ONLY = process.env.ONLY ? process.env.ONLY.split(',') : null;

const PAGES = [
  ['home', '/'], ['shop', '/shop/'], ['shop-filtered', '/shop/?category=blouses&sort=price_asc'],
  ['pdp', '/products/silk-embroidered-blouse/'], ['pdp-soldout', '/products/aggregate-stock/'],
  ['pdp-custom', '/products/silk-embroidered-blouse/?fit=custom'],
  ['cart', '/cart/'], ['checkout', '/checkout/'], ['wishlist', '/wishlist/'],
  ['login', '/accounts/login/', 'anon'], ['register', '/accounts/register/', 'anon'], ['phone-login', '/accounts/login/phone/', 'anon'],
  ['password-reset', '/accounts/password/reset/', 'anon'],
  ['profile', '/accounts/profile/'], ['profile-edit', '/accounts/profile/edit/'], ['orders', '/accounts/orders/'],
  ['order-detail', `/accounts/orders/${ORDER}/`], ['invoice', `/accounts/orders/${ORDER}/invoice/`],
  ['order-success', `/orders/${ORDER}/success/`],
  ['fitting-created', `/customizations/${TOKEN}/created/`], ['fitting-detail', `/customizations/${TOKEN}/`],
  ['contact', '/contact/'], ['faq', '/faq/'], ['appointment', '/book-appointment/'],
  ['track', '/track-order/'], ['diaries', '/client-diaries/'], ['page', '/pages/shipping-policy/'], ['404', '/no-such-page/'],
];
const VIEWPORTS = [
  ['m360', { width: 360, height: 780 }, true], ['m390', { width: 390, height: 844 }, true],
  ['t768', { width: 768, height: 1024 }, true], ['d1024', { width: 1024, height: 768 }, false], ['d1440', { width: 1440, height: 900 }, false],
];

function audit() {
  const vw = document.documentElement.clientWidth;
  const issues = [];
  const path = (el) => {
    const parts = []; let e = el;
    while (e && e.nodeType === 1 && parts.length < 4) {
      let s = e.tagName.toLowerCase();
      if (e.id) { s += '#' + e.id; parts.unshift(s); break; }
      const cls = [...e.classList].filter(c => !/^(col|row|g-|d-|mb-|mt-|p-|px-|py-|me-|ms-|gap-|w-|h-|text-|align|justify|flex|order)/.test(c)).slice(0, 2);
      if (cls.length) s += '.' + cls.join('.');
      parts.unshift(s); e = e.parentElement;
    }
    return parts.join(' > ');
  };
  const parseRGBA = (c) => { const m = c.match(/rgba?\(([^)]+)\)/); if (!m) return null; const p = m[1].split(',').map(x => parseFloat(x)); return { r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1 }; };
  const visible = (el) => {
    for (let e = el; e && e.nodeType === 1; e = e.parentElement) {
      const cs = getComputedStyle(e);
      if (cs.display === 'none' || cs.visibility === 'hidden' || parseFloat(cs.opacity) < 0.05) return false;
      if (e.parentElement && e.parentElement.tagName === 'DETAILS' && !e.parentElement.open && e.tagName !== 'SUMMARY') return false;
      if (e.matches('[hidden], .offcanvas:not(.show), .search-popup:not(.is-visible), dialog:not([open]), .visually-hidden, .skip-link, .fd-mega:not(.is-open), .fd-sticky-buy:not(.is-visible), .fd-toasts, .preloader, template, noscript')) return false;
    }
    return true;
  };
  const isFixed = (el) => { for (let e = el; e && e.nodeType === 1; e = e.parentElement) { const p = getComputedStyle(e).position; if (p === 'fixed' || p === 'sticky') return true; } return false; };
  const boxedCache = new Map();
  const boxed = (el) => {
    if (boxedCache.has(el)) return boxedCache.get(el);
    let res = false;
    if (el !== document.body && el !== document.documentElement) {
      const cs = getComputedStyle(el); const bg = parseRGBA(cs.backgroundColor);
      const borders = ['Top', 'Right', 'Bottom', 'Left'].filter(s => parseFloat(cs['border' + s + 'Width']) > 0 && (parseRGBA(cs['border' + s + 'Color']) || { a: 0 }).a > 0.15).length;
      const hasBg = (bg && bg.a > 0.2) || cs.backgroundImage !== 'none';
      const shadow = cs.boxShadow !== 'none';
      res = (hasBg && (shadow || borders >= 2 || parseFloat(cs.borderTopLeftRadius) > 4)) || borders >= 3 || (shadow && parseFloat(cs.borderTopLeftRadius) > 4);
      const r = el.getBoundingClientRect();
      if (r.width >= vw * 0.97) res = false; // full-bleed sections
      if (el.matches('input, select, textarea, img, svg, video, canvas, .carousel-inner, .swiper, .product-gallery, .fd-card-media, .fd-editorial, .fd-promo, .offcanvas, .fd-header, .fd-announce')) res = false;
    }
    boxedCache.set(el, res); return res;
  };
  const nearestBox = (el) => { for (let e = el; e && e !== document.body; e = e.parentElement) if (boxed(e)) return e; return null; };
  const lum = (c) => { const f = v => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }; return 0.2126 * f(c.r) + 0.7152 * f(c.g) + 0.0722 * f(c.b); };
  const effBg = (el) => { for (let e = el; e; e = e.parentElement) { const cs = getComputedStyle(e); if (cs.backgroundImage !== 'none' && !cs.backgroundImage.startsWith('linear-gradient(rgba(0, 0, 0, 0)')) return null; const c = parseRGBA(cs.backgroundColor); if (c && c.a > 0.9) return c; } return { r: 255, g: 255, b: 255, a: 1 }; };

  if (document.documentElement.scrollWidth > vw + 1) issues.push({ type: 'sideways-scroll', where: `page is ${document.documentElement.scrollWidth}px wide in a ${vw}px window` });

  // Text nodes
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, { acceptNode: n => n.textContent.trim().length > 1 ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT });
  const texts = []; const seenContrast = new Set();
  for (let n; (n = walker.nextNode());) {
    const el = n.parentElement; if (!el || el.closest('script, style, option, select, svg') || !visible(el)) continue;
    const range = document.createRange(); range.selectNodeContents(n);
    const rects = [...range.getClientRects()].filter(r => r.width > 1 && r.height > 1); if (!rects.length) continue;
    const box = nearestBox(el); const label = n.textContent.trim().replace(/\s+/g, ' ').slice(0, 40);
    if ([el, el.parentElement].some(x => x && getComputedStyle(x).textOverflow === "ellipsis")) continue; // truncated on purpose
    for (const r of rects) {
      texts.push({ r, el, fixed: isFixed(el), label });
      if (box && !(["auto", "scroll"].includes(getComputedStyle(box).overflowX))) { // scrollers (category bar) clip by design
        const b = box.getBoundingClientRect(); const bcs = getComputedStyle(box);
        const out = Math.max(b.left - r.left, r.right - b.right, b.top - r.top, r.bottom - b.bottom);
        if (out > 1.5) issues.push({ type: 'text-escapes-box', where: path(box), text: label, by: Math.round(out) + 'px' });
        else {
          const gapL = r.left - b.left, gapR = b.right - r.right;
          const pad = Math.min(gapL, gapR);
          const isPill = b.height < 48; // badges, chips, buttons: small padding is fine
          if (!isPill && pad < 6 && !box.matches('.btn, button, a, .fd-badge, .fd-status-pill, label, .fd-chip, .alert')) issues.push({ type: 'text-touches-edge', where: path(box), text: label, gap: Math.round(pad) + 'px' });
        }
        if (bcs.overflow !== 'visible' && out > 0.5) issues.push({ type: 'text-clipped', where: path(box), text: label });
      }
    }
    // Contrast (once per element)
    if (!seenContrast.has(el)) {
      seenContrast.add(el);
      const cs = getComputedStyle(el); const fg = parseRGBA(cs.color); const bg = effBg(el);
      if (fg && bg && fg.a > 0.5) {
        const L1 = lum(fg), L2 = lum(bg); const ratio = (Math.max(L1, L2) + 0.05) / (Math.min(L1, L2) + 0.05);
        const size = parseFloat(cs.fontSize), bold = parseInt(cs.fontWeight) >= 600;
        const need = (size >= 24 || (size >= 18.6 && bold)) ? 3 : 4.5;
        if (ratio < need - 0.15 && !el.closest('[disabled], .text-decoration-line-through, del, s, .fd-compare')) issues.push({ type: 'low-contrast', where: path(el), text: label, ratio: ratio.toFixed(2) + ' (needs ' + need + ')' });
      }
    }
    // Clipped by an overflow:hidden ancestor (ellipsis is intentional)
    const cs = getComputedStyle(el);
    if ((cs.overflow === 'hidden' || cs.overflowX === 'hidden') && cs.textOverflow !== 'ellipsis' && el.scrollWidth > el.clientWidth + 2 && !el.closest('.swiper, .fd-marquee, .carousel, .fd-filter-scroll')) issues.push({ type: 'text-clipped', where: path(el), text: label });
  }
  // Overlapping text (different elements, neither fixed); ignore text clipped away by an overflow:hidden ancestor
  const clippedAway = (x) => { for (let e = x.el.parentElement; e && e !== document.body; e = e.parentElement) { const cs = getComputedStyle(e); if (cs.overflow !== 'visible') { const b = e.getBoundingClientRect(); if (x.r.top >= b.bottom - 1 || x.r.bottom <= b.top + 1 || x.r.left >= b.right - 1 || x.r.right <= b.left + 1) return true; } } return false; };
  const t = texts.filter(x => !x.fixed && !clippedAway(x));
  for (let i = 0; i < t.length; i++) for (let j = i + 1; j < t.length; j++) {
    const a = t[i], b = t[j]; if (a.el === b.el || a.el.contains(b.el) || b.el.contains(a.el)) continue;
    const w = Math.min(a.r.right, b.r.right) - Math.max(a.r.left, b.r.left), h = Math.min(a.r.bottom, b.r.bottom) - Math.max(a.r.top, b.r.top);
    if (w > 2 && h > 2 && w * h > 0.25 * Math.min(a.r.width * a.r.height, b.r.width * b.r.height)) issues.push({ type: 'text-overlap', where: path(a.el) + ' ⟂ ' + path(b.el), text: a.label + ' / ' + b.label });
  }
  // Broken images
  document.querySelectorAll('img').forEach(img => { if (visible(img) && img.complete && img.naturalWidth === 0 && img.getAttribute('src')) issues.push({ type: 'broken-image', where: path(img), text: img.getAttribute('src').slice(0, 80) }); });
  return issues;
}

function taps() {
  const out = [];
  document.querySelectorAll('a[href], button, select, summary, input[type=checkbox], input[type=radio], label[for]').forEach(e => {
    const cs = getComputedStyle(e);
    if (cs.display === 'none' || cs.visibility === 'hidden' || e.closest('[hidden], .offcanvas:not(.show), dialog:not([open]), .search-popup:not(.is-visible), .visually-hidden, .fd-sticky-buy:not(.is-visible), .fd-mega, .fd-toasts')) return;
    if (e.matches('input[type=radio], input[type=checkbox]') && (cs.opacity === '0' || e.getBoundingClientRect().width < 2)) return; // styled via label
    const r = e.getBoundingClientRect(); if (r.width < 2 || r.height < 2) return;
    const inline = cs.display === 'inline' && e.closest('p, li, small, dd, td, .fd-summary-row, figcaption, .fd-crumbs, .fd-guide-help, .fd-prose, .fd-footer');
    if (inline) return;
    if (r.height < 36 && !e.matches('label[for]')) out.push({ type: 'small-tap-target', where: (e.className || e.tagName).toString().slice(0, 50), text: (e.textContent || e.getAttribute('aria-label') || '').trim().replace(/\s+/g, ' ').slice(0, 30) + ` ${Math.round(r.width)}×${Math.round(r.height)}` });
  });
  return out;
}

(async () => {
  const b = await chromium.launch();
  const all = [];
  for (const [vtag, size, mobile] of VIEWPORTS) {
    const mk = async (signedIn) => {
      const ctx = await b.newContext({ viewport: size, isMobile: mobile, hasTouch: mobile, reducedMotion: 'reduce' });
      const p = await ctx.newPage();
      if (signedIn) {
        await p.goto(base + '/accounts/login/'); await p.fill('input[name=username]', 'qa@example.com'); await p.fill('input[name=password]', 'Qa-pass-12345!');
        await Promise.all([p.waitForNavigation(), p.click('form.fd-form button[type=submit]')]);
        await p.goto(base + '/products/silk-embroidered-blouse/'); await Promise.all([p.waitForNavigation(), p.evaluate(() => document.getElementById('pdp-cart-form').submit())]);
      }
      return { ctx, p };
    };
    const signed = await mk(true), anon = await mk(false);
    for (const [name, url, who] of PAGES) {
      if (ONLY && !ONLY.includes(name)) continue;
      const { p } = who === 'anon' ? anon : signed;
      const errs = [];
      const onErr = e => errs.push({ type: 'js-error', where: url, text: e.message.slice(0, 80) });
      const onCon = m => { if (m.type() === 'error' && !/favicon|GL Driver|deprecated/i.test(m.text())) errs.push({ type: 'console-error', where: url, text: m.text().slice(0, 80) }); };
      const onRes = r => { if (r.status() >= 400 && r.url().startsWith(base) && !/favicon|no-such-page/.test(r.url())) errs.push({ type: 'http-' + r.status(), where: url, text: r.url().replace(base, '').slice(0, 80) }); };
      p.on('pageerror', onErr); p.on('console', onCon); p.on('response', onRes);
      await p.goto(base + url, { waitUntil: 'load' }).catch(e => errs.push({ type: 'nav-error', where: url, text: e.message.slice(0, 60) }));
      await p.evaluate(async () => { document.querySelectorAll('img[loading=lazy]').forEach(i => { i.loading = 'eager'; }); for (let y = 0; y < document.body.scrollHeight; y += 600) { window.scrollTo(0, y); await new Promise(r => setTimeout(r, 30)); } window.scrollTo(0, 0); });
      await p.waitForTimeout(700);
      const found = [...await p.evaluate(audit), ...(mobile && size.width < 768 ? await p.evaluate(taps) : []), ...errs];
      for (const f of found) all.push({ vp: vtag, page: name, ...f });
      if (vtag === 'm390' || vtag === 'd1440') await p.screenshot({ path: `${OUT}/${vtag}_${name}.jpg`, fullPage: true, type: 'jpeg', quality: 60 });
      p.off('pageerror', onErr); p.off('console', onCon); p.off('response', onRes);
    }
    await signed.ctx.close(); await anon.ctx.close();
  }
  await b.close();
  fs.writeFileSync(`${OUT}/issues.json`, JSON.stringify(all, null, 1));
  // Summary: group identical issues across viewports
  const groups = new Map();
  for (const i of all) { const k = [i.type, i.page, i.where, i.text].join(' | '); const g = groups.get(k) || { ...i, vps: new Set() }; g.vps.add(i.vp); groups.set(k, g); }
  const byType = {};
  for (const g of groups.values()) (byType[g.type] = byType[g.type] || []).push(g);
  for (const [type, list] of Object.entries(byType).sort()) {
    console.log(`\n## ${type} (${list.length})`);
    for (const g of list.slice(0, 40)) console.log(`- [${g.page}] ${g.where} — "${g.text || ''}" ${g.by || g.gap || g.ratio || ''} @ ${[...g.vps].join(',')}`);
  }
  console.log(`\nTOTAL distinct issues: ${groups.size}`);
})();
