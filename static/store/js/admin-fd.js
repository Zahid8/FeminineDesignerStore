/* FemDes admin: mobile sidebar drawer + status pills in change lists. */
(function () {
  'use strict';
  var TONES = ['pending', 'confirmed', 'processing', 'shipped', 'completed', 'cancelled', 'awaiting_review',
    'paid', 'failed', 'refunded', 'new', 'contacted', 'scheduled', 'done'];

  function setMenu(open) {
    document.body.classList.toggle('fd-nav-open', open);
    var btn = document.querySelector('[data-fd-menu]');
    if (btn) btn.setAttribute('aria-expanded', open ? 'true' : 'false');
    var scrim = document.querySelector('[data-fd-menu-close]');
    if (scrim) scrim.hidden = !open;
  }

  document.addEventListener('click', function (e) {
    if (e.target.closest('[data-fd-menu]')) { setMenu(!document.body.classList.contains('fd-nav-open')); }
    else if (e.target.closest('[data-fd-menu-close]')) { setMenu(false); }
  });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') setMenu(false); });

  function badges() {
    document.querySelectorAll('#result_list td.field-status, #result_list td.field-payment_status').forEach(function (td) {
      if (td.querySelector('.fd-badge, select, input')) return;
      var text = td.textContent.trim();
      var tone = text.toLowerCase().replace(/\s+/g, '_');
      if (!text || TONES.indexOf(tone) === -1) return;
      var span = document.createElement('span');
      span.className = 'fd-badge';
      span.setAttribute('data-tone', tone);
      span.textContent = text;
      td.textContent = '';
      td.appendChild(span);
    });
  }
  // Column names on every cell, so lists and tabular inlines can stack into labelled cards on small screens.
  function labelCells() {
    document.querySelectorAll('#result_list, .inline-group .tabular table').forEach(function (table) {
      var heads = Array.prototype.map.call(table.querySelectorAll('thead th'), function (th) { return th.textContent.trim(); });
      table.classList.add('fd-stackable');
      table.querySelectorAll('tbody tr').forEach(function (tr) {
        var i = 0;
        Array.prototype.forEach.call(tr.children, function (cell) {
          var colspan = parseInt(cell.getAttribute('colspan') || '1', 10);
          if (heads[i] && !cell.hasAttribute('data-label')) cell.setAttribute('data-label', heads[i]);
          i += colspan;
        });
      });
    });
  }
  function ready() { badges(); labelCells(); }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', ready); else ready();
  // New inline rows ("Add another …") get labels too.
  document.addEventListener('formset:added', labelCells);
})();
