const { chromium } = require('playwright');
const base = 'http://127.0.0.1:8766';
const pages = (process.env.PAGES || '/').split(',');
(async () => {
  const b = await chromium.launch();
  const ctx = await b.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, reducedMotion: 'reduce', deviceScaleFactor: 1 });
  const p = await ctx.newPage();
  await p.goto(base + '/accounts/login/'); await p.fill('input[name=username]', 'qa@example.com'); await p.fill('input[name=password]', 'Qa-pass-12345!');
  await Promise.all([p.waitForNavigation(), p.click('form.fd-form button[type=submit]')]);
  for (const url of pages) {
    await p.goto(base + url, { waitUntil: 'load' }); await p.waitForTimeout(600);
    const h = await p.evaluate(() => document.querySelector('footer') ? document.querySelector('footer').getBoundingClientRect().top + scrollY : document.body.scrollHeight);
    const tag = url.replace(/[^a-z0-9]+/gi, '_').replace(/^_|_$/g, '') || 'home';
    let i = 0;
    for (let y = 0; y < h && i < 9; y += 780, i++) { await p.evaluate(y => window.scrollTo(0, y), y); await p.waitForTimeout(250); await p.screenshot({ path: `/tmp/fdshot/scr/${tag}_${i}.png` }); }
    console.log(tag, i, 'screens');
  }
  await b.close();
})();
