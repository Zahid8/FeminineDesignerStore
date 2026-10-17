const { chromium } = require('playwright');
const base = 'http://127.0.0.1:8766';
(async () => {
  const b = await chromium.launch();
  for (const [tag, opts] of [['d', { viewport: { width: 1440, height: 900 } }], ['m', { viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true }]]) {
    const p = await (await b.newContext(opts)).newPage(); const errs = []; p.on('pageerror', e => errs.push(e.message));
    await p.goto(base + '/products/silk-embroidered-blouse/?fit=custom', { waitUntil: 'load' }); await p.waitForTimeout(800);
    await p.locator('#customize-section').screenshot({ path: `/tmp/fdshot/guide_builder_${tag}.png` });
    const asideInForm = await p.$('#custom-fit-form .fd-guide');
    await p.click('.fd-guide-btn'); await p.waitForTimeout(500);
    const open = await p.$eval('#measure-guide-dialog', d => d.open);
    await p.screenshot({ path: `/tmp/fdshot/guide_dialog_${tag}.png` });
    await p.click('#measure-guide-dialog [data-close-dialog]'); await p.waitForTimeout(300);
    const closed = await p.$eval('#measure-guide-dialog', d => !d.open);
    console.log(tag, 'guide inside form:', !!asideInForm, '| dialog opens:', open, '| closes:', closed, '| errors:', errs);
  }
  await b.close();
})();
