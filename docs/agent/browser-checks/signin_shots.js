const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch(); const base = 'http://127.0.0.1:8766'; const errs = [];
  const ctx = await b.newContext({ viewport: {width:390,height:844}, isMobile: true, hasTouch: true, deviceScaleFactor: 2 });
  const p = await ctx.newPage(); p.on('pageerror', e => errs.push(e.message));
  for (const [n, u] of [['phone', '/accounts/login/phone/'], ['email', '/accounts/login/?method=email'], ['register', '/accounts/register/']]) {
    await p.goto(base + u, { waitUntil: 'networkidle' }); await p.waitForTimeout(1500);
    const f = await p.$('.fd-auth-form'); await f.screenshot({ path: `home/signin_${n}.png` });
    console.log(n, 'google iframe', !!(await p.$('.fd-google-btn iframe')));
  }
  console.log('errors', errs); await b.close();
})();
