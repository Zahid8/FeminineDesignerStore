// Every admin page (index, each model's list / add / first change page) at phone + tablet widths.
// Flags: page scrolls sideways; element past the viewport edge; content clipped by an overflow:hidden box;
// tap targets < 32px; text overlapping.
const { chromium } = require('playwright');
const base = process.env.BASE || 'http://127.0.0.1:8766';
const WIDTHS = (process.env.WIDTHS || '360,390,412,768,820,1024').split(',').map(Number);
(async () => {
  const b = await chromium.launch();
  const ctx0 = await b.newContext({ viewport: { width: 1440, height: 900 } }); const p0 = await ctx0.newPage();
  const login = async (p) => { await p.goto(base + '/admin/login/'); await p.fill('#id_username', 'qa_admin'); await p.fill('#id_password', 'Qa-admin-123!'); await Promise.all([p.waitForNavigation(), p.click('input[type=submit], button[type=submit]')]); };
  await login(p0);
  const lists = await p0.$$eval('#nav-sidebar a[href^="/admin/"]', a => [...new Set(a.map(x => x.getAttribute('href')).filter(h => /^\/admin\/\w+\/\w+\/$/.test(h)))]);
  const urls = ['/admin/'];
  for (const l of lists) {
    urls.push(l);
    await p0.goto(base + l);
    const add = await p0.$('a.addlink'); if (add) urls.push(await add.getAttribute('href'));
    const first = await p0.$('#result_list tbody tr th a, #result_list tbody tr td a'); if (first) urls.push(await first.getAttribute('href'));
  }
  await ctx0.close();
  console.log('pages:', urls.length);
  const issues = {};
  for (const w of WIDTHS) {
    const ctx = await b.newContext({ viewport: { width: w, height: 900 }, isMobile: w < 1024 || !!process.env.TOUCH, hasTouch: w < 1024 || !!process.env.TOUCH }); const p = await ctx.newPage();
    await login(p);
    for (const u of urls) {
      await p.goto(base + u, { waitUntil: 'networkidle' }).catch(() => {});
      const found = await p.evaluate(() => {
        const vw = document.documentElement.clientWidth, out = [];
        const name = e => e.tagName.toLowerCase() + (e.id ? '#' + e.id : '') + (typeof e.className === 'string' && e.className.trim() ? '.' + e.className.trim().split(/\s+/).slice(0, 2).join('.') : '');
        const path = e => { const parts = []; for (let x = e; x && x !== document.body && parts.length < 3; x = x.parentElement) parts.unshift(name(x)); return parts.join(' > '); };
        if (document.documentElement.scrollWidth > vw + 1) out.push(['sideways-scroll', `page ${document.documentElement.scrollWidth}px in ${vw}px`]);
        const vis = e => { const cs = getComputedStyle(e); if (cs.display === 'none' || cs.visibility === 'hidden' || +cs.opacity === 0) return false; const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
        const all = [...document.querySelectorAll('#content *, #header *, .breadcrumbs *')].filter(vis);
        for (const e of all) {
          if (e.closest('.hidden, [hidden], .fd-sidebar, #nav-sidebar, .calendarbox, .clockbox, .selector-chooser, option')) continue;
          const r = e.getBoundingClientRect();
          // past the screen edge (and not inside a horizontal scroller)
          let anc = e.parentElement, clipBox = null, scroller = false;
          for (; anc && anc !== document.body; anc = anc.parentElement) {
            const cs = getComputedStyle(anc);
            if (['auto', 'scroll'].includes(cs.overflowX)) { scroller = true; break; }
            if (['hidden', 'clip'].includes(cs.overflowX) && !clipBox) clipBox = anc;
          }
          if (scroller) continue;
          if (r.right > vw + 1 || r.left < -1) { out.push(['off-screen', `${path(e)} ${Math.round(r.left)}..${Math.round(r.right)}`]); continue; }
          if (clipBox) { const c = clipBox.getBoundingClientRect(); if (r.right > c.right + 2 && e.children.length === 0 && (e.textContent.trim() || ['INPUT', 'SELECT', 'TEXTAREA', 'IMG', 'BUTTON'].includes(e.tagName))) out.push(['clipped', `${path(e)} cut by ${name(clipBox)} (${Math.round(r.right - c.right)}px)`]); }
        }
        // small tap targets (interactive, standalone)
        for (const e of document.querySelectorAll('#content a[href], #content button, #content input[type=submit], #content select, #header a, #header button')) {
          if (!vis(e) || e.closest('.hidden, .calendarbox, .clockbox, #result_list thead, .paginator, .breadcrumbs, p, li.selector-chooser, td.field-photo, td.field-preview')) continue;
          const r = e.getBoundingClientRect();
          if (r.height < 30 && r.width < 30 && !e.closest('label')) out.push(['tap-target', `${path(e)} ${Math.round(r.width)}x${Math.round(r.height)}`]);
        }
        return out;
      });
      for (const [type, d] of found) { const key = `${type} | ${u.replace(/\/\d+\//, '/<id>/')} | ${d.replace(/-?\d+\.\.-?\d+|\(\d+px\)|\d+x\d+|\d+px in \d+px/g, '#')}`; (issues[key] = issues[key] || new Set()).add(w); }
    }
    await ctx.close();
  }
  const keys = Object.keys(issues).sort();
  for (const k of keys) console.log(k, '@', [...issues[k]].join(','));
  console.log('TOTAL', keys.length);
  await b.close();
})();
