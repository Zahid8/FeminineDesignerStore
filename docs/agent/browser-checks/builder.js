const { chromium } = require('playwright');
const base = 'http://127.0.0.1:8766';
(async () => {
  const b = await chromium.launch();
  for (const [tag, opts] of [['d', { viewport: { width: 1440, height: 900 } }], ['m', { viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true }]]) {
    const ctx = await b.newContext(opts); const p = await ctx.newPage(); const errs = []; p.on('pageerror', e => errs.push(e.message));
    await p.goto(base + '/shop/'); const href = await p.getAttribute('.product-item a', 'href');
    await p.goto(base + href + '?fit=custom', { waitUntil: 'networkidle' }); await p.waitForTimeout(800);
    await p.locator('#customize-section').scrollIntoViewIfNeeded(); await p.waitForTimeout(400);
    for (const [k, v] of Object.entries({ length: '15', chest: '36', waist: '30', armhole: '16', opening: '11', bicep: '13' })) { await p.fill('#id_' + k, v); }
    await p.locator('#customize-section').screenshot({ path: `/tmp/fdshot/t33_${tag}_step1.jpg`, type: 'jpeg', quality: 72 });
    await p.click('#customize-section .fd-unit-toggle button:has-text("cm")'); await p.waitForTimeout(300);
    const cmVal = await p.inputValue('#id_chest');
    await p.click('#customize-section button:has-text("Continue to style")'); await p.waitForTimeout(300);
    await p.click('label[for="sleeve-5"]');
    await p.click('#customize-section button:has-text("Review")'); await p.waitForTimeout(400);
    await p.locator('#customize-section').screenshot({ path: `/tmp/fdshot/t33_${tag}_step3.jpg`, type: 'jpeg', quality: 72 });
    await Promise.all([p.waitForNavigation(), p.click('#custom-fit-form button[type=submit]:has-text("Add Made-to-Measure")')]);
    const toast = await p.textContent('.fd-toast').catch(() => '');
    await p.goto(base + '/cart/', { waitUntil: 'networkidle' });
    const cartHasCustom = await p.evaluate(() => document.body.innerText.includes('MADE TO MEASURE') || document.body.innerText.includes('Made to measure'));
    await p.locator('.fd-cart-line').first().screenshot({ path: `/tmp/fdshot/t33_${tag}_cartline.jpg`, type: 'jpeg', quality: 72 });
    console.log(tag, '| chest in cm:', cmVal, '| toast:', (toast || '').trim().slice(0, 60), '| cart custom:', cartHasCustom, '| errors:', errs);
    await ctx.close();
  }
  await b.close();
})();
