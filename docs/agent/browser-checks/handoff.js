const { chromium } = require('playwright');
const bill = 'http://127.0.0.1:3011', shop = 'http://127.0.0.1:8770';
const R = [], I = []; const ok = (n, c, d = '') => { R.push(`${c ? 'PASS' : 'FAIL'}  ${n}${d ? '  — ' + d : ''}`); if (!c) I.push(n); };
(async () => {
  const b = await chromium.launch();
  // Not signed in to the billing app: the button route must not hand out a link
  const anon = await b.newContext();
  const r = await anon.request.get(bill + '/storefront-admin', { maxRedirects: 0 });
  ok('handoff route needs the billing staff login', [302, 307].includes(r.status()) && (r.headers().location || '').includes('/login'), `${r.status()} ${r.headers().location}`);

  const ctx = await b.newContext({ viewport: { width: 1440, height: 900 } }); const p = await ctx.newPage(); p.setDefaultTimeout(60000);
  await p.goto(bill + '/login'); await p.fill('input[type=password]', 'feminine@222'); await Promise.all([p.waitForNavigation(), p.click('button[type=submit]')]);
  await p.goto(bill + '/online-orders', { waitUntil: 'load' }); await p.waitForTimeout(1500);
  const btn = p.locator('a:has-text("Edit storefront")');
  if (await btn.count() === 0) { await p.screenshot({ path: '/tmp/fdshot/handoff_missing.png', fullPage: true }); console.log('page text:', (await p.textContent('main')).replace(/\s+/g, ' ').slice(0, 300)); }
  ok('Online Orders shows the big Edit storefront button', await btn.count() === 1 && (await btn.boundingBox()).height >= 50);
  await p.locator('main').screenshot({ path: '/tmp/fdshot/handoff_button.png' });
  let handoffUrl = '';
  ctx.on('request', r => { if (r.url().includes('/admin/handoff/?t=')) handoffUrl = r.url(); });
  const [popup] = await Promise.all([ctx.waitForEvent('page'), btn.click()]);
  await popup.waitForLoadState('load'); await popup.waitForTimeout(800);
  ok('opens the shop admin in a new tab, no password asked', popup.url() === shop + '/admin/' && (await popup.textContent('body')).includes('Store management'), popup.url());
  const who = await popup.textContent('#user-tools').catch(() => '');
  ok('signed in as the manager superuser', /manager/i.test(who), who.replace(/\s+/g, ' ').trim().slice(0, 60));
  await popup.screenshot({ path: '/tmp/fdshot/handoff_admin.png' });
  const users = await popup.goto(shop + '/admin/auth/user/');
  ok('manager can open superuser-only pages (Users)', users.status() === 200);
  // The same link cannot be replayed
  const replay = await (await b.newContext()).request.get(handoffUrl, { maxRedirects: 0 });
  ok('a handoff link works once and is then rejected', !!handoffUrl && replay.status() === 403, `${handoffUrl ? 'captured' : 'no url'} → ${replay.status()}`);
  await b.close();
  console.log(R.join('\n')); console.log('\nISSUES:', I.length ? '\n' + I.join('\n') : 'none');
})();
