const { chromium } = require('playwright');
const base = process.env.BASE || 'http://127.0.0.1:8766';
const URL = base + (process.env.PDP || '/products/aggregate-stock/') + '?fit=custom';
const R = [], I = [];
const ok = (n, c, d = '') => { R.push(`${c ? 'PASS' : 'FAIL'}  ${n}${d ? '  — ' + d : ''}`); if (!c) I.push(n); };
const inView = loc => loc.evaluate(e => { const r = e.getBoundingClientRect(); return !!e.offsetParent && r.top >= 0 && r.bottom <= innerHeight; }).catch(() => false);
(async () => {
  const b = await chromium.launch();
  for (const [tag, opts] of [['desktop', { viewport: { width: 1440, height: 900 } }], ['mobile', { viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true }]]) {
    const ctx = await b.newContext(opts); const p = await ctx.newPage(); let posts = 0;
    p.on('pageerror', e => I.push(`[${tag}] JS error: ${e.message}`));
    p.on('request', r => { if (r.method() === 'POST' && r.url().includes('/cart/add/')) posts++; });
    await p.goto(URL, { waitUntil: 'networkidle' }); await p.waitForTimeout(500);
    const pre = await p.$$eval('#customize-section input[data-measure][required]', is => is.filter(i => !i.value).map(i => i.name));
    ok(`[${tag}] setup mirrors live (opening+bicep empty)`, pre.join() === 'opening,bicep', pre.join());

    // A: Continue with missing fields -> stays, focuses Opening, error visible
    await p.click('#customize-section button:has-text("Continue to style")'); await p.waitForTimeout(700);
    const focused = await p.evaluate(() => document.activeElement && document.activeElement.id);
    ok(`[${tag}] Continue blocked; focus on first missing (Opening)`, focused === 'id_opening', focused);
    const errA = p.locator('#customize-section .fd-measure.has-error .fd-field-error:visible').first();
    ok(`[${tag}] inline error visible on screen`, await inView(errA), await errA.textContent().catch(() => ''));

    // B: jump to review via step tab and press Add -> no POST, back to step 1
    await p.click('.fd-builder-steps button:has-text("Review")'); await p.waitForTimeout(300);
    ok(`[${tag}] review lists what is missing`, (await p.textContent('[data-mtm-problems]')).includes('opening'));
    await p.click('#custom-fit-form button[type=submit]:has-text("Add Made-to-Measure")'); await p.waitForTimeout(800);
    ok(`[${tag}] Add with missing fields does not submit`, posts === 0, `posts=${posts}`);
    ok(`[${tag}] ...and returns to measurements with focus on Opening`, (await p.evaluate(() => document.activeElement.id)) === 'id_opening');
    const btnBusy = await p.getAttribute('#custom-fit-form button[type=submit]:has-text("Add Made-to-Measure")', 'aria-busy');
    ok(`[${tag}] submit button not stuck in busy state`, btnBusy !== 'true');

    // C: out of range
    await p.fill('#id_opening', '11'); await p.fill('#id_bicep', '90');
    await p.click('#customize-section button:has-text("Continue to style")'); await p.waitForTimeout(500);
    ok(`[${tag}] out-of-range bicep blocked with range message`, ((await p.textContent('#customize-section')) || '').includes('Bicep should be between 6–30 in'));

    // D: cm unit valid -> proceeds
    await p.fill('#id_bicep', '13');
    await p.click('#customize-section .fd-unit-toggle button:has-text("cm")'); await p.waitForTimeout(200);
    await p.click('#customize-section button:has-text("Continue to style")'); await p.waitForTimeout(300);
    ok(`[${tag}] valid values (in cm) move to Style`, await p.isVisible('label[for="sleeve-5"]'));
    await p.click('label[for="sleeve-5"]'); await p.click('#customize-section button:has-text("Review")');
    ok(`[${tag}] no warning on review when complete`, !(await p.isVisible('[data-mtm-problems]')));
    await Promise.all([p.waitForNavigation(), p.click('#custom-fit-form button[type=submit]:has-text("Add Made-to-Measure")')]);
    const toast = (await p.$$eval('[data-toast]', ts => ts.map(t => t.textContent.trim()))).join(' ');
    ok(`[${tag}] added to bag`, /made-to-measure/.test(toast), toast.replace(/\s+/g, ' ').slice(0, 80));
    await p.goto(base + '/cart/');
    const cart = (await p.textContent('main')).replace(/\s+/g, ' ');
    ok(`[${tag}] cart shows custom line with bicep 13 in`, cart.includes('Made to measure') && cart.includes('Bicep13 in'), cart.match(/Length.{0,120}/)?.[0]);
    await ctx.close();
  }
  await b.close();
  console.log(R.join('\n')); console.log('\nISSUES:', I.length ? '\n' + I.join('\n') : 'none');
})();
