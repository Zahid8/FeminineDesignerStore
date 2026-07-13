// FemDes progressive storefront enhancements
// All behavior is additive — site works fully without this script.
(function () {
  'use strict';
  if (typeof document === 'undefined') return;

  function ready(fn) {
    if (document.readyState !== 'loading') { fn(); return; }
    document.addEventListener('DOMContentLoaded', fn);
  }

  function safeClamp(val, min, max) {
    var n = parseInt(val, 10);
    if (isNaN(n)) return min;
    if (n < min) return min;
    if (n > max) return max;
    return n;
  }

  // ---- Quantity steppers ----
  function buildSteppers() {
    var inputs = document.querySelectorAll('.qty-input');
    for (var i = 0; i < inputs.length; i++) {
      (function (input) {
        if (input.dataset.femdesStepper) return;
        input.dataset.femdesStepper = '1';
        var min = parseInt(input.getAttribute('min'), 10) || 1;
        var max = parseInt(input.getAttribute('max'), 10) || 99;
        var wrap = document.createElement('div');
        wrap.className = 'd-inline-flex align-items-center';
        input.parentNode.insertBefore(wrap, input);
        var dec = document.createElement('button');
        dec.type = 'button'; dec.textContent = '−'; dec.className = 'btn btn-sm btn-outline-dark';
        dec.setAttribute('aria-label', 'Decrease quantity');
        dec.addEventListener('click', function () {
          input.value = safeClamp(parseInt(input.value, 10) - 1, min, max);
        });
        var inc = document.createElement('button');
        inc.type = 'button'; inc.textContent = '+'; inc.className = 'btn btn-sm btn-outline-dark';
        inc.setAttribute('aria-label', 'Increase quantity');
        inc.addEventListener('click', function () {
          input.value = safeClamp(parseInt(input.value, 10) + 1, min, max);
        });
        wrap.appendChild(dec);
        wrap.appendChild(input);
        wrap.appendChild(inc);
        input.addEventListener('change', function () {
          input.value = safeClamp(input.value, min, max);
        });
      })(inputs[i]);
    }
  }

  // ---- Search popup focus ----
  function searchFocus() {
    var triggers = document.querySelectorAll('.search-button');
    for (var i = 0; i < triggers.length; i++) {
      triggers[i].addEventListener('click', function () {
        setTimeout(function () {
          var q = document.querySelector('input[name="q"]');
          if (q) q.focus();
        }, 100);
      });
    }
    var searchPopups = document.querySelectorAll('.search-popup');
    for (var j = 0; j < searchPopups.length; j++) {
      searchPopups[j].addEventListener('keydown', function (e) {
        if (e.key === 'Escape') {
          var closeBtn = document.querySelector('.btn-close-search');
          if (closeBtn) closeBtn.click();
          var trigger = document.querySelector('.search-button');
          if (trigger) trigger.focus();
        }
      });
    }
  }

  ready(function () {
    buildSteppers();
    searchFocus();
  });
})();
