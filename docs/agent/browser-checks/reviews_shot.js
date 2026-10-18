const { chromium } = require('playwright');
(async () => { const b = await chromium.launch(); const ctx = await b.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, deviceScaleFactor: 2 }); const p = await ctx.newPage(); const errs=[]; p.on('pageerror', e => errs.push(e.message));
  await p.goto('http://127.0.0.1:8766/products/rani-pink-floral-brocade-blouse/', { waitUntil: 'networkidle' });
  await (await p.$('.fd-pdp-info h1')).scrollIntoViewIfNeeded(); await p.screenshot({ path: 'home/rv_top.png' });
  await (await p.$('#reviews')).screenshot({ path: 'home/rv_section.png' });
  await p.goto('http://127.0.0.1:8766/shop/?sort=newest', { waitUntil: 'networkidle' });
  const card = await p.$('.product-item:has(.fd-card-rating)'); if (card) { await card.scrollIntoViewIfNeeded(); await p.waitForTimeout(1500); } if (card) await card.screenshot({ path: 'home/rv_card.png' }); else console.log('no rated card on first page');
  console.log('errors', errs); await b.close(); })();
